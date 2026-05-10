"""
Transaction analysis service.
"""

from typing import Dict, Any, List, Optional

from app.services.base import BaseService
from app.agents.transaction import analyze_transaction


class TransactionService(BaseService):
    """Service for transaction analysis and fraud detection."""
    
    async def analyze_transaction(
        self, 
        transaction: Dict[str, Any],
        customer_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze transaction for fraud risk."""
        self._log_operation("analyze_transaction", 
                          transaction_id=transaction.get('transaction_id'),
                          customer_id=transaction.get('customer_id'))
        
        try:
            result = await analyze_transaction(transaction, customer_history)
            return self._generate_response(result)
        except Exception as e:
            self._log_error("analyze_transaction", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    def calculate_velocity(
        self,
        transactions: List[Dict[str, Any]],
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """Calculate transaction velocity metrics."""
        from app.agents.transaction import get_transaction_agent
        
        agent = get_transaction_agent()
        velocity = agent.velocity_analyzer.calculate_velocity(transactions, window_hours)
        
        return self._generate_response({
            "window_hours": window_hours,
            "velocity": velocity.__dict__
        })
    
    def add_fraud_pattern(
        self,
        key: str,
        pattern: str,
        confidence: float,
        risk_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add fraud pattern to memory."""
        from app.agents.transaction import get_transaction_agent, FraudPattern
        
        agent = get_transaction_agent()
        
        try:
            fraud_pattern = FraudPattern(pattern)
            agent.add_fraud_pattern(key, fraud_pattern, confidence, risk_score, metadata)
            
            return self._generate_response({
                "key": key,
                "pattern": pattern,
                "confidence": confidence,
                "risk_score": risk_score
            })
        except ValueError as e:
            self._log_error("add_fraud_pattern", e)
            return self._generate_response({"error": f"Invalid pattern: {e}"}, success=False)
