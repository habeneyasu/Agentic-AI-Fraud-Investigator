"""Build alert payloads from policy rules over file-backed reference data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from app.core.logging import get_logger
from app.data.data_loader import data_loader
from app.models.alert import Alert

logger = get_logger(__name__)


def _utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


class AlertGenerationService:
    """Policy-driven alert payloads (caller persists via ``AlertRepository``)."""

    def __init__(self) -> None:
        self.data_loader = data_loader

    async def generate_alerts_from_data(self, customer_id: str) -> List[Alert]:
        cid = (customer_id or "").strip()
        txs = self.data_loader.get_transactions(cid) if cid else self.data_loader.get_all_transactions()
        kyc = self.data_loader.get_kyc_events(cid) if cid else self.data_loader.get_all_kyc_events()
        sanctions = self.data_loader.get_sanctions_data()

        out: List[Alert] = []
        out.extend(await self._high_value_alerts(txs, cid))
        out.extend(await self._new_device_alerts(kyc, cid))
        out.extend(await self._sanctions_country_alerts(txs, sanctions, cid))
        logger.info("generated_alert_payloads", count=len(out), customer_id=cid or "*")
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
        sanctions_list: Dict[str, Any],
        customer_id: str,
    ) -> List[Alert]:
        sanctioned: Set[str] = set()
        for entry in sanctions_list.get("sanctions_entries", []):
            sanctioned.update(entry.get("countries", []))
        sanctioned.update(["IR", "KP", "MM", "SD", "SY", "YE"])

        alerts: List[Alert] = []
        stamp = _utc_compact()
        for tx in transactions:
            dest = tx.get("destination_country", "") or ""
            if dest not in sanctioned:
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
