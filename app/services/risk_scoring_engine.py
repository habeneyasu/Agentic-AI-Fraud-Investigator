"""Risk Scoring Engine - Domain logic for calculating alert risk scores."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from app.models.triage import AlertPolicy, AlertSeverity, RiskScore

# Transactions older than this many days get a recency penalty
_RECENCY_PENALTY_DAYS = 30
_RECENCY_PENALTY_FACTOR = 0.85  # multiply raw score by this if stale


def _recency_penalty(alert) -> Tuple[float, bool]:
    """Return (multiplier, penalty_applied). Stale alerts get 0.85× their raw score."""
    ts = getattr(alert, "timestamp", None) or alert.metadata.get("timestamp")
    if not ts:
        return 1.0, False
    try:
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - ts).days
        if age_days > _RECENCY_PENALTY_DAYS:
            return _RECENCY_PENALTY_FACTOR, True
    except Exception:
        pass
    return 1.0, False


class RiskScoringEngine:
    """Enterprise-grade risk scoring engine with configurable rules."""
    
    def __init__(self):
        # Risk scoring thresholds - can be made configurable
        self.high_value_thresholds = {
            "critical": 50000,
            "high": 25000,
            "medium": 15000,
            "base": 10000
        }
        
        self.high_value_scores = {
            "critical": 0.9,
            "high": 0.7,
            "medium": 0.5,
            "base": 0.3
        }
        
        self.device_login_scores = {
            "geo_mismatch": 0.8,
            "anomaly": 0.6,
            "clean": 0.4
        }
        
        self.sanctioned_country_scores = {
            "critical": ["IR", "KP", "SY"],
            "high": ["MM", "SD", "YE"],
            "medium": ["AF", "CU", "IR"],  # Example medium risk
            "base": 0.6
        }
    
    def score(self, alert) -> RiskScore:
        """
        Calculate risk score for an alert based on policy type and metadata.
        Applies a recency penalty (×0.85) for transactions older than 30 days.
        """
        policy = alert.metadata.get("policy", "")
        score = 0.0
        scoring_factors = {}

        if policy == AlertPolicy.HIGH_VALUE_TRANSACTION:
            score, factors = self._score_high_value_transaction(alert.amount)
            scoring_factors.update(factors)

        elif policy == AlertPolicy.NEW_DEVICE_LOGIN:
            anomaly_type = alert.metadata.get("anomaly_type", "")
            score, factors = self._score_device_login(anomaly_type)
            scoring_factors.update(factors)

        elif policy == AlertPolicy.SANCTIONED_COUNTRY:
            sanctioned_country = alert.metadata.get("sanctioned_country", "")
            score, factors = self._score_sanctioned_country(sanctioned_country)
            scoring_factors.update(factors)

        # Apply recency penalty for stale transactions
        multiplier, penalty_applied = _recency_penalty(alert)
        if penalty_applied:
            score = score * multiplier
            scoring_factors["recency_penalty_applied"] = True
            scoring_factors["recency_penalty_factor"] = multiplier
        else:
            scoring_factors["recency_penalty_applied"] = False

        # Determine severity
        severity = self._determine_severity(score)
        auto_close_eligible = score < 0.6

        return RiskScore(
            score=round(score, 3),
            severity=severity,
            auto_close_eligible=auto_close_eligible,
            assessment_timestamp=datetime.now(timezone.utc),
            scoring_factors=scoring_factors,
        )
    
    def _score_high_value_transaction(self, amount: float) -> tuple[float, Dict[str, Any]]:
        """Score high-value transaction alerts."""
        if amount >= self.high_value_thresholds["critical"]:
            score = self.high_value_scores["critical"]
            tier = "critical"
        elif amount >= self.high_value_thresholds["high"]:
            score = self.high_value_scores["high"]
            tier = "high"
        elif amount >= self.high_value_thresholds["medium"]:
            score = self.high_value_scores["medium"]
            tier = "medium"
        else:
            score = self.high_value_scores["base"]
            tier = "base"
        
        factors = {
            "transaction_amount": amount,
            "amount_tier": tier,
            "threshold_used": self.high_value_thresholds["medium"]
        }
        
        return score, factors
    
    def _score_device_login(self, anomaly_type: str) -> tuple[float, Dict[str, Any]]:
        """Score new device login alerts."""
        if anomaly_type == "geo_location_mismatch":
            score = self.device_login_scores["geo_mismatch"]
            tier = "geo_mismatch"
        elif anomaly_type:
            score = self.device_login_scores["anomaly"]
            tier = "anomaly"
        else:
            score = self.device_login_scores["clean"]
            tier = "clean"
        
        factors = {
            "anomaly_type": anomaly_type,
            "anomaly_tier": tier,
            "geo_mismatch": anomaly_type == "geo_location_mismatch"
        }
        
        return score, factors
    
    def _score_sanctioned_country(self, sanctioned_country: str) -> tuple[float, Dict[str, Any]]:
        """Score sanctioned country transfer alerts."""
        if sanctioned_country in self.sanctioned_country_scores["critical"]:
            score = 0.95
            tier = "critical"
        elif sanctioned_country in self.sanctioned_country_scores["high"]:
            score = 0.8
            tier = "high"
        else:
            score = self.sanctioned_country_scores["base"]
            tier = "medium"
        
        factors = {
            "sanctioned_country": sanctioned_country,
            "country_tier": tier,
            "critical_sanctions": sanctioned_country in self.sanctioned_country_scores["critical"]
        }
        
        return score, factors
    
    def _determine_severity(self, score: float) -> AlertSeverity:
        """Determine alert severity based on risk score."""
        if score >= 0.8:
            return AlertSeverity.CRITICAL
        elif score >= 0.6:
            return AlertSeverity.HIGH
        elif score >= 0.4:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
