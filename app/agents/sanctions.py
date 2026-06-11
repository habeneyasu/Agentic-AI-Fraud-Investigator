"""Sanctions agent with country risk and sanctions list detection."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import get_logger
from app.shared.enums import RiskLevel, SanctionType
from app.shared.models import CountryRisk, SanctionsEntry, SanctionsAlert

logger = get_logger(__name__)


class SanctionsDatabase:
    """Deterministic sanctions database."""
    
    def __init__(self):
        # High-risk countries
        self.high_risk_countries = {
            'IR': {'name': 'Iran', 'risk_score': 0.9, 'sanctions': True},
            'KP': {'name': 'North Korea', 'risk_score': 0.95, 'sanctions': True},
            'SY': {'name': 'Syria', 'risk_score': 0.85, 'sanctions': True},
            'RU': {'name': 'Russia', 'risk_score': 0.8, 'sanctions': True},
            'CN': {'name': 'China', 'risk_score': 0.6, 'sanctions': False},
            'AF': {'name': 'Afghanistan', 'risk_score': 0.7, 'sanctions': True},
            'MM': {'name': 'Myanmar', 'risk_score': 0.75, 'sanctions': True},
            'BY': {'name': 'Belarus', 'risk_score': 0.7, 'sanctions': True},
            'VE': {'name': 'Venezuela', 'risk_score': 0.8, 'sanctions': True},
            'CU': {'name': 'Cuba', 'risk_score': 0.65, 'sanctions': True}
        }
        
        # Sanctioned entities (simplified)
        self.sanctioned_entities = {
            'entities': {
                'IRAN_REVOLUTIONARY_GUARD': {
                    'name': 'Islamic Revolutionary Guard Corps',
                    'type': 'organization',
                    'country': 'IR',
                    'sanction_type': SanctionType.ENTITY_SANCTION
                },
                'NORTH_KOREAN_BANK': {
                    'name': 'Korea Development Bank',
                    'type': 'financial_institution',
                    'country': 'KP',
                    'sanction_type': SanctionType.FINANCIAL_SANCTION
                },
                'RUSSIAN_BANK_1': {
                    'name': 'Sberbank',
                    'type': 'financial_institution',
                    'country': 'RU',
                    'sanction_type': SanctionType.FINANCIAL_SANCTION
                },
                'RUSSIAN_BANK_2': {
                    'name': 'VTB Bank',
                    'type': 'financial_institution',
                    'country': 'RU',
                    'sanction_type': SanctionType.FINANCIAL_SANCTION
                }
            },
            'individuals': {
                'IRAN_OFFICIAL_1': {
                    'name': 'Hassan Rouhani',
                    'type': 'individual',
                    'country': 'IR',
                    'sanction_type': SanctionType.INDIVIDUAL_SANCTION
                },
                'RUSSIA_OFFICIAL_1': {
                    'name': 'Vladimir Putin',
                    'type': 'individual',
                    'country': 'RU',
                    'sanction_type': SanctionType.INDIVIDUAL_SANCTION
                }
            }
        }
        
        # Watchlist keywords
        self.watchlist_keywords = {
            'weapons', 'nuclear', 'missile', 'military', 'terrorism',
            'drug', 'trafficking', 'money laundering', 'corruption'
        }
    
    def get_country_risk(self, country_code: str) -> Optional[CountryRisk]:
        """Get country risk assessment."""
        country_data = self.high_risk_countries.get(country_code.upper())
        if not country_data:
            return None
        
        risk_level = (
            RiskLevel.CRITICAL if country_data['risk_score'] >= 0.9
            else RiskLevel.HIGH if country_data['risk_score'] >= 0.7
            else RiskLevel.MEDIUM if country_data['risk_score'] >= 0.5
            else RiskLevel.LOW
        )
        
        return CountryRisk(
            country_code=country_code.upper(),
            country_name=country_data['name'],
            risk_level=risk_level,
            risk_score=country_data['risk_score'],
            sanctions_active=country_data['sanctions'],
            last_updated=datetime.utcnow()
        )
    
    def check_entity_sanctions(self, entity_name: str, country: str) -> List[SanctionsEntry]:
        """Check if entity is on sanctions list."""
        matches = []
        entity_lower = entity_name.lower()
        
        # Check both entities and individuals
        for category in ['entities', 'individuals']:
            for entity_id, entity_data in self.sanctioned_entities[category].items():
                if entity_data['name'].lower() in entity_lower or entity_lower in entity_data['name'].lower():
                    matches.append(SanctionsEntry(
                        entity_id=entity_id,
                        entity_name=entity_data['name'],
                        entity_type=entity_data['type'],
                        sanction_type=entity_data['sanction_type'],
                        country=entity_data['country'],
                        confidence=0.9,
                        last_seen=datetime.utcnow()
                    ))
        
        return matches


class CountryRiskAnalyzer:
    """Deterministic country risk analysis."""
    
    def __init__(self):
        self.sanctions_db = SanctionsDatabase()
        
    def analyze_country_risk(self, country_code: str, 
                            entity_name: Optional[str] = None) -> List[SanctionsAlert]:
        """Analyze country risk."""
        alerts = []
        
        # Get country risk
        country_risk = self.sanctions_db.get_country_risk(country_code)
        if not country_risk:
            return alerts
        
        # Country-level sanctions alert
        if country_risk.sanctions_active:
            alerts.append(SanctionsAlert(
                alert_type=SanctionType.COUNTRY_SANCTION,
                severity='critical' if country_risk.risk_level == RiskLevel.CRITICAL else 'high',
                confidence=country_risk.risk_score,
                description=f"Country under sanctions: {country_risk.country_name}",
                metadata={
                    'country_code': country_risk.country_code,
                    'country_name': country_risk.country_name,
                    'risk_score': country_risk.risk_score
                }
            ))
        
        # High-risk country alert
        if country_risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            alerts.append(SanctionsAlert(
                alert_type=SanctionType.TRADE_RESTRICTION,
                severity='medium',
                confidence=country_risk.risk_score * 0.8,
                description=f"High-risk country: {country_risk.country_name}",
                metadata={
                    'country_code': country_risk.country_code,
                    'risk_level': country_risk.risk_level.value
                }
            ))
        
        # Check entity sanctions if provided
        if entity_name:
            entity_matches = self.sanctions_db.check_entity_sanctions(entity_name, country_code)
            for match in entity_matches:
                alerts.append(SanctionsAlert(
                    alert_type=match.sanction_type,
                    severity='critical',
                    confidence=match.confidence,
                    description=f"Sanctioned entity detected: {match.entity_name}",
                    metadata={
                        'entity_id': match.entity_id,
                        'entity_type': match.entity_type,
                        'country': match.country
                    }
                ))
        
        return alerts


class SanctionsAgent:
    """Sanctions agent with country risk and sanctions list detection."""
    
    def __init__(self):
        self.country_analyzer = CountryRiskAnalyzer()
        # Fix 3: expose sanctions_db directly so _analyze_keywords can reach watchlist_keywords
        # without going through country_analyzer (which owns the db instance).
        self.sanctions_db = self.country_analyzer.sanctions_db
        
    async def analyze_sanctions_risk(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sanctions risk for entity."""
        entity_name = entity.get('name', '')
        country_code = entity.get('country_code', '')
        entity_type = entity.get('entity_type', 'unknown')
        
        logger.info(f"Analyzing sanctions risk for {entity_name} in {country_code}")
        
        # Analyze country risk
        country_alerts = self.country_analyzer.analyze_country_risk(country_code, entity_name)
        
        # Additional keyword analysis
        keyword_alerts = self._analyze_keywords(entity_name, entity.get('description', ''))
        
        # Combine all alerts
        all_alerts = country_alerts + keyword_alerts
        
        # Calculate overall risk score
        risk_score = self._calculate_risk_score(all_alerts)
        
        return {
            'entity_name': entity_name,
            'country_code': country_code,
            'entity_type': entity_type,
            'risk_score': risk_score,
            'alerts': [alert.__dict__ for alert in all_alerts],
            'recommendation': self._get_recommendation(risk_score, all_alerts),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    def _analyze_keywords(self, entity_name: str, description: str) -> List[SanctionsAlert]:
        """Analyze text for watchlist keywords."""
        alerts = []
        text = f"{entity_name} {description}".lower()
        
        matched_keywords = [keyword for keyword in self.sanctions_db.watchlist_keywords if keyword in text]
        
        if matched_keywords:
            alerts.append(SanctionsAlert(
                alert_type=SanctionType.TRADE_RESTRICTION,
                severity='medium',
                confidence=0.6,
                description=f"Watchlist keywords detected: {', '.join(matched_keywords)}",
                metadata={'keywords': matched_keywords}
            ))
        
        return alerts
    
    def _calculate_risk_score(self, alerts: List[SanctionsAlert]) -> float:
        """Calculate overall risk score."""
        if not alerts:
            return 0.0
        
        severity_weights = {'critical': 0.5, 'high': 0.3, 'medium': 0.2, 'low': 0.1}
        risk_score = sum(
            severity_weights.get(alert.severity, 0.1) * alert.confidence
            for alert in alerts
        )
        
        return min(risk_score, 1.0)
    
    def _get_recommendation(self, risk_score: float, alerts: List[SanctionsAlert]) -> str:
        """Get recommendation based on risk factors."""
        if risk_score >= 0.8:
            return "BLOCK_TRANSACTION"
        elif risk_score >= 0.6:
            return "REQUIRE_COMPLIANCE_REVIEW"
        elif risk_score >= 0.4:
            return "ENHANCED_DUE_DILIGENCE"
        elif alerts:
            return "MONITOR_CLOSELY"
        else:
            return "PROCEED"


# Global sanctions agent instance
sanctions_agent = SanctionsAgent()


def get_sanctions_agent() -> SanctionsAgent:
    """Get global sanctions agent instance."""
    return sanctions_agent


async def analyze_sanctions_risk(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze sanctions risk using global agent."""
    return await get_sanctions_agent().analyze_sanctions_risk(entity)