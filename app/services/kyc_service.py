"""
KYC verification service.
"""

from typing import Dict, Any, List, Optional

from app.services.base import BaseService
from app.agents.kyc_device import analyze_kyc_event


class KYCService(BaseService):
    """Service for KYC verification and device analysis."""
    
    async def analyze_kyc_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze KYC event for anomalies."""
        self._log_operation("analyze_kyc_event", 
                          customer_id=event.get('customer_id'),
                          event_type=event.get('event_type'))
        
        try:
            result = await analyze_kyc_event(event)
            return self._generate_response(result)
        except Exception as e:
            self._log_error("analyze_kyc_event", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    def check_device(self, customer_id: str, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check device for suspicious activity."""
        from app.agents.kyc_device import get_kyc_device_agent
        
        agent = get_kyc_device_agent()
        anomalies = agent.device_analyzer.analyze_device(device_info, customer_id)
        
        return self._generate_response({
            "customer_id": customer_id,
            "device_id": device_info.get('device_id'),
            "anomalies": [a.__dict__ for a in anomalies],
            "risk_score": agent._calculate_risk_score(anomalies)
        })
    
    def check_geo_location(self, customer_id: str, location: Dict[str, Any]) -> Dict[str, Any]:
        """Check geo-location for anomalies."""
        from app.agents.kyc_device import get_kyc_device_agent, GeoLocation
        
        agent = get_kyc_device_agent()
        geo_loc = GeoLocation(**location)
        anomalies = agent.geo_analyzer.analyze_location(geo_loc, customer_id)
        
        return self._generate_response({
            "customer_id": customer_id,
            "location": location,
            "anomalies": [a.__dict__ for a in anomalies],
            "risk_score": agent._calculate_risk_score(anomalies)
        })
    
    def check_impossible_travel(
        self,
        customer_id: str,
        from_location: Dict[str, Any],
        to_location: Dict[str, Any],
        timestamp_from: str,
        timestamp_to: str
    ) -> Dict[str, Any]:
        """Check for impossible travel between locations."""
        from app.agents.kyc_device import get_kyc_device_agent, GeoLocation
        from datetime import datetime
        
        agent = get_kyc_device_agent()
        
        from_loc = GeoLocation(**from_location)
        from_loc.last_seen = datetime.fromisoformat(timestamp_from)
        
        to_loc = GeoLocation(**to_location)
        to_loc.last_seen = datetime.fromisoformat(timestamp_to)
        
        is_impossible = agent.geo_analyzer._is_impossible_travel(from_loc, to_loc)
        distance = agent.geo_analyzer._calculate_distance(
            from_loc.latitude, from_loc.longitude,
            to_loc.latitude, to_loc.longitude
        )
        
        return self._generate_response({
            "customer_id": customer_id,
            "impossible_travel": is_impossible,
            "distance_km": distance,
            "time_diff_hours": (datetime.fromisoformat(timestamp_to) - 
                              datetime.fromisoformat(timestamp_from)).total_seconds() / 3600
        })
