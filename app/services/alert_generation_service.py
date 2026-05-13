"""Build alert payloads from policy rules over Postgres ORM tables."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.sync_session import sync_session
from app.models.alert import Alert
from app.models.orm_tables import (
    CountryRiskORM,
    KycProfileORM,
    SanctionsWatchlistORM,
    TransactionORM,
)

logger = get_logger(__name__)


def _utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _iso_z(dt: datetime) -> str:
    s = dt.isoformat()
    if s.endswith("Z"):
        return s
    if s.endswith("+00:00"):
        return s[:-6] + "Z"
    return s


def _transaction_to_dict(tx: TransactionORM) -> Dict[str, Any]:
    raw = tx.raw_payload or {}
    dest = (tx.destination_country or "").strip().upper()
    ts = _iso_z(tx.occurred_at)
    return {
        "transaction_id": tx.transaction_id,
        "customer_id": tx.customer_id,
        "amount": tx.amount,
        "currency": tx.currency,
        "timestamp": ts,
        "transaction_type": tx.transaction_type,
        "source_account": tx.source_account or "",
        "destination_account": tx.destination_account or "",
        "destination_country": dest,
        "description": tx.narrative or "",
        "ip_address": raw.get("ip_address"),
        "device_id": raw.get("device_id"),
        "risk_indicators": raw.get("risk_indicators") or [],
    }


def _kyc_profile_to_event_row(p: KycProfileORM) -> Dict[str, Any]:
    pl = p.profile_payload or {}
    ts = pl.get("timestamp")
    if not ts and p.last_reviewed_at:
        ts = _iso_z(p.last_reviewed_at)
    if not ts:
        ts = _iso_z(p.updated_at)
    return {
        "customer_id": p.customer_id,
        "event_type": pl.get("event_type", "profile_snapshot"),
        "timestamp": ts,
        "ip_address": pl.get("ip_address", ""),
        "device_info": pl.get("device_info") or {},
        "geo_location": pl.get("geo_location") or {},
        "anomaly_type": pl.get("anomaly_type", ""),
        "risk_score": pl.get("risk_score", 0.0),
    }


def _load_transactions(session: Session, customer_id: str) -> List[Dict[str, Any]]:
    q = session.query(TransactionORM)
    if customer_id:
        q = q.filter(TransactionORM.customer_id == customer_id)
    return [_transaction_to_dict(tx) for tx in q.order_by(TransactionORM.occurred_at).all()]


def _load_kyc_events(session: Session, customer_id: str) -> List[Dict[str, Any]]:
    q = session.query(KycProfileORM)
    if customer_id:
        q = q.filter(KycProfileORM.customer_id == customer_id)
    return [_kyc_profile_to_event_row(p) for p in q.all()]


def _sanctioned_country_codes(session: Session) -> Set[str]:
    codes: Set[str] = set()
    for row in session.query(SanctionsWatchlistORM).filter(SanctionsWatchlistORM.is_active.is_(True)).all():
        cc = row.country_codes
        if isinstance(cc, list):
            for c in cc:
                if c:
                    codes.add(str(c).strip().upper())
    for cr in session.query(CountryRiskORM).all():
        if cr.sanctions_active or cr.risk_level in ("CRITICAL", "HIGH"):
            codes.add(cr.country_code.strip().upper())
    codes.update({"IR", "KP", "MM", "SD", "SY", "YE"})
    return codes


class AlertGenerationService:
    """Policy-driven alerts from ``transactions``, ``kyc_profiles``, ``sanctions_watchlist`` (+ ``country_risks``)."""

    async def generate_alerts_from_data(self, customer_id: str) -> List[Alert]:
        cid = (customer_id or "").strip()
        with sync_session() as session:
            txs = _load_transactions(session, cid)
            kyc = _load_kyc_events(session, cid)
            sanctioned = _sanctioned_country_codes(session)

        out: List[Alert] = []
        out.extend(await self._high_value_alerts(txs, cid))
        out.extend(await self._new_device_alerts(kyc, cid))
        out.extend(await self._sanctions_country_alerts(txs, sanctioned, cid))
        logger.info("generated_alert_payloads", count=len(out), customer_id=cid or "*", source="postgres")
        return out

    async def _high_value_alerts(self, transactions: List[Dict[str, Any]], customer_id: str) -> List[Alert]:
        alerts: List[Alert] = []
        stamp = _utc_compact()
        for tx in transactions:
            amount = tx.get("amount", 0) or 0
            if amount <= 10000:
                continue
            tid = tx.get("transaction_id", "")
            alerts.append(
                Alert(
                    alert_id=f"TX_HIGH_VALUE_{tid}_{stamp}",
                    investigation_id=f"inv_{tid}_{stamp}",
                    transaction_id=tid,
                    customer_id=tx.get("customer_id", customer_id),
                    amount=amount,
                    currency=tx.get("currency", "USD"),
                    account_id=tx.get("source_account", ""),
                    recipient_country=tx.get("destination_country", ""),
                    alert_hash=f"hash_{amount}_{tid}",
                    timestamp=tx.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    status="OPEN",
                    severity="high",
                    metadata={
                        "reason": "Amount exceeds high-value threshold",
                        "policy": "high_value_transaction_amount",
                        "amount": amount,
                        "threshold": 10000,
                        "transaction_type": tx.get("transaction_type", ""),
                        "description": tx.get("description", ""),
                    },
                )
            )
        return alerts

    async def _new_device_alerts(self, kyc_events: List[Dict[str, Any]], customer_id: str) -> List[Alert]:
        if not kyc_events:
            return []

        def _ts(ev: Dict[str, Any]) -> str:
            return str(ev.get("timestamp") or "")

        ordered = sorted(kyc_events, key=_ts)
        seen: Dict[str, Set[str]] = {}
        alerts: List[Alert] = []
        stamp = _utc_compact()

        for event in ordered:
            cust = event.get("customer_id") or customer_id
            dev = event.get("device_info", {}) or {}
            fp = f"{dev.get('os', '')}_{dev.get('browser', '')}_{event.get('ip_address', '')}"
            prior = seen.setdefault(cust, set())
            if fp not in prior and prior:
                alerts.append(
                    Alert(
                        alert_id=f"KYC_NEW_DEVICE_{cust}_{stamp}",
                        investigation_id=f"inv_{cust}_{stamp}",
                        transaction_id="",
                        customer_id=event.get("customer_id", customer_id),
                        amount=0.0,
                        currency="USD",
                        account_id=event.get("customer_id", customer_id),
                        recipient_country="",
                        alert_hash=f"hash_{fp}",
                        timestamp=event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        status="OPEN",
                        severity="medium",
                        metadata={
                            "reason": "Login from device not seen earlier for this customer",
                            "policy": "new_device_login",
                            "event_type": event.get("event_type", ""),
                            "ip_address": event.get("ip_address", ""),
                            "device_info": dev,
                            "geo_location": event.get("geo_location", {}),
                            "anomaly_type": event.get("anomaly_type", ""),
                        },
                    )
                )
            prior.add(fp)
        return alerts

    async def _sanctions_country_alerts(
        self,
        transactions: List[Dict[str, Any]],
        sanctioned_countries: Set[str],
        customer_id: str,
    ) -> List[Alert]:
        alerts: List[Alert] = []
        stamp = _utc_compact()
        for tx in transactions:
            dest = (tx.get("destination_country", "") or "").strip().upper()
            if dest not in sanctioned_countries:
                continue
            tid = tx.get("transaction_id", "")
            alerts.append(
                Alert(
                    alert_id=f"SANCTION_COUNTRY_{tid}_{stamp}",
                    investigation_id=f"inv_{tid}_{stamp}",
                    transaction_id=tid,
                    customer_id=tx.get("customer_id", customer_id),
                    amount=tx.get("amount", 0),
                    currency=tx.get("currency", "USD"),
                    account_id=tx.get("source_account", ""),
                    recipient_country=dest,
                    alert_hash=f"hash_{dest}_{tid}",
                    timestamp=tx.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    status="OPEN",
                    severity="high",
                    metadata={
                        "reason": "Destination country on sanctions / high-risk list",
                        "policy": "transfer_to_sanctioned_country",
                        "sanctioned_country": dest,
                        "destination_account": tx.get("destination_account", ""),
                        "transaction_type": tx.get("transaction_type", ""),
                        "description": tx.get("description", ""),
                        "ip_address": tx.get("ip_address", ""),
                    },
                )
            )
        return alerts
