from typing import Optional, Dict, Any, List
from enum import Enum
import openai
import google.generativeai as genai
from anthropic import Anthropic
from cerebras.cloud.sdk import Cerebras
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.base import BaseCallbackHandler
import time

from app.core.config import LLMConfig
from app.core.langsmith import track_langsmith, get_langsmith_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CEREBRAS = "cerebras"
    GEMINI = "gemini"


class LangSmithCallbackHandler(BaseCallbackHandler):
    """LangSmith callback handler for LangChain integration."""
    
    def __init__(self):
        self.langsmith_manager = get_langsmith_manager()
        self.run_id = None
        
    def on_chain_start(self, serialized, inputs, **kwargs):
        """Handle chain start."""
        self.run_id = self.langsmith_manager.create_run(
            name=serialized.get("name", "unknown_chain"),
            inputs=inputs,
            run_type="chain"
        )
        
    def on_chain_end(self, outputs, **kwargs):
        """Handle chain end."""
        if self.run_id:
            self.langsmith_manager.end_run(self.run_id, outputs=outputs)
            
    def on_chain_error(self, error, **kwargs):
        """Handle chain error."""
        if self.run_id:
            self.langsmith_manager.end_run(self.run_id, error=str(error))


class LLMClient:
    """Unified LLM client supporting multiple providers with LangSmith observability."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        self.provider = provider
        self.langsmith_manager = get_langsmith_manager()
        self.callback_handler = LangSmithCallbackHandler()
        
        if provider == LLMProvider.OPENAI:
            self._init_openai()
        elif provider == LLMProvider.ANTHROPIC:
            self._init_anthropic()
        elif provider == LLMProvider.CEREBRAS:
            self._init_cerebras()
        elif provider == LLMProvider.GEMINI:
            self._init_gemini()
    
    def _init_openai(self) -> None:
        """Initialize OpenAI client."""
        if not LLMConfig.openai_api_key:
            raise ValueError("OpenAI API key not configured")
            
        openai.api_key = LLMConfig.openai_api_key
        self.client = ChatOpenAI(
            model=LLMConfig.openai_model,
            temperature=LLMConfig.temperature,
            max_tokens=LLMConfig.max_tokens,
            callbacks=[self.callback_handler] if self.langsmith_manager.enabled else None
        )
    
    def _init_anthropic(self) -> None:
        """Initialize Anthropic client."""
        if not LLMConfig.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
            
        self.client = Anthropic(api_key=LLMConfig.anthropic_api_key)
    
    def _init_cerebras(self) -> None:
        """Initialize Cerebras client."""
        if not LLMConfig.cerebras_api_key:
            raise ValueError("Cerebras API key not configured")
            
        self.client = Cerebras(api_key=LLMConfig.cerebras_api_key)
    
    def _init_gemini(self) -> None:
        """Initialize Gemini client."""
        if not LLMConfig.gemini_api_key:
            raise ValueError("Gemini API key not configured")
            
        genai.configure(api_key=LLMConfig.gemini_api_key)
        self.client = ChatGoogleGenerativeAI(
            model=LLMConfig.gemini_model,
            temperature=LLMConfig.temperature,
            max_tokens=LLMConfig.max_tokens,
            callbacks=[self.callback_handler] if self.langsmith_manager.enabled else None
        )
    
    @track_langsmith(
        name="fraud_analysis",
        run_type="chain",
        tags=["fraud", "investigation"],
        metadata={"task": "fraud_analysis"}
    )
    def analyze_transaction(
        self,
        transaction_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze transaction for fraud indicators."""
        
        prompt = self._build_fraud_analysis_prompt(transaction_data, context)
        
        if self.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt, "fraud_analysis")
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(prompt, "fraud_analysis")
        elif self.provider == LLMProvider.CEREBRAS:
            return self._call_cerebras(prompt, "fraud_analysis")
        elif self.provider == LLMProvider.GEMINI:
            return self._call_gemini(prompt, "fraud_analysis")
    
    @track_langsmith(
        name="risk_assessment",
        run_type="chain",
        tags=["risk", "assessment"],
        metadata={"task": "risk_assessment"}
    )
    def assess_risk(
        self,
        entity_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Assess risk level for an entity."""
        
        prompt = self._build_risk_assessment_prompt(entity_data, historical_data)
        
        if self.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt, "risk_assessment")
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(prompt, "risk_assessment")
        elif self.provider == LLMProvider.CEREBRAS:
            return self._call_cerebras(prompt, "risk_assessment")
        elif self.provider == LLMProvider.GEMINI:
            return self._call_gemini(prompt, "risk_assessment")
    
    @track_langsmith(
        name="investigation_recommendation",
        run_type="chain",
        tags=["investigation", "recommendation"],
        metadata={"task": "investigation_recommendation"}
    )
    def generate_investigation_recommendation(
        self,
        case_data: Dict[str, Any],
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate investigation recommendations."""
        
        prompt = self._build_investigation_prompt(case_data, evidence)
        
        if self.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt, "investigation_recommendation")
        elif self.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(prompt, "investigation_recommendation")
        elif self.provider == LLMProvider.CEREBRAS:
            return self._call_cerebras(prompt, "investigation_recommendation")
        elif self.provider == LLMProvider.GEMINI:
            return self._call_gemini(prompt, "investigation_recommendation")
    
    def _call_openai(self, prompt: str, task_type: str) -> Dict[str, Any]:
        """Call OpenAI API with LangSmith tracking."""
        try:
            start_time = time.time()
            
            messages = [
                SystemMessage(content="You are a fraud investigation expert."),
                HumanMessage(content=prompt)
            ]
            
            response = self.client.invoke(messages)
            duration = time.time() - start_time
            
            result = {
                "provider": "openai",
                "model": LLMConfig.openai_model,
                "response": response.content,
                "duration_ms": duration * 1000,
                "task_type": task_type
            }
            
            # Log performance metrics
            logger.info(
                "LLM call completed",
                provider="openai",
                task_type=task_type,
                duration_ms=duration * 1000
            )
            
            return result
            
        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e), task_type=task_type)
            raise
    
    def _call_anthropic(self, prompt: str, task_type: str) -> Dict[str, Any]:
        """Call Anthropic API with LangSmith tracking."""
        try:
            start_time = time.time()
            
            response = self.client.messages.create(
                model=LLMConfig.anthropic_model,
                max_tokens=LLMConfig.max_tokens,
                temperature=LLMConfig.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            duration = time.time() - start_time
            
            result = {
                "provider": "anthropic",
                "model": LLMConfig.anthropic_model,
                "response": response.content[0].text,
                "duration_ms": duration * 1000,
                "task_type": task_type
            }
            
            # Log performance metrics
            logger.info(
                "LLM call completed",
                provider="anthropic",
                task_type=task_type,
                duration_ms=duration * 1000
            )
            
            return result
            
        except Exception as e:
            logger.error("Anthropic API call failed", error=str(e), task_type=task_type)
            raise
    
    def _call_cerebras(self, prompt: str, task_type: str) -> Dict[str, Any]:
        """Call Cerebras API with LangSmith tracking."""
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=LLMConfig.cerebras_model,
                messages=[
                    {"role": "system", "content": "You are a fraud investigation expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLMConfig.temperature,
                max_tokens=LLMConfig.max_tokens
            )
            
            duration = time.time() - start_time
            
            result = {
                "provider": "cerebras",
                "model": LLMConfig.cerebras_model,
                "response": response.choices[0].message.content,
                "duration_ms": duration * 1000,
                "task_type": task_type
            }
            
            # Log performance metrics
            logger.info(
                "LLM call completed",
                provider="cerebras",
                task_type=task_type,
                duration_ms=duration * 1000
            )
            
            return result
            
        except Exception as e:
            logger.error("Cerebras API call failed", error=str(e), task_type=task_type)
            raise
    
    def _call_gemini(self, prompt: str, task_type: str) -> Dict[str, Any]:
        """Call Gemini API with LangSmith tracking."""
        try:
            start_time = time.time()
            
            messages = [
                SystemMessage(content="You are a fraud investigation expert."),
                HumanMessage(content=prompt)
            ]
            
            response = self.client.invoke(messages)
            duration = time.time() - start_time
            
            result = {
                "provider": "gemini",
                "model": LLMConfig.gemini_model,
                "response": response.content,
                "duration_ms": duration * 1000,
                "task_type": task_type
            }
            
            # Log performance metrics
            logger.info(
                "LLM call completed",
                provider="gemini",
                task_type=task_type,
                duration_ms=duration * 1000
            )
            
            return result
            
        except Exception as e:
            logger.error("Gemini API call failed", error=str(e), task_type=task_type)
            raise
    
    def _build_fraud_analysis_prompt(
        self,
        transaction_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for fraud analysis."""
        
        base_prompt = """
        Analyze the following transaction for potential fraud indicators:
        
        Transaction Details:
        - Amount: {amount}
        - Currency: {currency}
        - Timestamp: {timestamp}
        - Sender: {sender}
        - Receiver: {receiver}
        - Location: {location}
        - Device: {device}
        """
        
        if context:
            base_prompt += f"""
            
            Context:
            - Customer History: {customer_history}
            - Risk Score: {risk_score}
            - Previous Alerts: {previous_alerts}
            """
        
        base_prompt += """
        
        Please provide:
        1. Risk level (LOW/MEDIUM/HIGH)
        2. Specific fraud indicators detected
        3. Recommended actions
        4. Confidence score (0-100)
        
        Format your response as JSON.
        """
        
        return base_prompt.format(
            amount=transaction_data.get("amount", "N/A"),
            currency=transaction_data.get("currency", "N/A"),
            timestamp=transaction_data.get("timestamp", "N/A"),
            sender=transaction_data.get("sender", "N/A"),
            receiver=transaction_data.get("receiver", "N/A"),
            location=transaction_data.get("location", "N/A"),
            device=transaction_data.get("device", "N/A"),
            customer_history=context.get("customer_history", "N/A") if context else "N/A",
            risk_score=context.get("risk_score", "N/A") if context else "N/A",
            previous_alerts=context.get("previous_alerts", "N/A") if context else "N/A"
        )
    
    def _build_risk_assessment_prompt(
        self,
        entity_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for risk assessment."""
        
        base_prompt = """
        Assess the risk level for the following entity:
        
        Entity Information:
        - Name: {name}
        - Type: {entity_type}
        - Registration Date: {registration_date}
        - Location: {location}
        - Business Type: {business_type}
        """
        
        if historical_data:
            base_prompt += f"""
            
            Historical Data:
            - Transaction Volume: {transaction_volume}
            - Average Transaction Amount: {avg_amount}
            - Previous Incidents: {incidents}
            - Risk History: {risk_history}
            """
        
        base_prompt += """
        
        Please provide:
        1. Overall risk score (0-100)
        2. Risk factors identified
        3. Recommended monitoring frequency
        4. Suggested mitigation measures
        
        Format your response as JSON.
        """
        
        return base_prompt.format(
            name=entity_data.get("name", "N/A"),
            entity_type=entity_data.get("type", "N/A"),
            registration_date=entity_data.get("registration_date", "N/A"),
            location=entity_data.get("location", "N/A"),
            business_type=entity_data.get("business_type", "N/A"),
            transaction_volume=historical_data.get("transaction_volume", "N/A") if historical_data else "N/A",
            avg_amount=historical_data.get("avg_amount", "N/A") if historical_data else "N/A",
            incidents=historical_data.get("incidents", "N/A") if historical_data else "N/A",
            risk_history=historical_data.get("risk_history", "N/A") if historical_data else "N/A"
        )
    
    def _build_investigation_prompt(
        self,
        case_data: Dict[str, Any],
        evidence: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for investigation recommendations."""
        
        evidence_text = "\n".join([
            f"- {e.get('type', 'Unknown')}: {e.get('description', 'No description')}"
            for e in evidence
        ])
        
        prompt = f"""
        Generate investigation recommendations for the following case:
        
        Case Information:
        - Case ID: {case_data.get('case_id', 'N/A')}
        - Case Type: {case_data.get('case_type', 'N/A')}
        - Priority: {case_data.get('priority', 'N/A')}
        - Status: {case_data.get('status', 'N/A')}
        
        Evidence:
        {evidence_text}
        
        Please provide:
        1. Recommended investigation steps
        2. Priority actions
        3. Required resources
        4. Estimated timeline
        5. Success criteria
        
        Format your response as JSON.
        """
        
        return prompt


# Factory function for creating LLM clients
def create_llm_client(provider: LLMProvider = LLMProvider.OPENAI) -> LLMClient:
    """Create an LLM client with the specified provider."""
    return LLMClient(provider)


# Default client instance
default_llm_client = create_llm_client()