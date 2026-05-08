"""KYC agent with device, geo, and login anomaly detection."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import math

from app.core.logging import get_logger

logger = get_logger(__name__)


class AnomalyType(str, Enum):
    """KYC anomaly types."""
    NEW_DEVICE = "new_device"
    SUSPICIOUS_DEVICE = "suspicious_device"
    GEO_LOCATION_ANOMALY = "geo_location_anomaly"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    HIGH_RISK_LOCATION = "high_risk_location"
    UNUSUAL_TIME = "unusual_time"
    MULTIPLE_FAILED_ATTEMPTS = "multiple_failed_attempts"
    ACCOUNT_TAKEOVER = "account_takeover"


@dataclass
class DeviceInfo:
    """Device information for KYC analysis."""
    device_id: str
    device_type: str
    user_agent: str
    ip_address: str
    fingerprint: Dict[str, Any]
    first_seen: datetime
    last_seen: datetime
    usage_count: int
    is_trusted: bool = False


@dataclass
class GeoLocation:
    """Geographic location information."""
    ip_address: str
    country: str
    city: str
    latitude: float
    longitude: float
    isp: str
    is_proxy: bool
    is_vpn: bool
    risk_score: float
    last_seen: datetime = datetime.utcnow()


@dataclass
class LoginAttempt:
    """Login attempt information."""
    timestamp: datetime
    device_id: str
    ip_address: str
    location: GeoLocation
    success: bool
    failure_reason: Optional[str] = None


@dataclass
class KYCAnomaly:
    """KYC anomaly detection result."""
    anomaly_type: AnomalyType
    severity: str
    confidence: float
    description: str
    metadata: Dict[str, Any]


class DeviceAnalyzer:
    """Deterministic device analysis for KYC."""
    
    def __init__(self):
        self.known_devices: Dict[str, DeviceInfo] = {}
        
    def analyze_device(self, device_info: Dict[str, Any], 
                    customer_id: str) -> List[KYCAnomaly]:
        """Analyze device for anomalies."""
        anomalies = []
        device_id = device_info.get('device_id')
        
        if not device_id:
            return anomalies
        
        # Check if device is known
        if device_id not in self.known_devices:
            anomalies.append(KYCAnomaly(
                anomaly_type=AnomalyType.NEW_DEVICE,
                severity='medium',
                confidence=0.8,
                description=f"New device detected: {device_id}",
                metadata={'device_id': device_id, 'customer_id': customer_id}
            ))
        
        # Analyze device fingerprint
        fingerprint = device_info.get('fingerprint', {})
        if self._is_suspicious_fingerprint(fingerprint):
            anomalies.append(KYCAnomaly(
                anomaly_type=AnomalyType.SUSPICIOUS_DEVICE,
                severity='high',
                confidence=0.9,
                description="Suspicious device fingerprint detected",
                metadata={'fingerprint': fingerprint, 'device_id': device_id}
            ))
        
        return anomalies
    
    def _is_suspicious_fingerprint(self, fingerprint: Dict[str, Any]) -> bool:
        """Check if device fingerprint is suspicious."""
        suspicious_indicators = [
            not fingerprint.get('screen_resolution'),
            not fingerprint.get('timezone'),
            fingerprint.get('browser') in ['HeadlessChrome', 'PhantomJS'],
            fingerprint.get('is_bot', False),
            fingerprint.get('is_proxy', False)
        ]
        return any(suspicious_indicators)


class GeoLocationAnalyzer:
    """Deterministic geo-location analysis for KYC."""
    
    def __init__(self):
        self.high_risk_countries = {'CN', 'RU', 'KP', 'IR', 'SY'}
        self.recent_locations: Dict[str, List[GeoLocation]] = defaultdict(list)
        
    def analyze_location(self, location: GeoLocation, 
                      customer_id: str) -> List[KYCAnomaly]:
        """Analyze geo-location for anomalies."""
        anomalies = []
        
        # Check high-risk country
        if location.country in self.high_risk_countries:
            anomalies.append(KYCAnomaly(
                anomaly_type=AnomalyType.HIGH_RISK_LOCATION,
                severity='high',
                confidence=0.8,
                description=f"High-risk location: {location.country}",
                metadata={'country': location.country, 'ip': location.ip_address}
            ))
        
        # Check for proxy/VPN
        if location.is_proxy or location.is_vpn:
            anomalies.append(KYCAnomaly(
                anomaly_type=AnomalyType.GEO_LOCATION_ANOMALY,
                severity='medium',
                confidence=0.7,
                description="Proxy/VPN detected",
                metadata={'ip': location.ip_address, 'is_proxy': location.is_proxy}
            ))
        
        # Check for impossible travel
        recent_locations = self.recent_locations.get(customer_id, [])
        if recent_locations:
            last_location = recent_locations[-1]
            if self._is_impossible_travel(last_location, location):
                anomalies.append(KYCAnomaly(
                    anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL,
                    severity='high',
                    confidence=0.9,
                    description="Impossible travel detected",
                    metadata={
                        'from_location': last_location.__dict__,
                        'to_location': location.__dict__
                    }
                ))
        
        # Update recent locations (keep last 10)
        self.recent_locations[customer_id].append(location)
        if len(self.recent_locations[customer_id]) > 10:
            self.recent_locations[customer_id].pop(0)
        
        return anomalies
    
    def _is_impossible_travel(self, loc1: GeoLocation, loc2: GeoLocation) -> bool:
        """Check if travel between locations is impossible."""
        distance = self._calculate_distance(loc1.latitude, loc1.longitude, 
                                       loc2.latitude, loc2.longitude)
        time_diff = abs((loc2.last_seen - loc1.last_seen).total_seconds()) / 3600
        max_possible_distance = 1000  # km per hour
        
        return distance > (max_possible_distance * time_diff)
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                         lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in km."""
        R = 6371  # Earth's radius in km
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
              math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


class LoginPatternAnalyzer:
    """Deterministic login pattern analysis for KYC."""
    
    def __init__(self):
        self.login_history: Dict[str, List[LoginAttempt]] = defaultdict(list)
        
    def analyze_login_pattern(self, login_attempt: LoginAttempt, 
                           customer_id: str) -> List[KYCAnomaly]:
        """Analyze login pattern for anomalies."""
        anomalies = []
        history = self.login_history.get(customer_id, [])
        
        # Check for unusual time
        if self._is_unusual_time(login_attempt.timestamp, history):
            anomalies.append(KYCAnomaly(
                anomaly_type=AnomalyType.UNUSUAL_TIME,
                severity='low',
                confidence=0.6,
                description="Login at unusual time",
                metadata={'timestamp': login_attempt.timestamp.isoformat()}
            ))
        
        # Check for multiple failed attempts
        recent_failures = [
            attempt for attempt in history[-10:]
            if not attempt.success and 
            (login_attempt.timestamp - attempt.timestamp).total_seconds() < 3600
        ]
        
        if len(recent_failures) >= 3:
            anomalies.append(KYCAnomaly(
                anomaly_type=AnomalyType.MULTIPLE_FAILED_ATTEMPTS,
                severity='high',
                confidence=0.8,
                description=f"Multiple failed login attempts: {len(recent_failures)}",
                metadata={'failure_count': len(recent_failures)}
            ))
        
        # Check for account takeover indicators
        if self._is_account_takeover(login_attempt, history):
            anomalies.append(KYCAnomaly(
                anomaly_type=AnomalyType.ACCOUNT_TAKEOVER,
                severity='critical',
                confidence=0.9,
                description="Account takeover indicators detected",
                metadata={'device_id': login_attempt.device_id}
            ))
        
        # Update login history (keep last 50)
        self.login_history[customer_id].append(login_attempt)
        if len(self.login_history[customer_id]) > 50:
            self.login_history[customer_id].pop(0)
        
        return anomalies
    
    def _is_unusual_time(self, timestamp: datetime, history: List[LoginAttempt]) -> bool:
        """Check if login time is unusual for the user."""
        if len(history) < 5:
            return False
        
        historical_hours = [attempt.timestamp.hour for attempt in history]
        current_hour = timestamp.hour
        frequency = historical_hours.count(current_hour) / len(historical_hours)
        
        return frequency < 0.1
    
    def _is_account_takeover(self, login_attempt: LoginAttempt, 
                           history: List[LoginAttempt]) -> bool:
        """Check for account takeover indicators."""
        if len(history) < 3:
            return False
        
        recent_devices = {attempt.device_id for attempt in history[-5:]}
        recent_locations = {attempt.ip_address for attempt in history[-5:]}
        
        return (login_attempt.device_id not in recent_devices and 
                login_attempt.ip_address not in recent_locations)


class KYCDeviceAgent:
    """KYC agent with device, geo, and login anomaly detection."""
    
    def __init__(self):
        self.device_analyzer = DeviceAnalyzer()
        self.geo_analyzer = GeoLocationAnalyzer()
        self.login_analyzer = LoginPatternAnalyzer()
        
    async def analyze_kyc_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze KYC event for anomalies."""
        customer_id = event.get('customer_id')
        event_type = event.get('event_type', 'login')
        
        anomalies = []
        
        # Analyze device
        if 'device_info' in event:
            anomalies.extend(self.device_analyzer.analyze_device(
                event['device_info'], customer_id
            ))
        
        # Analyze geo-location
        if 'location' in event:
            anomalies.extend(self.geo_analyzer.analyze_location(
                GeoLocation(**event['location']), customer_id
            ))
        
        # Analyze login pattern
        if event_type == 'login' and 'login_attempt' in event:
            anomalies.extend(self.login_analyzer.analyze_login_pattern(
                LoginAttempt(**event['login_attempt']), customer_id
            ))
        
        # Calculate overall risk score
        risk_score = self._calculate_risk_score(anomalies)
        
        return {
            'customer_id': customer_id,
            'event_type': event_type,
            'risk_score': risk_score,
            'anomalies': [a.__dict__ for a in anomalies],
            'recommendation': self._get_recommendation(risk_score, anomalies),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_risk_score(self, anomalies: List[KYCAnomaly]) -> float:
        """Calculate overall risk score."""
        if not anomalies:
            return 0.0
        
        severity_weights = {'critical': 0.5, 'high': 0.3, 'medium': 0.2, 'low': 0.1}
        risk_score = sum(
            severity_weights.get(anomaly.severity, 0.1) * anomaly.confidence
            for anomaly in anomalies
        )
        
        return min(risk_score, 1.0)
    
    def _get_recommendation(self, risk_score: float, 
                         anomalies: List[KYCAnomaly]) -> str:
        """Get recommendation based on risk factors."""
        if risk_score >= 0.8:
            return "BLOCK_ACCESS"
        elif risk_score >= 0.6:
            return "REQUIRE_ADDITIONAL_VERIFICATION"
        elif risk_score >= 0.4:
            return "FLAG_FOR_REVIEW"
        elif anomalies:
            return "MONITOR_CLOSELY"
        return "ALLOW_ACCESS"


# Global KYC device agent instance
kyc_device_agent = KYCDeviceAgent()


def get_kyc_device_agent() -> KYCDeviceAgent:
    """Get global KYC device agent instance."""
    return kyc_device_agent


async def analyze_kyc_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze KYC event using global agent."""
    return await get_kyc_device_agent().analyze_kyc_event(event)