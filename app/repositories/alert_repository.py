"""Alert repository: runtime JSON queue + Postgres ``alerts`` table (merge, generate, triage mirror)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.sync_session import sync_session
from app.models.alert import Alert, AlertFilter, AlertListResponse
from app.models.orm_tables import (
    AlertORM,
    KycProfileORM,
    SanctionsWatchlistORM,
    TriageAssessmentORM,
    TransactionORM,
)

logger = get_logger(__name__)

# ── Runtime JSON store (per process, synced to disk) ───────────────────────────
_alerts_store: List[Alert] = []
_disk_mtime: float = 0.0

_RUNTIME_ALERTS_PATH = Path(__file__).resolve().parent.parent / "data" / "runtime_alerts.json"


def _reload_if_stale() -> None:
    """If the runtime JSON file was updated (e.g. by another worker), reload into memory."""
    global _alerts_store, _disk_mtime
    path = _RUNTIME_ALERTS_PATH
    if not path.exists():
        return
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return
    if mtime <= _disk_mtime:
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("runtime_alerts.json read failed; keeping in-memory store", error=str(e))
        return
    if not isinstance(raw, list):
        return
    _alerts_store.clear()
    for row in raw:
        try:
            _alerts_store.append(Alert(**row))
        except Exception as e:
            logger.warning("Skipping invalid alert row in runtime file", error=str(e))
    _disk_mtime = mtime
    logger.info("Reloaded alerts from disk", count=len(_alerts_store), path=str(path))


def _persist() -> None:
    """Write current store to disk (all workers see updates on next read)."""
    global _disk_mtime
    path = _RUNTIME_ALERTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [a.model_dump(mode="json") for a in _alerts_store]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        _disk_mtime = path.stat().st_mtime
    except OSError:
        pass


# ── Postgres ``alerts`` helpers ────────────────────────────────────────────────


def _customer_id_norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _trigger_ctx(alert: Alert) -> Dict[str, Any]:
    return {
        "alert_hash": alert.alert_hash,
        "investigation_id": alert.investigation_id,
        "amount": alert.amount,
        "currency": alert.currency,
        "account_id": alert.account_id,
        "recipient_country": alert.recipient_country,
        "timestamp": alert.timestamp,
        "metadata": alert.metadata,
        "customer_context": alert.customer_context,
    }


def _orm_to_alert(row: AlertORM) -> Alert:
    ctx = row.trigger_context or {}
    return Alert(
        alert_id=row.alert_id,
        investigation_id=str(ctx.get("investigation_id") or row.alert_id),
        transaction_id=row.transaction_id or "",
        customer_id=row.customer_id,
        amount=float(ctx.get("amount", 0) or 0),
        currency=str(ctx.get("currency", "USD")),
        account_id=str(ctx.get("account_id", "")),
        recipient_country=str(ctx.get("recipient_country", "")),
        alert_hash=str(ctx.get("alert_hash") or row.alert_id),
        timestamp=str(ctx.get("timestamp") or ""),
        status=row.status.upper() if row.status else "OPEN",
        severity=row.severity,
        metadata=dict(ctx.get("metadata") or {}),
        customer_context=dict(ctx.get("customer_context") or {}),
    )


def _apply_alert_filters(alerts: List[Alert], filters: Optional[AlertFilter]) -> List[Alert]:
    if not filters:
        return alerts
    out = list(alerts)
    if filters.status:
        out = [a for a in out if a.status == filters.status]
    if filters.severity:
        out = [a for a in out if a.severity == filters.severity]
    if filters.customer_id:
        want = _customer_id_norm(filters.customer_id)
        out = [a for a in out if _customer_id_norm(a.customer_id) == want]
    if filters.alert_id:
        want_id = (filters.alert_id or "").strip()
        if want_id:
            out = [a for a in out if a.alert_id == want_id]
    if filters.date_from:
        out = [a for a in out if a.timestamp >= filters.date_from]
    if filters.date_to:
        out = [a for a in out if a.timestamp <= filters.date_to]
    if getattr(filters, "alert_type", None):
        out = [a for a in out if (a.metadata or {}).get("policy") == filters.alert_type]
    return out


def filter_alert_list(alerts: List[Alert], filters: Optional[AlertFilter]) -> List[Alert]:
    return _apply_alert_filters(alerts, filters)


def fetch_postgres_alert_hashes() -> Set[str]:
    """All ``alert_hash`` values stored in ``alerts.trigger_context`` (best-effort)."""
    try:
        with sync_session() as session:
            hashes: Set[str] = set()
            for (tc,) in session.query(AlertORM.trigger_context).filter(AlertORM.trigger_context.isnot(None)).all():
                if isinstance(tc, dict) and tc.get("alert_hash"):
                    hashes.add(str(tc["alert_hash"]))
            return hashes
    except Exception as e:
        logger.warning("fetch_postgres_alert_hashes failed", error=str(e))
        return set()


def fetch_postgres_alerts(filters: Optional[AlertFilter] = None) -> List[Alert]:
    try:
        with sync_session() as session:
            q = session.query(AlertORM).order_by(AlertORM.created_at.desc())
            if filters:
                cid = (filters.customer_id or "").strip()
                if cid:
                    q = q.filter(func.lower(AlertORM.customer_id) == cid.lower())
                aid = (filters.alert_id or "").strip()
                if aid:
                    q = q.filter(AlertORM.alert_id == aid)
            rows = q.all()
            alerts = [_orm_to_alert(r) for r in rows]
        return _apply_alert_filters(alerts, filters)
    except Exception as e:
        logger.warning("fetch_postgres_alerts failed", error=str(e))
        return []


def _valid_customer_ids(session: Session) -> Set[str]:
    return {c for (c,) in session.query(KycProfileORM.customer_id).all()}


def _valid_transaction_ids(session: Session) -> Set[str]:
    return {t for (t,) in session.query(TransactionORM.transaction_id).all()}


def _sanctions_entry_for_country(session: Session, country: str) -> Optional[str]:
    c = (country or "").strip().upper()
    if not c:
        return None
    for row in session.query(SanctionsWatchlistORM).filter(SanctionsWatchlistORM.is_active.is_(True)).all():
        codes = row.country_codes
        if not isinstance(codes, list):
            continue
        for x in codes:
            if str(x).strip().upper() == c:
                return row.entry_id
    return None


def _resolve_sanctions_fk(session: Session, alert: Alert) -> Optional[str]:
    dest = alert.metadata.get("sanctioned_country") or alert.recipient_country
    return _sanctions_entry_for_country(session, str(dest))


def save_generated_alert_to_sql(alert: Alert) -> bool:
    """Insert one row into ``alerts`` if FKs allow and ``alert_hash`` is not already stored. Returns True if inserted."""
    try:
        with sync_session() as session:
            dup = (
                session.query(AlertORM)
                .filter(AlertORM.trigger_context.isnot(None))
                .filter(AlertORM.trigger_context.contains({"alert_hash": alert.alert_hash}))
                .first()
            )
            if dup is not None:
                return False

            customers = _valid_customer_ids(session)
            if alert.customer_id not in customers:
                logger.warning(
                    "skip_sql_alert_missing_kyc_profile",
                    alert_id=alert.alert_id,
                    customer_id=alert.customer_id,
                )
                return False

            tx_ids = _valid_transaction_ids(session)
            tx_fk = alert.transaction_id if alert.transaction_id and alert.transaction_id in tx_ids else None

            sanctions_fk = _resolve_sanctions_fk(session, alert)

            policy = (alert.metadata or {}).get("policy", "generated") or "generated"
            alert_type = str(policy)[:64]

            row = AlertORM(
                alert_id=alert.alert_id[:128],
                transaction_id=tx_fk,
                customer_id=alert.customer_id,
                sanctions_watchlist_id=sanctions_fk,
                alert_type=alert_type,
                status=(alert.status or "open").lower(),
                severity=(alert.severity or "medium").lower(),
                trigger_context=_trigger_ctx(alert),
            )
            session.add(row)
            session.commit()
            logger.info("alert_inserted_postgres", alert_id=row.alert_id)
            return True
    except Exception as e:
        logger.error("save_generated_alert_to_sql failed", alert_id=alert.alert_id, error=str(e))
        return False


def mirror_alert_update_to_sql(alert_id: str, data: Dict[str, Any]) -> None:
    """Best-effort: apply triage JSON merge fields onto ``alerts`` row with same ``alert_id``."""
    try:
        with sync_session() as session:
            row = session.query(AlertORM).filter(AlertORM.alert_id == alert_id).first()
            if row is None:
                return
            if "status" in data and data["status"] is not None:
                row.status = str(data["status"]).lower()
            if "severity" in data and data["severity"] is not None:
                row.severity = str(data["severity"]).lower()
            ctx = dict(row.trigger_context or {})
            if "metadata" in data and isinstance(data["metadata"], dict):
                ctx["metadata"] = {**ctx.get("metadata", {}), **data["metadata"]}
            row.trigger_context = ctx
            session.commit()
            logger.info("alert_mirrored_postgres", alert_id=alert_id)
    except Exception as e:
        logger.warning("mirror_alert_update_to_sql failed", alert_id=alert_id, error=str(e))


def save_triage_assessment_to_sql(
    alert_id: str,
    risk_score_value: float,
    assessment: Dict[str, Any],
    agent_version: str = "rules_v1",
) -> Optional[int]:
    """
    Insert a snapshot into ``triage_assessments`` when ``alert_id`` exists in ``alerts`` (FK).

    Alerts that exist only in the runtime JSON queue are skipped (no FK row).
    """
    try:
        with sync_session() as session:
            if session.query(AlertORM).filter(AlertORM.alert_id == alert_id).first() is None:
                return None
            row = TriageAssessmentORM(
                alert_id=alert_id,
                risk_score=float(risk_score_value),
                assessment=assessment,
                agent_version=agent_version,
            )
            session.add(row)
            session.commit()
            return int(row.id)
    except Exception as e:
        logger.warning("save_triage_assessment_to_sql failed", alert_id=alert_id, error=str(e))
        return None


# ── Repository class (JSON queue + merged reads) ───────────────────────────────


class AlertRepository:
    """Runtime JSON alert queue with Postgres ``alerts`` merge and SQL persistence for generate/triage."""

    def __init__(self) -> None:
        global _alerts_store
        self._alerts = _alerts_store
        _reload_if_stale()

    async def create_alert(self, alert_data: Dict[str, Any]) -> Alert:
        """Create a new alert in the JSON queue."""
        _reload_if_stale()
        alert = Alert(
            alert_id=alert_data["alert_id"],
            investigation_id=alert_data["investigation_id"],
            transaction_id=alert_data["transaction_id"],
            customer_id=alert_data["customer_id"],
            amount=alert_data["amount"],
            currency=alert_data.get("currency", "USD"),
            account_id=alert_data["account_id"],
            recipient_country=alert_data["recipient_country"],
            alert_hash=alert_data["alert_hash"],
            timestamp=alert_data["timestamp"],
            status=alert_data.get("status", "OPEN"),
            severity=alert_data.get("severity", "medium"),
            metadata=alert_data.get("metadata", {}),
            customer_context=alert_data.get("customer_context", {}),
        )
        self._alerts.append(alert)
        _persist()
        logger.info(f"Alert created: {alert.alert_id}")
        return alert

    async def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID (Postgres row first, then runtime JSON)."""
        _reload_if_stale()
        for a in fetch_postgres_alerts(None):
            if a.alert_id == alert_id:
                return a
        return next((alert for alert in self._alerts if alert.alert_id == alert_id), None)

    async def get_alerts(self, filters: Optional[AlertFilter] = None) -> AlertListResponse:
        """Merge Postgres ``alerts`` rows with the runtime JSON queue (dedupe by ``alert_hash``; Postgres wins).

        When ``filters.customer_id`` is set, Postgres rows and JSON queue entries are restricted to that
        customer before merge so triage/list APIs never assemble a global queue only to filter afterward.
        """
        _reload_if_stale()
        pg_alerts = fetch_postgres_alerts(filters)
        json_pool = self._alerts
        if filters:
            want = _customer_id_norm(filters.customer_id)
            if want:
                json_pool = [a for a in json_pool if _customer_id_norm(a.customer_id) == want]
            aid = (filters.alert_id or "").strip()
            if aid:
                json_pool = [a for a in json_pool if a.alert_id == aid]
        by_hash: dict[str, Alert] = {}
        for a in pg_alerts:
            by_hash[a.alert_hash] = a
        for a in json_pool:
            by_hash.setdefault(a.alert_hash, a)
        combined = sorted(by_hash.values(), key=lambda x: x.timestamp, reverse=True)
        filtered_alerts = filter_alert_list(combined, filters)
        return AlertListResponse(
            alerts=filtered_alerts,
            total_count=len(combined),
            filtered_count=len(filtered_alerts),
        )

    async def update_alert_status(self, alert_id: str, status: str) -> bool:
        """Update alert status in JSON store and mirror to Postgres when a row exists."""
        _reload_if_stale()
        alert = await self.get_alert_by_id(alert_id)
        if alert:
            alert.status = status
            _persist()
            logger.info(f"Alert {alert_id} status updated to {status}")
            mirror_alert_update_to_sql(alert_id, {"status": status})
            return True
        return False

    async def update_alert(self, alert_id: str, data: Dict[str, Any]) -> bool:
        """Replace alert in the JSON store with merged fields; mirror status/metadata onto Postgres if present."""
        _reload_if_stale()
        for i, existing in enumerate(self._alerts):
            if existing.alert_id == alert_id:
                merged = {**existing.model_dump(), **data}
                self._alerts[i] = Alert(**merged)
                _persist()
                logger.info(f"Alert {alert_id} updated in repository")
                mirror_alert_update_to_sql(alert_id, merged)
                return True
        mirror_alert_update_to_sql(alert_id, data)
        return False
