"""Mock risk scoring system with random and rule-based options."""

from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import random

from app.core.logging import get_logger

logger = get_logger(__name__)


class ScoringMode(str, Enum):
    """Scoring mode types."""
    RANDOM = "random"
    RULES_ONLY = "rules_only"
    HYBRID = "hybrid"


class RiskCategory(str, Enum):
    """Risk categories."""
    TRANSACTION = "transaction"
    DEVICE = "device"
    GEO = "geo"
    SANCTIONS = "sanctions"
    BEHAVIOR = "behavior"
    IDENTITY = "identity"


@dataclass
class RiskFactor:
    """Risk factor for scoring."""
    category: RiskCategory
    factor: str
    weight: float
    value: float
    description: str


@dataclass
class ScoringResult:
    """Scoring result."""
    risk_score: float
    risk_level: str
    confidence: float
    factors: List[RiskFactor]
    explanation: str
    scoring_mode: ScoringMode
    timestamp: datetime


class MockRiskScorer:
    """Mock risk scoring system."""
    
    def __init__(self, mode: ScoringMode = ScoringMode.RANDOM):
        self.mode = mode
        self.rules = self._load_rules()
        
    def _load_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load scoring rules."""
        return {
            'transaction': {
                'high_amount_threshold': 10000
            },
            'device': {
                'new_device_penalty': 0.3
            },
            'geo': {
                'high_risk_country_penalty': 0.5
            },
            'sanctions': {
                'sanctioned_entity_penalty': 0.8
            },
            'behavior': {
                'failed_login_penalty': 0.2
            },
            'identity': {
                'synthetic_identity_penalty': 0.7
            }
        }
    
    async def calculate_risk_score(self, event: Dict[str, Any]) -> ScoringResult:
        """Calculate risk score for event."""
        logger.info(f"Calculating risk score using {self.mode.value} mode")
        
        if self.mode == ScoringMode.RANDOM:
            return await self._random_scoring(event)
        elif self.mode == ScoringMode.RULES_ONLY:
            return await self._rules_based_scoring(event)
        else:  # HYBRID
            return await self._hybrid_scoring(event)
    
    async def _random_scoring(self, event: Dict[str, Any]) -> ScoringResult:
        """Generate random risk score."""
        event_type = event.get('event_type', 'unknown')
        
        if event_type == 'transaction':
            base_score = max(0.0, min(random.uniform(0.0, 1.0) + random.uniform(-0.1, 0.3), 1.0))
        elif event_type == 'login':
            base_score = max(0.0, min(random.uniform(0.0, 1.0) + random.uniform(-0.2, 0.2), 1.0))
        else:
            base_score = random.uniform(0.0, 1.0)
        
        return ScoringResult(
            risk_score=base_score,
            risk_level=self._get_risk_level(base_score),
            confidence=random.uniform(0.6, 0.9),
            factors=self._generate_mock_factors(event, base_score),
            explanation=f"Random scoring generated score {base_score:.3f}",
            scoring_mode=ScoringMode.RANDOM,
            timestamp=datetime.utcnow()
        )
    
    async def _rules_based_scoring(self, event: Dict[str, Any]) -> ScoringResult:
        """Calculate risk score using rules."""
        score = 0.0
        factors = []
        
        # Transaction rules
        if event.get('amount', 0) > self.rules['transaction']['high_amount_threshold']:
            score += 0.3
            factors.append(RiskFactor(
                category=RiskCategory.TRANSACTION,
                factor="high_amount",
                weight=0.3,
                value=event.get('amount', 0),
                description="High transaction amount detected"
            ))
        
        # Device rules
        if event.get('new_device', False):
            score += self.rules['device']['new_device_penalty']
            factors.append(RiskFactor(
                category=RiskCategory.DEVICE,
                factor="new_device",
                weight=self.rules['device']['new_device_penalty'],
                value=1.0,
                description="New device detected"
            ))
        
        # Geo rules
        if event.get('high_risk_country', False):
            score += self.rules['geo']['high_risk_country_penalty']
            factors.append(RiskFactor(
                category=RiskCategory.GEO,
                factor="high_risk_country",
                weight=self.rules['geo']['high_risk_country_penalty'],
                value=1.0,
                description="High-risk country detected"
            ))
        
        # Sanctions rules
        if event.get('sanctioned_entity', False):
            score += self.rules['sanctions']['sanctioned_entity_penalty']
            factors.append(RiskFactor(
                category=RiskCategory.SANCTIONS,
                factor="sanctioned_entity",
                weight=self.rules['sanctions']['sanctioned_entity_penalty'],
                value=1.0,
                description="Sanctioned entity detected"
            ))
        
        # Behavior rules
        failed_attempts = event.get('failed_attempts', 0)
        if failed_attempts > 3:
            actual_contribution = self.rules['behavior']['failed_login_penalty'] * min(failed_attempts / 3, 2)
            score += actual_contribution
            factors.append(RiskFactor(
                category=RiskCategory.BEHAVIOR,
                factor="failed_attempts",
                weight=actual_contribution,
                value=failed_attempts,
                description=f"Multiple failed attempts: {failed_attempts}"
            ))
        
        capped_score = min(score, 1.0)
        return ScoringResult(
            risk_score=capped_score,
            risk_level=self._get_risk_level(capped_score),
            confidence=0.8,
            factors=factors,
            explanation=f"Rules-based scoring calculated score {capped_score:.3f}",
            scoring_mode=ScoringMode.RULES_ONLY,
            timestamp=datetime.utcnow()
        )
    
    async def _hybrid_scoring(self, event: Dict[str, Any]) -> ScoringResult:
        """Calculate risk score using hybrid approach."""
        rules_result = await self._rules_based_scoring(event)
        random_factor = random.uniform(-0.1, 0.1)
        hybrid_score = max(0.0, min(rules_result.risk_score + random_factor, 1.0))
        
        # Blend factors
        hybrid_factors = rules_result.factors.copy()
        if abs(random_factor) > 0.05:
            hybrid_factors.append(RiskFactor(
                category=RiskCategory.IDENTITY,
                factor="random_variation",
                weight=abs(random_factor),
                value=random_factor,
                description="Random variation applied"
            ))
        
        return ScoringResult(
            risk_score=hybrid_score,
            risk_level=self._get_risk_level(hybrid_score),
            confidence=0.85,
            factors=hybrid_factors,
            explanation=f"Hybrid scoring: {rules_result.risk_score:.3f} + {random_factor:.3f}",
            scoring_mode=ScoringMode.HYBRID,
            timestamp=datetime.utcnow()
        )
    
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
    
    def _generate_mock_factors(self, event: Dict[str, Any], score: float) -> List[RiskFactor]:
        """Generate mock risk factors for random scoring."""
        factors = []
        
        if score > 0.7:
            factors.append(RiskFactor(
                category=RiskCategory.TRANSACTION,
                factor="high_risk_pattern",
                weight=0.4,
                value=score,
                description="High-risk pattern detected"
            ))
        
        if score > 0.5:
            factors.append(RiskFactor(
                category=RiskCategory.DEVICE,
                factor="anomaly_detected",
                weight=0.3,
                value=score,
                description="Device anomaly detected"
            ))
        
        if score > 0.3:
            factors.append(RiskFactor(
                category=RiskCategory.BEHAVIOR,
                factor="unusual_behavior",
                weight=0.2,
                value=score,
                description="Unusual behavior pattern"
            ))
        
        return factors


# Global mock scorer instance
mock_scorer = MockRiskScorer(ScoringMode.RANDOM)


def get_mock_scorer(mode: ScoringMode = ScoringMode.RANDOM) -> MockRiskScorer:
    """Get mock scorer instance."""
    return MockRiskScorer(mode)


async def calculate_risk_score(event: Dict[str, Any], 
                           mode: ScoringMode = ScoringMode.RANDOM) -> ScoringResult:
    """Calculate risk score using mock scorer."""
    return await mock_scorer.calculate_risk_score(event)


def update_scoring_mode(mode: ScoringMode) -> None:
    """Update global scoring mode."""
    global mock_scorer
    mock_scorer = MockRiskScorer(mode)
    logger.info(f"Updated scoring mode to: {mode.value}")