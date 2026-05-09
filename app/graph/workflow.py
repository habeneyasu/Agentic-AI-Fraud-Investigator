"""LangGraph workflow definition with nodes, edges, and conditional routing."""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio
from asyncio import Semaphore
import time

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor

from app.core.logging import get_logger
from app.graph.state import InvestigationState, InvestigationStatus
from app.agents.transaction import analyze_transaction
from app.agents.kyc_device import analyze_kyc_event
from app.agents.sanctions import analyze_sanctions_risk
from app.graph.scoring import calculate_risk_score
from app.services.fraud_memory import get_fraud_memory_service

logger = get_logger(__name__)


class NodeType(str, Enum):
    """LangGraph node types."""
    START = "start"
    TRANSACTION_ANALYSIS = "transaction_analysis"
    KYC_ANALYSIS = "kyc_analysis"
    SANCTIONS_CHECK = "sanctions_check"
    RISK_SCORING = "risk_scoring"
    DECISION = "decision"
    INVESTIGATION = "investigation"
    ESCALATION = "escalation"
    RESOLUTION = "resolution"
    END = "end"


class EdgeType(str, Enum):
    """LangGraph edge types."""
    CONDITIONAL = "conditional"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    RETRY = "retry"


@dataclass
class WorkflowNode:
    """Workflow node definition."""
    node_id: str
    node_type: NodeType
    function: Optional[Callable]
    conditions: Optional[Dict[str, Any]]
    max_retries: int = 3
    timeout: float = 30.0
    semaphore_key: Optional[str] = None


@dataclass
class WorkflowEdge:
    """Workflow edge definition."""
    from_node: str
    to_node: str
    edge_type: EdgeType
    condition: Optional[str] = None
    weight: float = 1.0


class WorkflowExecutor:
    """LangGraph workflow executor with concurrency control."""
    
    def __init__(self):
        self.semaphores: Dict[str, Semaphore] = {}
        self.max_concurrent_nodes = 10
        self.retry_delays = [1.0, 2.0, 4.0, 8.0]
        
    async def _acquire_semaphore(self, key: str) -> Optional[Semaphore]:
        """Acquire semaphore for node execution."""
        if key not in self.semaphores:
            self.semaphores[key] = Semaphore(3)
        return self.semaphores[key]
        
    async def execute_node_with_semaphore(self, node: WorkflowNode, 
                                     state: InvestigationState) -> Dict[str, Any]:
        """Execute workflow node with semaphore control."""
        semaphore = await self._acquire_semaphore(node.semaphore_key) if node.semaphore_key else None
        
        try:
            if semaphore:
                async with semaphore:
                    return await self._execute_node_with_retry(node, state)
            else:
                return await self._execute_node_with_retry(node, state)
        except Exception as e:
            logger.error(f"Node {node.node_id} execution failed: {e}")
            raise
        
    async def _execute_node_with_retry(self, node: WorkflowNode, 
                                  state: InvestigationState) -> Dict[str, Any]:
        """Execute node with retry mechanism."""
        last_exception = None
        
        for attempt in range(node.max_retries):
            try:
                start_time = time.time()
                result = await asyncio.wait_for(
                    node.function(state), 
                    timeout=node.timeout
                )
                
                logger.info(f"Node {node.node_id} completed on attempt {attempt + 1}")
                return result
                
            except asyncio.TimeoutError:
                last_exception = f"Timeout after {node.timeout}s"
                logger.warning(f"Node {node.node_id} timeout on attempt {attempt + 1}")
                
            except Exception as e:
                last_exception = str(e)
                logger.warning(f"Node {node.node_id} failed on attempt {attempt + 1}: {e}")
            
            if attempt < node.max_retries - 1:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                logger.info(f"Retrying node {node.node_id} in {delay}s...")
                await asyncio.sleep(delay)
        
        raise Exception(f"Node {node.node_id} failed after {node.max_retries} attempts: {last_exception}")
    
    def _evaluate_condition(self, condition: str, state: InvestigationState) -> bool:
        """Evaluate routing condition."""
        try:
            if condition.startswith("risk_score >"):
                threshold = float(condition.split(">")[1].strip())
                return state.risk_score > threshold
            elif condition.startswith("status == "):
                status_value = condition.split("==")[1].strip().strip('"\'')
                return state.status.value == status_value
            elif condition.startswith("has_anomalies"):
                return len(state.anomalies) > 0
            elif condition.startswith("customer_age >"):
                threshold = float(condition.split(">")[1].strip())
                customer_age = state.metadata.get('customer_age', 0)
                return customer_age > threshold
            else:
                return True
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return True


class LangGraphWorkflow:
    """LangGraph workflow with conditional routing and concurrency control."""
    
    def __init__(self):
        self.executor = WorkflowExecutor()
        self.graph = self._build_workflow_graph()
        self.tool_executor = ToolExecutor()
        
    def _build_workflow_graph(self) -> StateGraph:
        """Build LangGraph with nodes and edges."""
        workflow = StateGraph(InvestigationState)
        
        # Define nodes
        nodes = {
            NodeType.START: WorkflowNode(
                node_id="start",
                node_type=NodeType.START,
                function=self._start_investigation
            ),
            NodeType.TRANSACTION_ANALYSIS: WorkflowNode(
                node_id="transaction_analysis",
                node_type=NodeType.TRANSACTION_ANALYSIS,
                function=self._analyze_transactions,
                semaphore_key="transaction_analysis"
            ),
            NodeType.KYC_ANALYSIS: WorkflowNode(
                node_id="kyc_analysis",
                node_type=NodeType.KYC_ANALYSIS,
                function=self._analyze_kyc,
                semaphore_key="kyc_analysis"
            ),
            NodeType.SANCTIONS_CHECK: WorkflowNode(
                node_id="sanctions_check",
                node_type=NodeType.SANCTIONS_CHECK,
                function=self._check_sanctions,
                semaphore_key="sanctions_check"
            ),
            NodeType.RISK_SCORING: WorkflowNode(
                node_id="risk_scoring",
                node_type=NodeType.RISK_SCORING,
                function=self._score_risk,
                semaphore_key="risk_scoring"
            ),
            NodeType.DECISION: WorkflowNode(
                node_id="decision",
                node_type=NodeType.DECISION,
                function=self._make_decision,
                conditions={"min_risk_score": 0.7}
            ),
            NodeType.INVESTIGATION: WorkflowNode(
                node_id="investigation",
                node_type=NodeType.INVESTIGATION,
                function=self._start_investigation,
                conditions={"high_risk": True}
            ),
            NodeType.ESCALATION: WorkflowNode(
                node_id="escalation",
                node_type=NodeType.ESCALATION,
                function=self._escalate_case,
                conditions={"critical_risk": True}
            ),
            NodeType.RESOLUTION: WorkflowNode(
                node_id="resolution",
                node_type=NodeType.RESOLUTION,
                function=self._resolve_case,
                conditions={"resolved": True}
            )
        }
        
        # Add nodes to graph
        for node_id, node in nodes.items():
            workflow.add_node(node_id, node.function)
        
        # Define edges with conditional routing
        edges = [
            # Sequential edges
            WorkflowEdge(NodeType.START, NodeType.TRANSACTION_ANALYSIS, EdgeType.SEQUENTIAL),
            WorkflowEdge(NodeType.TRANSACTION_ANALYSIS, NodeType.KYC_ANALYSIS, EdgeType.SEQUENTIAL),
            WorkflowEdge(NodeType.KYC_ANALYSIS, NodeType.SANCTIONS_CHECK, EdgeType.SEQUENTIAL),
            WorkflowEdge(NodeType.SANCTIONS_CHECK, NodeType.RISK_SCORING, EdgeType.SEQUENTIAL),
            
            # Conditional edges from decision
            WorkflowEdge(NodeType.DECISION, NodeType.INVESTIGATION, EdgeType.CONDITIONAL, "high_risk"),
            WorkflowEdge(NodeType.DECISION, NodeType.RESOLUTION, EdgeType.CONDITIONAL, "low_risk"),
            
            # Conditional edges from investigation
            WorkflowEdge(NodeType.INVESTIGATION, NodeType.ESCALATION, EdgeType.CONDITIONAL, "critical_risk"),
            WorkflowEdge(NodeType.INVESTIGATION, NodeType.RESOLUTION, EdgeType.CONDITIONAL, "resolved"),
            
            # Conditional edges from escalation
            WorkflowEdge(NodeType.ESCALATION, NodeType.RESOLUTION, EdgeType.CONDITIONAL, "resolved"),
        ]
        
        # Add edges to graph
        for edge in edges:
            if edge.edge_type == EdgeType.CONDITIONAL:
                workflow.add_conditional_edge(
                    edge.from_node,
                    edge.to_node,
                    lambda state: self.executor._evaluate_condition(edge.condition, state)
                )
            else:
                workflow.add_edge(edge.from_node, edge.to_node)
        
        workflow.set_entry_point(NodeType.START)
        workflow.set_finish_point(NodeType.RESOLUTION)
        
        return workflow
    
    async def _start_investigation(self, state: InvestigationState) -> Dict[str, Any]:
        """Start investigation process."""
        logger.info(f"Starting investigation for case {state.case_id}")
        return {"status": "investigation_started", "timestamp": datetime.utcnow().isoformat()}
    
    async def _analyze_transactions(self, state: InvestigationState) -> Dict[str, Any]:
        """Analyze transactions for fraud patterns."""
        logger.info(f"Analyzing transactions for case {state.case_id}")
        
        if not state.transaction_data:
            return {"anomalies": [], "risk_score": 0.0}
        
        all_anomalies = []
        for transaction in state.transaction_data:
            result = await analyze_transaction(transaction, state.customer_history)
            all_anomalies.extend(result.get('anomalies', []))
        
        return {"anomalies": all_anomalies, "transaction_count": len(state.transaction_data)}
    
    async def _analyze_kyc(self, state: InvestigationState) -> Dict[str, Any]:
        """Analyze KYC data for device and geo anomalies."""
        logger.info(f"Analyzing KYC for case {state.case_id}")
        
        if not state.kyc_data:
            return {"kyc_anomalies": [], "risk_score": 0.0}
        
        all_kyc_anomalies = []
        for kyc_event in state.kyc_data:
            result = await analyze_kyc_event(kyc_event)
            all_kyc_anomalies.extend(result.get('anomalies', []))
        
        return {"kyc_anomalies": all_kyc_anomalies, "kyc_events_count": len(state.kyc_data)}
    
    async def _check_sanctions(self, state: InvestigationState) -> Dict[str, Any]:
        """Check sanctions for entities."""
        logger.info(f"Checking sanctions for case {state.case_id}")
        
        if not state.entities:
            return {"sanctions_hits": [], "risk_score": 0.0}
        
        all_sanctions = []
        for entity in state.entities:
            result = await analyze_sanctions_risk(entity)
            if result.get('risk_score', 0) > 0.5:
                all_sanctions.append(result)
        
        return {"sanctions_hits": all_sanctions, "entities_checked": len(state.entities)}
    
    async def _score_risk(self, state: InvestigationState) -> Dict[str, Any]:
        """Calculate overall risk score."""
        logger.info(f"Calculating risk score for case {state.case_id}")
        
        combined_event = {
            "transaction_anomalies": state.anomalies,
            "kyc_anomalies": state.kyc_anomalies,
            "sanctions_hits": state.sanctions_hits,
            "case_metadata": state.metadata
        }
        
        result = await calculate_risk_score(combined_event)
        return {
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "confidence": result.confidence,
            "factors": result.factors
        }
    
    async def _make_decision(self, state: InvestigationState) -> Dict[str, Any]:
        """Make investigation decision based on risk score."""
        logger.info(f"Making decision for case {state.case_id}")
        
        if state.risk_score >= 0.8:
            state.status = InvestigationStatus.ESCALATED
            decision = "ESCALATE"
        elif state.risk_score >= 0.6:
            state.status = InvestigationStatus.IN_PROGRESS
            decision = "INVESTIGATE"
        else:
            state.status = InvestigationStatus.LOW_PRIORITY
            decision = "MONITOR"
        
        return {"decision": decision, "new_status": state.status.value}
    
    async def _start_investigation(self, state: InvestigationState) -> Dict[str, Any]:
        """Start detailed investigation."""
        logger.info(f"Starting detailed investigation for case {state.case_id}")
        
        state.status = InvestigationStatus.IN_PROGRESS
        state.investigator_id = "investigator_123"
        
        return {"investigation_started": True, "investigator_id": state.investigator_id}
    
    async def _escalate_case(self, state: InvestigationState) -> Dict[str, Any]:
        """Escalate case to higher level."""
        logger.warning(f"Escalating case {state.case_id}")
        
        state.status = InvestigationStatus.ESCALATED
        state.escalation_reason = "High risk score detected"
        state.escalated_to = "senior_investigator"
        
        return {"escalated": True, "escalated_to": state.escalated_to}
    
    async def _resolve_case(self, state: InvestigationState) -> Dict[str, Any]:
        """Resolve investigation case."""
        logger.info(f"Resolving case {state.case_id}")
        
        state.status = InvestigationStatus.RESOLVED
        state.resolution_notes = "Case resolved with automated workflow"
        state.closed_at = datetime.utcnow().isoformat()
        
        return {"resolved": True, "resolution_notes": state.resolution_notes}
    
    async def execute_workflow(self, initial_state: InvestigationState) -> InvestigationState:
        """Execute the complete fraud investigation workflow."""
        logger.info(f"Executing workflow for case {initial_state.case_id}")
        
        try:
            result = await self.graph.ainvoke(initial_state)
            final_state = InvestigationState(**result)
            final_state.status = InvestigationStatus.COMPLETED
            return final_state
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            initial_state.status = InvestigationStatus.FAILED
            initial_state.error_message = str(e)
            return initial_state


# Global workflow instance
fraud_workflow = LangGraphWorkflow()


def get_fraud_workflow() -> LangGraphWorkflow:
    """Get global fraud workflow instance."""
    return fraud_workflow


async def execute_fraud_workflow(initial_state: InvestigationState) -> InvestigationState:
    """Execute fraud investigation workflow."""
    workflow = get_fraud_workflow()
    return await workflow.execute_workflow(initial_state)