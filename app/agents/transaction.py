"""Transaction agent with velocity analysis and fraud memory lookup."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from app.core.logging import get_logger

logger = get_logger(__name__)


class FraudPattern(str, Enum):
    """Fraud pattern types."""
    VELOCITY_ANOMALY = "velocity_anomaly"
    FREQUENCY_SPIKE = "frequency_spike"
    AMOUNT_ANOMALY = "amount_anomaly"
    LOCATION_ANOMALY = "location_anomaly"
    DEVICE_ANOMALY = "device_anomaly"
    KNOWN_FRAUDSTER = "known_fraudster"
    SYNTHETIC_IDENTITY = "synthetic_identity"


@dataclass
class TransactionVelocity:
    """Transaction velocity metrics."""
    transaction_count: int
    total_amount: float
    average_amount: float
    max_amount: float
    min_amount: float
    time_window_hours: int
    unique_merchants: int
    unique_locations: int
    unique_devices: int


@dataclass
class FraudMemory:
    """Fraud memory entry for deterministic lookup."""
    pattern: FraudPattern
    confidence: float
    last_seen: datetime
    frequency: int
    risk_score: float
    metadata: Dict[str, Any]


class FraudMemoryLookup:
    """Deterministic fraud memory lookup system."""
    
    def __init__(self):
        self._memory: Dict[str, List[FraudMemory]] = defaultdict(list)
        
    def add_fraud_pattern(self, key: str, pattern: FraudPattern, 
                        confidence: float, risk_score: float,
                        metadata: Dict[str, Any] = None) -> None:
        """Add fraud pattern to memory."""
        memory_entry = FraudMemory(
            pattern=pattern,
            confidence=confidence,
            last_seen=datetime.utcnow(),
            frequency=1,
            risk_score=risk_score,
            metadata=metadata or {}
        )
        
        # Update existing pattern or add new
        existing_patterns = self._memory[key]
        for existing in existing_patterns:
            if existing.pattern == pattern:
                existing.frequency += 1
                existing.last_seen = datetime.utcnow()
                existing.confidence = max(existing.confidence, confidence)
                return
        
        self._memory[key].append(memory_entry)
    
    def lookup_fraud_patterns(self, key: str) -> List[FraudMemory]:
        """Lookup fraud patterns for given key."""
        patterns = self._memory.get(key, [])
        return sorted(patterns, key=lambda x: (x.confidence, x.last_seen), reverse=True)
    
    def get_high_risk_patterns(self, min_confidence: float = 0.7) -> List[FraudMemory]:
        """Get all high-risk patterns."""
        high_risk = []
        for patterns in self._memory.values():
            for pattern in patterns:
                if pattern.confidence >= min_confidence:
                    high_risk.append(pattern)
        return sorted(high_risk, key=lambda x: x.risk_score, reverse=True)


class TransactionVelocityAnalyzer:
    """Deterministic transaction velocity analysis."""
    
    def __init__(self):
        self.time_windows = [1, 6, 24, 168]  # hours: 1h, 6h, 24h, 7d
        
    def calculate_velocity(self, transactions: List[Dict[str, Any]], 
                       window_hours: int) -> TransactionVelocity:
        """Calculate transaction velocity for time window."""
        cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
        
        recent_transactions = [
            tx for tx in transactions 
            if datetime.fromisoformat(tx['timestamp']) >= cutoff_time
        ]
        
        if not recent_transactions:
            return TransactionVelocity(0, 0.0, 0.0, 0.0, 0.0, window_hours, 0, 0, 0)
        
        amounts = [tx['amount'] for tx in recent_transactions]
        merchants = set(tx.get('merchant_id', '') for tx in recent_transactions)
        locations = set(tx.get('location', '') for tx in recent_transactions)
        devices = set(tx.get('device_id', '') for tx in recent_transactions)
        
        return TransactionVelocity(
            transaction_count=len(recent_transactions),
            total_amount=sum(amounts),
            average_amount=sum(amounts) / len(amounts),
            max_amount=max(amounts),
            min_amount=min(amounts),
            time_window_hours=window_hours,
            unique_merchants=len(merchants),
            unique_locations=len(locations),
            unique_devices=len(devices)
        )
    
    def detect_velocity_anomalies(self, velocities: List[TransactionVelocity],
                               baseline_velocity: Optional[TransactionVelocity] = None) -> List[Dict[str, Any]]:
        """Detect velocity anomalies using deterministic rules."""
        anomalies = []
        
        for velocity in velocities:
            if baseline_velocity:
                count_ratio = velocity.transaction_count / max(baseline_velocity.transaction_count, 1)
                amount_ratio = velocity.total_amount / max(baseline_velocity.total_amount, 1)
                
                if count_ratio > 5.0:
                    anomalies.append({
                        'type': FraudPattern.VELOCITY_ANOMALY,
                        'severity': 'high',
                        'count_ratio': count_ratio,
                        'description': f"Transaction count increased by {count_ratio:.1f}x"
                    })
                
                if amount_ratio > 10.0:
                    anomalies.append({
                        'type': FraudPattern.AMOUNT_ANOMALY,
                        'severity': 'high',
                        'amount_ratio': amount_ratio,
                        'description': f"Transaction amount increased by {amount_ratio:.1f}x"
                    })
            
            if velocity.transaction_count > 100:
                anomalies.append({
                    'type': FraudPattern.FREQUENCY_SPIKE,
                    'severity': 'medium',
                    'count': velocity.transaction_count,
                    'description': f"High transaction frequency: {velocity.transaction_count} in {velocity.time_window_hours}h"
                })
            
            if velocity.max_amount > 10000:
                anomalies.append({
                    'type': FraudPattern.AMOUNT_ANOMALY,
                    'severity': 'medium',
                    'amount': velocity.max_amount,
                    'description': f"High value transaction: ${velocity.max_amount:,.2f}"
                })
        
        return anomalies


class TransactionAgent:
    """Transaction agent with velocity analysis and fraud memory lookup."""
    
    def __init__(self):
        self.fraud_memory = FraudMemoryLookup()
        self.velocity_analyzer = TransactionVelocityAnalyzer()
        self.baseline_velocities: Dict[str, TransactionVelocity] = {}
        
    async def analyze_transaction(self, transaction: Dict[str, Any],
                             customer_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze transaction with deterministic rules."""
        customer_id = transaction.get('customer_id')
        transaction_id = transaction.get('transaction_id')
        
        # Calculate velocity metrics
        velocities = [
            self.velocity_analyzer.calculate_velocity(customer_history + [transaction], window)
            for window in self.velocity_analyzer.time_windows
        ]
        
        # Detect anomalies and lookup patterns
        baseline = self.baseline_velocities.get(customer_id)
        velocity_anomalies = self.velocity_analyzer.detect_velocity_anomalies(velocities, baseline)
        
        fraud_patterns = []
        for key in [customer_id, transaction.get('device_id'), transaction.get('location'), 
                     transaction.get('merchant_id'), transaction.get('ip_address')]:
            if key:
                fraud_patterns.extend(self.fraud_memory.lookup_fraud_patterns(key))
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(velocity_anomalies, fraud_patterns)
        
        # Update baseline for low-risk transactions
        if risk_score < 0.3:
            self.baseline_velocities[customer_id] = velocities[2]
        
        return {
            'transaction_id': transaction_id,
            'customer_id': customer_id,
            'risk_score': risk_score,
            'velocity_metrics': [v.__dict__ for v in velocities],
            'velocity_anomalies': velocity_anomalies,
            'fraud_patterns': [p.__dict__ for p in fraud_patterns],
            'recommendation': self._get_recommendation(risk_score, velocity_anomalies, fraud_patterns),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_risk_score(self, velocity_anomalies: List[Dict[str, Any]],
                           fraud_patterns: List[FraudMemory]) -> float:
        """Calculate deterministic risk score."""
        risk_score = 0.0
        
        for anomaly in velocity_anomalies:
            risk_score += {'high': 0.4, 'medium': 0.2}.get(anomaly['severity'], 0.1)
        
        for pattern in fraud_patterns:
            risk_score += pattern.confidence * pattern.risk_score * 0.3
        
        return min(risk_score, 1.0)
    
    def _get_recommendation(self, risk_score: float,
                          velocity_anomalies: List[Dict[str, Any]],
                          fraud_patterns: List[FraudMemory]) -> str:
        """Get deterministic recommendation."""
        if risk_score >= 0.8:
            return "BLOCK_TRANSACTION"
        elif risk_score >= 0.6:
            return "REQUIRE_ADDITIONAL_VERIFICATION"
        elif risk_score >= 0.4:
            return "FLAG_FOR_REVIEW"
        elif velocity_anomalies or fraud_patterns:
            return "MONITOR_CLOSELY"
        return "APPROVE"
    
    def add_fraud_pattern(self, key: str, pattern: FraudPattern,
                        confidence: float, risk_score: float,
                        metadata: Dict[str, Any] = None) -> None:
        """Add fraud pattern to memory."""
        self.fraud_memory.add_fraud_pattern(key, pattern, confidence, risk_score, metadata)
    
    def update_baseline(self, customer_id: str, transactions: List[Dict[str, Any]]) -> None:
        """Update baseline velocity for customer."""
        self.baseline_velocities[customer_id] = self.velocity_analyzer.calculate_velocity(transactions, 24)


# Global transaction agent instance
transaction_agent = TransactionAgent()


def get_transaction_agent() -> TransactionAgent:
    """Get global transaction agent instance."""
    return transaction_agent


async def analyze_transaction(transaction: Dict[str, Any],
                       customer_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze transaction using global agent."""
    return await get_transaction_agent().analyze_transaction(transaction, customer_history)