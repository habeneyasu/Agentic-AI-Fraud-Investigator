"""
Sanctions screening service.
"""

from typing import Dict, Any, List, Optional

from app.services.base import BaseService
from app.agents.sanctions import analyze_sanctions_risk


class SanctionsService(BaseService):
    """Service for sanctions screening and country risk analysis."""
    
    async def analyze_sanctions_risk(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze entity for sanctions risk."""
        self._log_operation("analyze_sanctions_risk", 
                          entity_name=entity.get('name'),
                          country_code=entity.get('country_code'))
        
        try:
            result = await analyze_sanctions_risk(entity)
            return self._generate_response(result)
        except Exception as e:
            self._log_error("analyze_sanctions_risk", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    def get_country_risk(self, country_code: str) -> Dict[str, Any]:
        """Get country risk assessment."""
        from app.agents.sanctions import get_sanctions_agent
        
        agent = get_sanctions_agent()
        country_risk = agent.country_analyzer.sanctions_db.get_country_risk(country_code)
        
        if not country_risk:
            return self._generate_response(
                {"error": "Country not found in risk database"}, 
                success=False
            )
        
        return self._generate_response({
            "country_code": country_risk.country_code,
            "country_name": country_risk.country_name,
            "risk_level": country_risk.risk_level.value,
            "risk_score": country_risk.risk_score,
            "sanctions_active": country_risk.sanctions_active
        })
    
    def check_entity_sanctions(self, entity_name: str, country: str) -> Dict[str, Any]:
        """Check if entity is on sanctions list."""
        from app.agents.sanctions import get_sanctions_agent
        
        agent = get_sanctions_agent()
        matches = agent.country_analyzer.sanctions_db.check_entity_sanctions(entity_name, country)
        
        return self._generate_response({
            "entity_name": entity_name,
            "country": country,
            "sanctions_matches": [match.__dict__ for match in matches],
            "is_sanctioned": len(matches) > 0,
            "match_count": len(matches)
        })
    
    def check_watchlist_keywords(self, text: str) -> Dict[str, Any]:
        """Check text for watchlist keywords."""
        from app.agents.sanctions import get_sanctions_agent
        
        agent = get_sanctions_agent()
        alerts = agent._analyze_keywords("", text)
        
        return self._generate_response({
            "text": text,
            "watchlist_alerts": [alert.__dict__ for alert in alerts],
            "keywords_detected": len(alerts) > 0,
            "matched_keywords": [alert.metadata.get('keywords', []) for alert in alerts 
                               if alert.metadata.get('keywords')]
        })
    
    def get_high_risk_countries(self) -> Dict[str, Any]:
        """Get list of high-risk countries."""
        from app.agents.sanctions import get_sanctions_agent
        
        agent = get_sanctions_agent()
        high_risk = agent.country_analyzer.sanctions_db.high_risk_countries
        
        countries = [
            {
                "country_code": code,
                "country_name": data['name'],
                "risk_score": data['risk_score'],
                "sanctions_active": data['sanctions']
            }
            for code, data in high_risk.items()
        ]
        
        return self._generate_response({"high_risk_countries": countries})
