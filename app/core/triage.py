from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime, timedelta
import json
import asyncio
import instructor

from pydantic import ValidationError

from app.core.config import settings, LLMConfig
from app.llm.client import create_llm_client, LLMProvider
from app.core.logging import get_logger
from app.core.langsmith import track_langsmith
from app.core.schemas import (
    TriageAnalysis, TriageResult, TriagePriority, TriageCategory,
    CaseInput, HistoricalContext
)

logger = get_logger(__name__)


# Constants for production optimization
MAX_DESCRIPTION_LENGTH = 2000  # Max characters for description to control tokens
DEFAULT_TIMEOUT_SECONDS = 30  # Timeout for LLM calls


class FraudTriage:
    """Intelligent fraud case triage system with LLM-powered analysis."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        self.llm_client = create_llm_client(provider)
        self.priority_weights = {
            TriagePriority.CRITICAL: 1.0,
            TriagePriority.HIGH: 0.8,
            TriagePriority.MEDIUM: 0.6,
            TriagePriority.LOW: 0.4,
            TriagePriority.INFO: 0.2
        }
    
    @track_langsmith(
        name="fraud_triage",
        run_type="chain",
        tags=["triage", "fraud", "prioritization"],
        metadata={"task": "fraud_triage"}
    )
    async def triage_case(
        self,
        case_data: CaseInput,
        historical_context: HistoricalContext
    ) -> TriageResult:
        """
        Perform intelligent triage of fraud case.
        
        Args:
            case_data: Validated CaseInput object
            historical_context: Validated HistoricalContext object
            
        Returns:
            Dictionary with triage results including priority, category, and recommendations
        """
        
        try:
            
            # Analyze case with LLM (async)
            triage_analysis = await self._analyze_case_with_llm(case_data, historical_context)
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(triage_analysis)
            
            # Determine final priority
            final_priority = self._determine_priority(priority_score, triage_analysis)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(final_priority, triage_analysis.category)
            
            # Create structured triage result
            triage_result = TriageResult(
                case_id=case_data.case_id,
                triage_timestamp=datetime.utcnow().isoformat(),
                priority=final_priority,
                priority_score=priority_score,
                category=triage_analysis.category,
                risk_factors=triage_analysis.risk_factors,
                urgency_indicators=triage_analysis.urgency_indicators,
                estimated_investigation_time=triage_analysis.estimated_time_hours,
                required_resources=triage_analysis.required_resources,
                recommendations=recommendations,
                auto_escalation=self._should_auto_escalate(final_priority, triage_analysis),
                llm_analysis=triage_analysis.raw_analysis,
                triage_confidence=triage_analysis.confidence
            )
            
            logger.info(
                "Case triaged successfully",
                case_id=case_data.case_id,
                priority=final_priority.value,
                category=triage_analysis.category.value,
                confidence=triage_analysis.confidence
            )
            
            return triage_result
            
        except ValidationError as e:
            logger.error("Input validation failed", error=str(e), case_id=case_data.case_id)
            return self._get_default_triage(case_data.case_id)
        except Exception as e:
            logger.error("Failed to triage case", error=str(e), case_id=case_data.case_id)
            # Return default triage on error
            return self._get_default_triage(case_data.case_id)
    
    async def _analyze_case_with_llm(
        self,
        case_data: CaseInput,
        historical_context: HistoricalContext
    ) -> TriageAnalysis:
        """Analyze case using LLM for intelligent triage with structured output."""
        
        prompt = self._build_triage_prompt(case_data, historical_context)
        
        try:
            # Use instructor for structured output
            response = await asyncio.wait_for(
                self._call_llm_with_instructor(prompt),
                timeout=DEFAULT_TIMEOUT_SECONDS
            )
            
            # Return structured Pydantic model
            return response
            
        except asyncio.TimeoutError:
            logger.error("LLM analysis timed out", case_id=case_data.case_id)
            return self._get_fallback_analysis(case_data)
        except Exception as e:
            logger.error("LLM analysis failed", error=str(e), case_id=case_data.case_id)
            return self._get_fallback_analysis(case_data)
    
    def _build_triage_prompt(
        self,
        case_data: CaseInput,
        historical_context: HistoricalContext
    ) -> str:
        """Build comprehensive triage prompt for LLM with token management."""
        
        # Truncate description to control token usage
        description = case_data.description[:MAX_DESCRIPTION_LENGTH]
        if len(case_data.description) > MAX_DESCRIPTION_LENGTH:
            description += "..."  # Add ellipsis for truncation
        
        base_prompt = f"""
        You are an expert fraud investigation triage specialist. Analyze the following fraud case and provide detailed triage assessment.
        
        CASE INFORMATION:
        - Case ID: {case_data.case_id}
        - Reported Date: {case_data.reported_date}
        - Case Type: {case_data.case_type}
        - Amount Involved: {case_data.amount or 'N/A'}
        - Currency: {case_data.currency or 'N/A'}
        - Description: {description}
        - Reporter: {case_data.reporter}
        - Affected Parties: {case_data.affected_parties}
        - Evidence Count: {len(case_data.evidence)}
        """
        
        if historical_context:
            base_prompt += f"""
            
            HISTORICAL CONTEXT:
            - Similar Cases: {historical_context.similar_cases}
            - Historical Risk Score: {historical_context.historical_risk or 'N/A'}
            - Previous Escalations: {historical_context.previous_escalations}
            - Average Resolution Time: {historical_context.avg_resolution_time or 'N/A'}
            - Customer History: {historical_context.customer_history or 'N/A'}
            - Previous Alerts: {historical_context.previous_alerts or 'N/A'}
            """
        
        base_prompt += """
        
        Analyze the case and provide structured output for triage.
        
        Consider:
        1. Financial impact and potential loss
        2. Number of affected customers/accounts  
        3. Regulatory and compliance implications
        4. Time sensitivity and escalation needs
        5. Resource requirements for investigation
        """
        
        return base_prompt
    
    async def _call_llm_with_instructor(self, prompt: str) -> TriageAnalysis:
        """Call LLM using instructor for structured output."""
        # Configure instructor with the LLM client
        if hasattr(self.llm_client.client, 'model'):
            # For LangChain clients
            client = instructor.from_openai(
                self.llm_client.client.client if hasattr(self.llm_client.client, 'client') else self.llm_client.client
            )
        else:
            # For direct API clients
            client = instructor.from_openai(self.llm_client.client)
        
        # Use appropriate model for fraud detection based on provider
        if hasattr(self.llm_client.client, 'model'):
            model = self.llm_client.client.model
        else:
            # Default to GPT-4o for better reasoning on complex fraud cases
            model = "gpt-4o"
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a fraud investigation triage specialist with expertise in identifying complex fraud patterns and gray area cases."},
                {"role": "user", "content": prompt}
            ],
            response_model=TriageAnalysis,
            temperature=LLMConfig.temperature,
            max_tokens=LLMConfig.max_tokens
        )
        
        return response
    
    def _calculate_priority_score(self, analysis: TriageAnalysis) -> float:
        """Calculate priority score based on structured analysis."""
        score = 0.0
        
        # Base score from category
        if analysis.category == TriageCategory.TRANSACTION_FRAUD:
            score += 0.3
        elif analysis.category == TriageCategory.ACCOUNT_TAKEOVER:
            score += 0.4
        elif analysis.category == TriageCategory.IDENTITY_THEFT:
            score += 0.4
        elif analysis.category == TriageCategory.MONEY_LAUNDERING:
            score += 0.5
        elif analysis.category == TriageCategory.SANCTIONS_VIOLATION:
            score += 0.5
        elif analysis.category == TriageCategory.KYC_ISSUES:
            score += 0.2
        
        # Risk factors contribution
        score += len(analysis.risk_factors) * 0.1
        
        # Urgency indicators contribution
        score += len(analysis.urgency_indicators) * 0.15
        
        # Estimated time contribution
        if analysis.estimated_time_hours > 48:
            score += 0.2
        elif analysis.estimated_time_hours > 24:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _determine_priority(
        self,
        score: float,
        analysis: TriageAnalysis
    ) -> TriagePriority:
        """Determine priority based on score and analysis."""
        
        if score >= 0.8:
            return TriagePriority.CRITICAL
        elif score >= 0.6:
            return TriagePriority.HIGH
        elif score >= 0.4:
            return TriagePriority.MEDIUM
        elif score >= 0.2:
            return TriagePriority.LOW
        else:
            return TriagePriority.INFO
    
    def _generate_recommendations(
        self,
        priority: TriagePriority,
        category: TriageCategory
    ) -> List[str]:
        """Generate recommendations based on priority and category."""
        recommendations = []
        
        # Priority-based recommendations
        if priority == TriagePriority.CRITICAL:
            recommendations.extend([
                "Immediate escalation to senior investigator",
                "Notify compliance and legal teams",
                "Consider temporary account restrictions",
                "Document all evidence preservation steps"
            ])
        elif priority == TriagePriority.HIGH:
            recommendations.extend([
                "Assign to experienced investigator",
                "Schedule review within 4 hours",
                "Prepare escalation criteria"
            ])
        elif priority == TriagePriority.MEDIUM:
            recommendations.extend([
                "Assign to available investigator",
                "Schedule review within 24 hours",
                "Monitor for related cases"
            ])
        else:
            recommendations.extend([
                "Add to investigation queue",
                "Review during next triage cycle",
                "Monitor for pattern emergence"
            ])
        
        # Category-specific recommendations
        if category == TriageCategory.TRANSACTION_FRAUD:
            recommendations.append("Review transaction patterns and related accounts")
        elif category == TriageCategory.ACCOUNT_TAKEOVER:
            recommendations.append("Immediate account security measures required")
        elif category == TriageCategory.IDENTITY_THEFT:
            recommendations.append("Coordinate with identity verification team")
        elif category == TriageCategory.MONEY_LAUNDERING:
            recommendations.append("Engage financial crime specialists")
        elif category == TriageCategory.SANCTIONS_VIOLATION:
            recommendations.append("Immediate regulatory notification required")
        elif category == TriageCategory.KYC_ISSUES:
            recommendations.append("Enhanced due diligence investigation needed")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _should_auto_escalate(
        self,
        priority: TriagePriority,
        analysis: TriageAnalysis
    ) -> bool:
        """Determine if case should be auto-escalated."""
        
        # Auto-escalate critical cases
        if priority == TriagePriority.CRITICAL:
            return True
        
        # Auto-escalate based on risk factors
        if "regulatory_implications" in analysis.risk_factors:
            return True
        
        # Auto-escalate based on confidence
        if analysis.confidence < 0.3 and priority in [TriagePriority.HIGH, TriagePriority.MEDIUM]:
            return True
        
        return False
    
    def _get_fallback_analysis(self, case_data: CaseInput) -> TriageAnalysis:
        """Get fallback analysis when LLM fails."""
        return TriageAnalysis(
            category=TriageCategory.SUSPICIOUS_ACTIVITY,
            risk_factors=["llm_analysis_failed"],
            urgency_indicators=["manual_review_required"],
            estimated_time_hours=24,
            required_resources=["investigator"],
            confidence=0.3,
            raw_analysis="LLM analysis failed, using fallback triage"
        )
    
    def _get_default_triage(self, case_id: str) -> TriageResult:
        """Get default triage result for errors."""
        return TriageResult(
            case_id=case_id,
            triage_timestamp=datetime.utcnow().isoformat(),
            priority=TriagePriority.MEDIUM,
            priority_score=0.5,
            category=TriageCategory.SUSPICIOUS_ACTIVITY,
            risk_factors=["system_error"],
            urgency_indicators=["manual_review_required"],
            estimated_investigation_time=24,
            required_resources=["investigator"],
            recommendations=["Manual triage required due to system error"],
            auto_escalation=False,
            llm_analysis="System error during triage",
            triage_confidence=0.1
        )


# Global triage instance
fraud_triage = FraudTriage()


def get_fraud_triage() -> FraudTriage:
    """Get global fraud triage instance."""
    return fraud_triage