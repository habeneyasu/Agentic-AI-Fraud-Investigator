"""Hybrid rule + AI risk scoring."""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import re

from app.core.logging import get_logger
from app.core.config import get_settings
from app.shared.enums import ScoringMode, RiskCategory
from app.shared.models import RiskFactor, ScoringResult

logger = get_logger(__name__)
settings = get_settings()


class HybridRiskScorer:
    """Rule-first risk scoring; optional AI path when ``llm_provider`` is wired."""

    def __init__(self, mode: ScoringMode = ScoringMode.RULES_ONLY, llm_provider: Any = None):
        self.mode = mode
        self.llm_provider = llm_provider
        self.llm_client = None
        self.rules = self._load_rules()
        
    def _load_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load scoring rules from configuration."""
        return {
            'transaction': {'threshold': settings.transaction_amount_threshold, 'weight': 0.3},
            'device': {'new_device': 0.2, 'unknown_device': 0.3, 'weight': 0.2},
            'geo': {'high_risk_country': 0.4, 'unusual_location': 0.2, 'weight': 0.25},
            'sanctions': {'sanctioned': 0.8, 'pep': 0.5, 'weight': 0.35},
            'behavior': {'failed_login': 0.15, 'unusual_timing': 0.1, 'high_frequency': 0.2, 'weight': 0.2}
        }
    
    async def calculate_risk_score(self, event: Dict[str, Any]) -> ScoringResult:
        """Calculate risk score for event."""
        logger.info(f"Calculating risk score using {self.mode.value} mode")
        
        if self.mode == ScoringMode.RULES_ONLY:
            return await self._rules_based_scoring(event)
        elif self.mode == ScoringMode.AI_ONLY:
            return await self._ai_based_scoring(event)
        else:
            return await self._hybrid_scoring(event)
    
    async def _rules_based_scoring(self, event: Dict[str, Any]) -> ScoringResult:
        """Calculate risk score from agent output lists or flat event fields.

        Fix 2: When the graph passes aggregated agent outputs
        (transaction_anomalies, kyc_anomalies, sanctions_hits), extract signals
        from those lists instead of looking for flat keys that are never present.
        Falls back to flat-key lookup for direct single-event calls.
        """
        score = 0.0
        factors = []

        # ── Agent-aggregated path (called from _node_risk) ────────────────────
        tx_anomalies: List[Dict[str, Any]] = event.get("transaction_anomalies") or []
        kyc_anomalies: List[Dict[str, Any]] = event.get("kyc_anomalies") or []
        sanctions_hits: List[Dict[str, Any]] = event.get("sanctions_hits") or []

        if tx_anomalies or kyc_anomalies or sanctions_hits:
            # Transaction anomalies
            for anomaly in tx_anomalies:
                severity = str(anomaly.get("severity", "medium")).lower()
                weight = {"high": 0.4, "medium": 0.2, "low": 0.1}.get(severity, 0.1)
                score += weight
                factors.append(RiskFactor(
                    category=RiskCategory.TRANSACTION,
                    factor=str(anomaly.get("type", "transaction_anomaly")),
                    weight=weight,
                    value=weight,
                    description=str(anomaly.get("description", "Transaction anomaly detected")),
                ))

            # KYC anomalies
            for anomaly in kyc_anomalies:
                severity = str(anomaly.get("severity", "medium")).lower()
                weight = {"critical": 0.5, "high": 0.3, "medium": 0.2, "low": 0.1}.get(severity, 0.1)
                score += weight
                factors.append(RiskFactor(
                    category=RiskCategory.DEVICE,
                    factor=str(anomaly.get("anomaly_type", "kyc_anomaly")),
                    weight=weight,
                    value=weight,
                    description=str(anomaly.get("description", "KYC anomaly detected")),
                ))

            # Sanctions hits
            for hit in sanctions_hits:
                hit_score = float(hit.get("risk_score") or 0.0)
                weight = min(hit_score, self.rules["sanctions"]["sanctioned"])
                score += weight
                factors.append(RiskFactor(
                    category=RiskCategory.SANCTIONS,
                    factor="sanctions_hit",
                    weight=weight,
                    value=hit_score,
                    description=f"Sanctions hit: {hit.get('entity_name', 'unknown')} "
                                f"({hit.get('country_code', '')})",
                ))

            final_score = min(score, 1.0)
            return ScoringResult(
                risk_score=final_score,
                risk_level=self._get_risk_level(final_score),
                confidence=0.85,
                factors=factors,
                explanation=(
                    f"Agent-aggregated scoring: tx_anomalies={len(tx_anomalies)}, "
                    f"kyc_anomalies={len(kyc_anomalies)}, sanctions_hits={len(sanctions_hits)} "
                    f"→ {final_score:.3f}"
                ),
                scoring_mode=ScoringMode.RULES_ONLY,
                timestamp=datetime.utcnow(),
                rule_score=final_score,
                ai_score=None,
            )

        # ── Flat single-event path (direct calls) ─────────────────────────────
        if event.get('amount', 0) > self.rules['transaction']['threshold']:
            score += self.rules['transaction']['weight']
            factors.append(RiskFactor(
                category=RiskCategory.TRANSACTION,
                factor="high_amount",
                weight=self.rules['transaction']['weight'],
                value=event.get('amount', 0),
                description=f"High transaction amount: ${event.get('amount', 0):,.2f}"
            ))

        if event.get('new_device', False):
            score += self.rules['device']['new_device']
            factors.append(RiskFactor(
                category=RiskCategory.DEVICE,
                factor="new_device",
                weight=self.rules['device']['new_device'],
                value=1.0,
                description="New device detected"
            ))

        if event.get('high_risk_country', False):
            score += self.rules['geo']['high_risk_country']
            factors.append(RiskFactor(
                category=RiskCategory.GEO,
                factor="high_risk_country",
                weight=self.rules['geo']['high_risk_country'],
                value=1.0,
                description="High-risk country detected"
            ))

        if event.get('sanctioned_entity', False):
            score += self.rules['sanctions']['sanctioned']
            factors.append(RiskFactor(
                category=RiskCategory.SANCTIONS,
                factor="sanctioned_entity",
                weight=self.rules['sanctions']['sanctioned'],
                value=1.0,
                description="Sanctioned entity detected"
            ))

        failed_attempts = event.get('failed_attempts', 0)
        if failed_attempts > 3:
            behavior_score = self.rules['behavior']['failed_login'] * min(failed_attempts / 3, 2)
            score += behavior_score
            factors.append(RiskFactor(
                category=RiskCategory.BEHAVIOR,
                factor="failed_attempts",
                weight=behavior_score,
                value=failed_attempts,
                description=f"Multiple failed attempts: {failed_attempts}"
            ))

        final_score = min(score, 1.0)
        return ScoringResult(
            risk_score=final_score,
            risk_level=self._get_risk_level(final_score),
            confidence=0.85,
            factors=factors,
            explanation=f"Rules-based scoring: {final_score:.3f}",
            scoring_mode=ScoringMode.RULES_ONLY,
            timestamp=datetime.utcnow(),
            rule_score=final_score,
            ai_score=None
        )
    
    async def _ai_based_scoring(self, event: Dict[str, Any]) -> ScoringResult:
        """Calculate risk score using AI analysis."""
        if self.llm_client is None:
            return await self._rules_based_scoring(event)
        try:
            context = {
                'customer_risk_profile': event.get('risk_profile', 'unknown'),
                'historical_patterns': event.get('historical_patterns', 'none'),
                'previous_alerts': event.get('previous_alerts', 'none'),
                'account_age': event.get('account_age_days', 'unknown'),
                'typical_amount': event.get('typical_amount', 'unknown')
            }
            
            ai_result = await self.llm_client.analyze_transaction(event, context)
            ai_score = self._parse_ai_score(ai_result)
            
            factors = [RiskFactor(
                category=RiskCategory.AI_CONTEXT,
                factor="ai_analysis",
                weight=ai_score,
                value=ai_score,
                description="AI-based risk assessment"
            )]
            
            return ScoringResult(
                risk_score=ai_score,
                risk_level=self._get_risk_level(ai_score),
                confidence=0.75,
                factors=factors,
                explanation=f"AI-based scoring: {ai_score:.3f}",
                scoring_mode=ScoringMode.AI_ONLY,
                timestamp=datetime.utcnow(),
                rule_score=None,
                ai_score=ai_score
            )
            
        except Exception as e:
            logger.error(f"AI scoring failed: {e}")
            return await self._rules_based_scoring(event)
    
    async def _hybrid_scoring(self, event: Dict[str, Any]) -> ScoringResult:
        """Calculate risk score using hybrid approach."""
        rules_result = await self._rules_based_scoring(event)
        ai_result = await self._ai_based_scoring(event)
        
        # Dynamic weighting based on AI confidence
        rule_weight = 0.8 if ai_result.confidence < 0.5 else (0.4 if ai_result.confidence > 0.9 else 0.6)
        ai_weight = 1.0 - rule_weight
        
        hybrid_score = (rules_result.risk_score * rule_weight) + (ai_result.risk_score * ai_weight)
        hybrid_score = min(hybrid_score, 1.0)
        
        hybrid_factors = rules_result.factors + ai_result.factors + [RiskFactor(
            category=RiskCategory.AI_CONTEXT,
            factor="hybrid_combination",
            weight=0.1,
            value=hybrid_score,
            description=f"Hybrid: {rule_weight:.0%} rules + {ai_weight:.0%} AI"
        )]
        
        hybrid_confidence = (rules_result.confidence * rule_weight) + (ai_result.confidence * ai_weight)
        
        return ScoringResult(
            risk_score=hybrid_score,
            risk_level=self._get_risk_level(hybrid_score),
            confidence=hybrid_confidence,
            factors=hybrid_factors,
            explanation=f"Hybrid: {rules_result.risk_score:.3f} × {rule_weight:.0%} + {ai_result.risk_score:.3f} × {ai_weight:.0%} = {hybrid_score:.3f}",
            scoring_mode=ScoringMode.HYBRID,
            timestamp=datetime.utcnow(),
            rule_score=rules_result.risk_score,
            ai_score=ai_result.risk_score
        )
    
    def _parse_ai_score(self, ai_result: Dict[str, Any]) -> float:
        """Parse risk score from AI response."""
        try:
            response_text = ai_result.get('response', '')
            
            if response_text.startswith('{'):
                ai_response = json.loads(response_text)
                score = ai_response.get('overall_risk_score', 50) / 100.0
                return min(max(score, 0.0), 1.0)
            
            # Extract score from text
            score_match = re.search(r'risk[_\s]*score[:\s]*([0-9.]+)', response_text.lower())
            if score_match:
                score = float(score_match.group(1)) / 100.0
                return min(max(score, 0.0), 1.0)
            
            return 0.5
                
        except Exception as e:
            logger.warning(f"Failed to parse AI score: {e}")
            return 0.5
    
    def _get_risk_level(self, score: float) -> str:
        """Get risk level from score."""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        elif score >= 0.2:
            return "LOW"
        else:
            return "MINIMAL"


# Global instances — default RULES_ONLY avoids legacy LLMClient dependency in graph scoring.
hybrid_scorer = HybridRiskScorer(mode=ScoringMode.RULES_ONLY)


def get_scorer(mode: ScoringMode = ScoringMode.RULES_ONLY) -> HybridRiskScorer:
    """Get scorer instance."""
    return HybridRiskScorer(mode)


async def calculate_risk_score(event: Dict[str, Any], 
                           mode: ScoringMode = ScoringMode.RULES_ONLY) -> ScoringResult:
    """Calculate risk score using hybrid scorer."""
    return await hybrid_scorer.calculate_risk_score(event)


def update_scoring_mode(mode: ScoringMode) -> None:
    """Update global scoring mode."""
    global hybrid_scorer
    hybrid_scorer = HybridRiskScorer(mode)
    logger.info(f"Updated scoring mode to: {mode.value}")
