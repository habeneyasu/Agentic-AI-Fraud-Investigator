"""
Investigation workflow service.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.base import BaseService
from app.services.transaction_service import TransactionService
from app.services.kyc_service import KYCService
from app.services.sanctions_service import SanctionsService
from app.services.triage_service import TriageService


class InvestigationService(BaseService):
    """Service for complete fraud investigation workflow."""
    
    def __init__(self):
        super().__init__()
        self.investigations = {}
        self.transaction_service = TransactionService()
        self.kyc_service = KYCService()
        self.sanctions_service = SanctionsService()
        self.triage_service = TriageService()
    
    async def start_investigation(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start complete investigation workflow."""
        investigation_id = investigation_data.get("investigation_id")
        self._log_operation("start_investigation", investigation_id=investigation_id)
        
        try:
            # Store investigation
            self.investigations[investigation_id] = {
                "status": "IN_PROGRESS",
                "started_at": datetime.utcnow().isoformat(),
                "data": investigation_data
            }
            
            # Run agents in parallel
            agent_results = await self._run_agents(investigation_data)
            
            # Calculate overall risk
            overall_risk = self._calculate_overall_risk(agent_results)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(overall_risk, agent_results)
            
            result = {
                "investigation_id": investigation_id,
                "status": "COMPLETED",
                "risk_score": overall_risk,
                "agent_results": agent_results,
                "final_recommendation": recommendation,
                "requires_human_review": overall_risk >= 0.6,
                "investigation_timestamp": datetime.utcnow().isoformat(),
                "completed_timestamp": datetime.utcnow().isoformat()
            }
            
            # Update investigation
            self.investigations[investigation_id].update(result)
            
            return self._generate_response(result)
        except Exception as e:
            self._log_error("start_investigation", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    def get_investigation_status(self, investigation_id: str) -> Dict[str, Any]:
        """Get investigation status."""
        status = self.investigations.get(investigation_id)
        
        if not status:
            return self._generate_response(
                {"error": "Investigation not found"}, 
                success=False
            )
        
        # Add required fields for response
        status_data = status.copy()
        status_data.update({
            "current_step": status.get("status", "UNKNOWN"),
            "progress_percentage": 100 if status.get("status") == "COMPLETED" else 50,
            "estimated_completion": None
        })
        
        return self._generate_response(status_data)
    
    def get_investigation_evidence(self, investigation_id: str) -> Dict[str, Any]:
        """Get investigation evidence."""
        investigation = self.investigations.get(investigation_id)
        
        if not investigation:
            return self._generate_response(
                {"error": "Investigation not found"}, 
                success=False
            )
        
        # Generate evidence based on investigation data
        evidence = self._generate_evidence(investigation.get("data", {}))
        
        return self._generate_response({
            "investigation_id": investigation_id,
            "evidence": evidence,
            "total_pieces": len(evidence),
            "categories": list(set(e.get('category', 'unknown') for e in evidence))
        })
    
    async def run_agent(
        self,
        investigation_id: str,
        agent_type: str,
        agent_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run specific investigation agent."""
        self._log_operation("run_agent", investigation_id=investigation_id, agent_type=agent_type)
        
        try:
            if agent_type == "transaction":
                result = await self._run_transaction_agent(agent_data)
            elif agent_type == "kyc":
                result = await self._run_kyc_agent(agent_data)
            elif agent_type == "sanctions":
                result = await self._run_sanctions_agent(agent_data)
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            return self._generate_response({
                "investigation_id": investigation_id,
                "agent": agent_type,
                "result": result,
                "timestamp": result.get('analysis_timestamp', datetime.utcnow().isoformat())
            })
        except Exception as e:
            self._log_error("run_agent", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    async def synthesize_results(
        self,
        investigation_id: str,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize results from all agents."""
        self._log_operation("synthesize_results", investigation_id=investigation_id)
        
        try:
            # Calculate overall risk
            risk_scores = [
                result.get("risk_score", 0.0) 
                for result in agent_results.values()
            ]
            overall_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
            
            # Generate recommendation
            if overall_risk_score >= 0.8:
                recommendation = "BLOCK_FREEZE"
            elif overall_risk_score >= 0.6:
                recommendation = "HUMAN_REVIEW"
            elif overall_risk_score >= 0.4:
                recommendation = "ENHANCED_MONITORING"
            else:
                recommendation = "ALLOW"
            
            synthesis = {
                "recommendation": recommendation,
                "overall_risk_score": overall_risk_score,
                "confidence": min(overall_risk_score + 0.2, 1.0),
                "synthesis_timestamp": datetime.utcnow().isoformat(),
                "agent_summary": {
                    agent: result.get("recommendation", "UNKNOWN")
                    for agent, result in agent_results.items()
                }
            }
            
            return self._generate_response({
                "investigation_id": investigation_id,
                "synthesis": synthesis,
                "final_recommendation": synthesis.get('recommendation'),
                "overall_risk_score": synthesis.get('overall_risk_score'),
                "confidence": synthesis.get('confidence'),
                "timestamp": synthesis.get('synthesis_timestamp')
            })
        except Exception as e:
            self._log_error("synthesize_results", e)
            return self._generate_response({"error": str(e)}, success=False)
    
    async def _run_agents(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all investigation agents."""
        agent_results = {}
        
        # Transaction agent
        transaction_data = {
            "transaction_id": investigation_data.get("transaction_id"),
            "customer_id": investigation_data.get("customer_id"),
            "amount": investigation_data.get("amount"),
            "location": investigation_data.get("location", ""),
            "device_id": investigation_data.get("device_info", {}).get("device_id", ""),
            "ip_address": investigation_data.get("location", {}).get("ip_address", "")
        }
        
        transaction_result = await self._run_transaction_agent(transaction_data)
        agent_results["transaction"] = transaction_result
        
        # KYC agent
        kyc_event = {
            "customer_id": investigation_data.get("customer_id"),
            "event_type": "transaction",
            "device_info": investigation_data.get("device_info"),
            "location": investigation_data.get("location")
        }
        
        kyc_result = await self._run_kyc_agent(kyc_event)
        agent_results["kyc"] = kyc_result
        
        # Sanctions agent
        entity = {
            "name": investigation_data.get("customer_id"),
            "country_code": investigation_data.get("recipient_country", ""),
            "entity_type": "customer"
        }
        
        sanctions_result = await self._run_sanctions_agent(entity)
        agent_results["sanctions"] = sanctions_result
        
        return agent_results
    
    async def _run_transaction_agent(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run transaction analysis agent."""
        # Mock customer history for demo
        customer_history = []
        
        response = await self.transaction_service.analyze_transaction(transaction_data, customer_history)
        if response["success"]:
            return response["data"]
        else:
            return {"risk_score": 0.5, "error": response["data"].get("error")}
    
    async def _run_kyc_agent(self, kyc_event: Dict[str, Any]) -> Dict[str, Any]:
        """Run KYC analysis agent."""
        response = await self.kyc_service.analyze_kyc_event(kyc_event)
        if response["success"]:
            return response["data"]
        else:
            return {"risk_score": 0.3, "error": response["data"].get("error")}
    
    async def _run_sanctions_agent(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Run sanctions analysis agent."""
        response = await self.sanctions_service.analyze_sanctions_risk(entity)
        if response["success"]:
            return response["data"]
        else:
            return {"risk_score": 0.2, "error": response["data"].get("error")}
    
    def _calculate_overall_risk(self, agent_results: Dict[str, Any]) -> float:
        """Calculate overall risk score."""
        risk_scores = [
            result.get("risk_score", 0.0) 
            for result in agent_results.values()
        ]
        return sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
    
    def _generate_recommendation(self, overall_risk: float, agent_results: Dict[str, Any]) -> str:
        """Generate final recommendation."""
        if overall_risk >= 0.8:
            return "BLOCK_FREEZE"
        elif overall_risk >= 0.6:
            return "HUMAN_REVIEW"
        elif overall_risk >= 0.4:
            return "ENHANCED_MONITORING"
        else:
            return "ALLOW"
    
    def _generate_evidence(self, investigation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate evidence based on investigation data."""
        evidence = []
        
        amount = investigation_data.get("amount", 0)
        if amount > 10000:
            evidence.append({
                "type": "transaction",
                "category": "financial",
                "description": f"High-value transaction: ${amount:,.2f}",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        if investigation_data.get("device_info"):
            evidence.append({
                "type": "kyc",
                "category": "identity",
                "description": "New device fingerprint detected",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        country = investigation_data.get("recipient_country", "")
        high_risk_countries = {"IR", "KP", "SY", "RU", "CN"}
        if country in high_risk_countries:
            evidence.append({
                "type": "sanctions",
                "category": "compliance",
                "description": f"High-risk country: {country}",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return evidence
