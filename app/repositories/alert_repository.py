"""Alert repository implementation — in-memory list synced to disk for multi-worker / reload safety."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.alert import Alert, AlertFilter, AlertListResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global alert store (per process). Synced with disk so triage and GET /alerts agree across
# uvicorn workers, --reload restarts, and different client hosts hitting the same API port.
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


class AlertRepository:
    """Repository for alert data operations."""

    def __init__(self) -> None:
        global _alerts_store
        self._alerts = _alerts_store
        _reload_if_stale()

    async def create_alert(self, alert_data: Dict[str, Any]) -> Alert:
        """Create a new alert."""
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
        """Get alert by ID."""
        _reload_if_stale()
        return next((alert for alert in self._alerts if alert.alert_id == alert_id), None)

    async def get_alerts(self, filters: Optional[AlertFilter] = None) -> AlertListResponse:
        """Get alerts with optional filtering."""
        _reload_if_stale()
        filtered_alerts = list(self._alerts)

        if filters:
            if filters.status:
                filtered_alerts = [a for a in filtered_alerts if a.status == filters.status]
            if filters.severity:
                filtered_alerts = [a for a in filtered_alerts if a.severity == filters.severity]
            if filters.customer_id:
                cid = filters.customer_id.strip()
                filtered_alerts = [a for a in filtered_alerts if (a.customer_id or "").strip() == cid]
            if filters.date_from:
                filtered_alerts = [a for a in filtered_alerts if a.timestamp >= filters.date_from]
            if filters.date_to:
                filtered_alerts = [a for a in filtered_alerts if a.timestamp <= filters.date_to]
            if filters.alert_type:
                filtered_alerts = [
                    a for a in filtered_alerts if getattr(a, "alert_type", None) == filters.alert_type
                ]

        return AlertListResponse(
            alerts=filtered_alerts,
            total_count=len(self._alerts),
            filtered_count=len(filtered_alerts),
        )

    async def update_alert_status(self, alert_id: str, status: str) -> bool:
        """Update alert status."""
        _reload_if_stale()
        alert = await self.get_alert_by_id(alert_id)
        if alert:
            alert.status = status
            _persist()
            logger.info(f"Alert {alert_id} status updated to {status}")
            return True
        return False

    async def update_alert(self, alert_id: str, data: Dict[str, Any]) -> bool:
        """Replace alert in the store with merged fields (used after triage scoring)."""
        _reload_if_stale()
        for i, existing in enumerate(self._alerts):
            if existing.alert_id == alert_id:
                merged = {**existing.model_dump(), **data}
                self._alerts[i] = Alert(**merged)
                _persist()
                logger.info(f"Alert {alert_id} updated in repository")
                return True
        return False
