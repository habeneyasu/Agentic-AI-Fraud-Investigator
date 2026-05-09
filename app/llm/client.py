from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.generativeai import GenerativeModel, configure as genai_configure
from cerebras.cloud.sdk import Cerebras
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks.base import BaseCallbackHandler

from app.core.config import LLMConfig
from app.core.langsmith import track_langsmith, get_langsmith_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    CEREBRAS = "cerebras"
    GEMINI = "gemini"


class LangSmithCallbackHandler(BaseCallbackHandler):
    """LangSmith callback handler for LangChain integration."""
    
    def __init__(self):
        self.langsmith_manager = get_langsmith_manager()
        self.run_id = None
        
    def on_chain_start(self, serialized, inputs, **kwargs):
        self.run_id = self.langsmith_manager.create_run(
            name=serialized.get("name", "unknown_chain"),
            inputs=inputs,
            run_type="chain"
        )
        
    def on_chain_end(self, outputs, **kwargs):
        if self.run_id:
            self.langsmith_manager.end_run(self.run_id, outputs=outputs)
            
    def on_chain_error(self, error, **kwargs):
        if self.run_id:
            self.langsmith_manager.end_run(self.run_id, error=str(error))


class LLMClient:
    """Unified LLM client with async support, timeouts, and retries."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.CEREBRAS):
        self.provider = provider
        self.langsmith_manager = get_langsmith_manager()
        self.callback_handler = LangSmithCallbackHandler()
        self._init_client()
    
    def _init_client(self):
        """Initialize the appropriate client based on provider."""
        if self.provider == LLMProvider.OPENAI:
            if not LLMConfig.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            self.client = ChatOpenAI(
                model=LLMConfig.openai_model,
                temperature=LLMConfig.temperature,
                max_tokens=LLMConfig.max_tokens,
                callbacks=[self.callback_handler] if self.langsmith_manager.enabled else None
            )
        elif self.provider == LLMProvider.CEREBRAS:
            if not LLMConfig.cerebras_api_key:
                raise ValueError("Cerebras API key not configured")
            self.client = Cerebras(api_key=LLMConfig.cerebras_api_key)
        elif self.provider == LLMProvider.GEMINI:
            if not LLMConfig.gemini_api_key:
                raise ValueError("Gemini API key not configured")
            genai_configure(api_key=LLMConfig.gemini_api_key)
    
    def _log_result(self, provider: str, task_type: str, duration: float, model: str):
        """Log performance metrics."""
        logger.info(
            "LLM call completed",
            provider=provider,
            task_type=task_type,
            duration_ms=duration * 1000
        )
    
    def _build_result(self, provider: str, model: str, response: str, 
                     duration: float, task_type: str) -> Dict[str, Any]:
        """Build standardized result dictionary."""
        return {
            "provider": provider,
            "model": model,
            "response": response,
            "duration_ms": duration * 1000,
            "task_type": task_type
        }
    
    @track_langsmith(name="fraud_analysis", run_type="chain", 
                    tags=["fraud", "investigation"], metadata={"task": "fraud_analysis"})
    async def analyze_transaction(self, transaction_data: Dict[str, Any], 
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze transaction for fraud indicators."""
        prompt = self._build_fraud_analysis_prompt(transaction_data, context)
        return await self._call_llm(prompt, "fraud_analysis")
    
    @track_langsmith(name="risk_assessment", run_type="chain", 
                    tags=["risk", "assessment"], metadata={"task": "risk_assessment"})
    async def assess_risk(self, entity_data: Dict[str, Any], 
                         historical_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Assess risk level for an entity."""
        prompt = self._build_risk_assessment_prompt(entity_data, historical_data)
        return await self._call_llm(prompt, "risk_assessment")
    
    @track_langsmith(name="investigation_recommendation", run_type="chain", 
                    tags=["investigation", "recommendation"], 
                    metadata={"task": "investigation_recommendation"})
    async def generate_investigation_recommendation(self, case_data: Dict[str, Any], 
                                                 evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate investigation recommendations."""
        prompt = self._build_investigation_prompt(case_data, evidence)
        return await self._call_llm(prompt, "investigation_recommendation")
    
    async def _call_llm(self, prompt: str, task_type: str) -> Dict[str, Any]:
        """Unified LLM call method."""
        if self.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt, task_type)
        elif self.provider == LLMProvider.CEREBRAS:
            return await self._call_cerebras_async(prompt, task_type)
        elif self.provider == LLMProvider.GEMINI:
            return await self._call_gemini_async(prompt, task_type)
    
    def _call_openai(self, prompt: str, task_type: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        try:
            start_time = time.time()
            messages = [
                SystemMessage(content="You are a fraud investigation expert."),
                HumanMessage(content=prompt)
            ]
            response = self.client.invoke(messages)
            duration = time.time() - start_time
            
            result = self._build_result("openai", LLMConfig.openai_model, 
                                      response.content, duration, task_type)
            self._log_result("openai", task_type, duration, LLMConfig.openai_model)
            return result
            
        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e), task_type=task_type)
            raise
    
    @retry(stop=stop_after_attempt(3), 
           wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)))
    async def _call_cerebras_async(self, prompt: str, task_type: str, 
                                 timeout: float = 30.0) -> Dict[str, Any]:
        """Call Cerebras API asynchronously with timeout and retry."""
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLMConfig.cerebras_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": LLMConfig.cerebras_model,
                    "messages": [
                        {"role": "system", "content": "You are a fraud investigation expert."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": LLMConfig.temperature,
                    "max_tokens": LLMConfig.max_tokens
                }
            )
            response.raise_for_status()
            result_data = response.json()
            
        duration = time.time() - start_time
        response_text = result_data["choices"][0]["message"]["content"]
        
        result = self._build_result("cerebras", LLMConfig.cerebras_model, 
                                  response_text, duration, task_type)
        self._log_result("cerebras", task_type, duration, LLMConfig.cerebras_model)
        return result
    
    @retry(stop=stop_after_attempt(3), 
           wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)))
    async def _call_gemini_async(self, prompt: str, task_type: str, 
                               timeout: float = 30.0) -> Dict[str, Any]:
        """Call Gemini API asynchronously with timeout and retry."""
        start_time = time.time()
        
        model = GenerativeModel(
            model_name=LLMConfig.gemini_model,
            generation_config={
                "temperature": LLMConfig.temperature,
                "max_output_tokens": LLMConfig.max_tokens,
            }
        )
        
        full_prompt = f"You are a fraud investigation expert.\n\n{prompt}"
        response = await model.generate_content_async(full_prompt)
        
        duration = time.time() - start_time
        
        result = self._build_result("gemini", LLMConfig.gemini_model, 
                                  response.text, duration, task_type)
        self._log_result("gemini", task_type, duration, LLMConfig.gemini_model)
        return result
    
    def _build_fraud_analysis_prompt(self, transaction_data: Dict[str, Any], 
                                   context: Optional[Dict[str, Any]] = None) -> str:
        """Build prompt for fraud analysis."""
        base_prompt = f"""
        Analyze the following transaction for potential fraud indicators:
        
        Transaction Details:
        - Amount: {transaction_data.get("amount", "N/A")}
        - Currency: {transaction_data.get("currency", "N/A")}
        - Timestamp: {transaction_data.get("timestamp", "N/A")}
        - Sender: {transaction_data.get("sender", "N/A")}
        - Receiver: {transaction_data.get("receiver", "N/A")}
        - Location: {transaction_data.get("location", "N/A")}
        - Device: {transaction_data.get("device", "N/A")}
        """
        
        if context:
            base_prompt += f"""
            Context:
            - Customer History: {context.get("customer_history", "N/A")}
            - Risk Score: {context.get("risk_score", "N/A")}
            - Previous Alerts: {context.get("previous_alerts", "N/A")}
            """
        
        base_prompt += """
        
        Please provide:
        1. Risk level (LOW/MEDIUM/HIGH)
        2. Specific fraud indicators detected
        3. Recommended actions
        4. Confidence score (0-100)
        
        Format your response as JSON.
        """
        
        return base_prompt
    
    def _build_risk_assessment_prompt(self, entity_data: Dict[str, Any], 
                                    historical_data: Optional[Dict[str, Any]] = None) -> str:
        """Build prompt for risk assessment."""
        base_prompt = f"""
        Assess the risk level for the following entity:
        
        Entity Information:
        - Name: {entity_data.get("name", "N/A")}
        - Type: {entity_data.get("type", "N/A")}
        - Registration Date: {entity_data.get("registration_date", "N/A")}
        - Location: {entity_data.get("location", "N/A")}
        - Business Type: {entity_data.get("business_type", "N/A")}
        """
        
        if historical_data:
            base_prompt += f"""
            Historical Data:
            - Transaction Volume: {historical_data.get("transaction_volume", "N/A")}
            - Average Transaction Amount: {historical_data.get("avg_amount", "N/A")}
            - Previous Incidents: {historical_data.get("incidents", "N/A")}
            - Risk History: {historical_data.get("risk_history", "N/A")}
            """
        
        base_prompt += """
        
        Please provide:
        1. Overall risk score (0-100)
        2. Risk factors identified
        3. Recommended monitoring frequency
        4. Suggested mitigation measures
        
        Format your response as JSON.
        """
        
        return base_prompt
    
    def _build_investigation_prompt(self, case_data: Dict[str, Any], 
                                  evidence: List[Dict[str, Any]]) -> str:
        """Build prompt for investigation recommendations."""
        evidence_text = "\n".join([
            f"- {e.get('type', 'Unknown')}: {e.get('description', 'No description')}"
            for e in evidence
        ])
        
        return f"""
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


def create_llm_client(provider: LLMProvider = LLMProvider.CEREBRAS) -> LLMClient:
    """Create an LLM client with the specified provider."""
    return LLMClient(provider)


# Default client instance
default_llm_client = create_llm_client()
