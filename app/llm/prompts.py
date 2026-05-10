"""System prompts for risk scoring and fraud analysis."""
from typing import Dict, Any, Optional


class FraudPrompts:
    """Comprehensive prompts for fraud investigation and risk assessment."""
    
    SYSTEM_PROMPT = """You are an expert fraud investigator and risk analyst with 15+ years of experience in financial crime detection and anti-money laundering compliance. Your analysis must be objective, precise, actionable, and compliant with regulatory best practices. Always respond in valid JSON format."""
    
    @classmethod
    def fraud_analysis(cls, transaction_data: Dict[str, Any], 
                    context: Optional[Dict[str, Any]] = None) -> str:
        """Generate fraud analysis prompt."""
        prompt = f"""
{cls.SYSTEM_PROMPT}

TASK: Transaction Fraud Analysis

Analyze the following transaction for potential fraud indicators:

Transaction Details:
- Amount: {transaction_data.get('amount', 'N/A')} {transaction_data.get('currency', 'USD')}
- Timestamp: {transaction_data.get('timestamp', 'N/A')}
- Sender: {transaction_data.get('sender', 'N/A')}
- Receiver: {transaction_data.get('receiver', 'N/A')}
- Location: {transaction_data.get('location', 'N/A')}
- Device/IP: {transaction_data.get('device', 'N/A')}
- Channel: {transaction_data.get('channel', 'N/A')}

{f"""Contextual Information:
- Customer Risk Profile: {context.get('customer_risk_profile', 'N/A')}
- Historical Transaction Patterns: {context.get('historical_patterns', 'N/A')}
- Previous Fraud Alerts: {context.get('previous_alerts', 'N/A')}
- Account Age: {context.get('account_age', 'N/A')}
- Typical Transaction Amount: {context.get('typical_amount', 'N/A')}
""" if context else ''}

RISK FACTORS TO EVALUATE:
1. Amount anomalies (unusual size, round numbers)
2. Timing patterns (unusual hours, high frequency)
3. Geographic inconsistencies
4. Counterparty relationships
5. Channel/device risks
6. Customer behavior deviations

RESPONSE FORMAT (JSON):
{{
    "overall_risk_score": <0-100>,
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "risk_factors": [
        {{
            "factor": "specific factor name",
            "score": <0-100>,
            "description": "detailed explanation"
        }}
    ],
    "fraud_indicators": [
        {{
            "indicator": "specific indicator",
            "severity": "LOW|MEDIUM|HIGH",
            "confidence": <0-100>,
            "description": "why this indicates fraud"
        }}
    ],
    "recommended_actions": [
        "specific immediate action 1",
        "specific immediate action 2"
    ],
    "monitoring_recommendations": [
        "ongoing monitoring recommendation 1",
        "ongoing monitoring recommendation 2"
    ],
    "confidence_score": <0-100>,
    "reasoning": "detailed analysis explaining risk assessment"
}}
"""
        return prompt.strip()
    
    @classmethod
    def risk_assessment(cls, entity_data: Dict[str, Any], 
                      historical_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate risk assessment prompt."""
        prompt = f"""
{cls.SYSTEM_PROMPT}

TASK: Entity Risk Assessment

Conduct a comprehensive risk assessment of the following entity:

Entity Information:
- Name: {entity_data.get('name', 'N/A')}
- Type: {entity_data.get('type', 'N/A')} (individual/corporate/etc)
- Registration Date: {entity_data.get('registration_date', 'N/A')}
- Jurisdiction: {entity_data.get('jurisdiction', 'N/A')}
- Business Type: {entity_data.get('business_type', 'N/A')}
- Industry: {entity_data.get('industry', 'N/A')}

{f"""Historical Data:
- Transaction Volume: {historical_data.get('transaction_volume', 'N/A')}
- Average Transaction Amount: {historical_data.get('avg_amount', 'N/A')}
- Payment Patterns: {historical_data.get('payment_patterns', 'N/A')}
- Geographic Distribution: {historical_data.get('geo_distribution', 'N/A')}
- Previous Incidents: {historical_data.get('incidents', 'N/A')}
- Compliance Issues: {historical_data.get('compliance_issues', 'N/A')}
""" if historical_data else ''}

RISK DIMENSIONS TO ASSESS:
1. Identity and verification risks
2. Business legitimacy and structure
3. Geographic and jurisdictional risks
4. Industry-specific risks
5. Transaction pattern risks
6. Regulatory and compliance risks

RESPONSE FORMAT (JSON):
{{
    "overall_risk_score": <0-100>,
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "risk_dimensions": {{
        "identity_verification": {{"score": <0-100>, "factors": ["factor1", "factor2"]}},
        "business_legitimacy": {{"score": <0-100>, "factors": ["factor1", "factor2"]}},
        "geographic_risk": {{"score": <0-100>, "factors": ["factor1", "factor2"]}},
        "industry_risk": {{"score": <0-100>, "factors": ["factor1", "factor2"]}},
        "transaction_patterns": {{"score": <0-100>, "factors": ["factor1", "factor2"]}},
        "regulatory_compliance": {{"score": <0-100>, "factors": ["factor1", "factor2"]}}
    }},
    "key_risk_factors": [
        {{
            "factor": "specific risk factor",
            "impact": "HIGH|MEDIUM|LOW",
            "likelihood": "HIGH|MEDIUM|LOW",
            "description": "detailed explanation"
        }}
    ],
    "red_flags": [
        {{
            "flag": "specific red flag",
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "explanation": "why this is concerning"
        }}
    ],
    "due_diligence_recommendations": [
        "specific verification step 1",
        "specific verification step 2"
    ],
    "monitoring_requirements": [
        {{
            "type": "transaction|behavioral|documentary",
            "frequency": "daily|weekly|monthly|event-driven",
            "description": "what to monitor"
        }}
    ],
    "risk_mitigation": [
        "specific mitigation action 1",
        "specific mitigation action 2"
    ],
    "confidence_score": <0-100>,
    "reasoning": "comprehensive risk assessment explanation"
}}
"""
        return prompt.strip()
    
    @classmethod
    def investigation_recommendation(cls, case_data: Dict[str, Any], 
                                evidence: list) -> str:
        """Generate investigation recommendation prompt."""
        evidence_text = "\n".join([
            f"- {e.get('type', 'Unknown')}: {e.get('description', 'No description')}"
            for e in evidence
        ])
        
        prompt = f"""
{cls.SYSTEM_PROMPT}

TASK: Investigation Recommendations

Generate investigation recommendations for the following case:

Case Information:
- Case ID: {case_data.get('case_id', 'N/A')}
- Case Type: {case_data.get('case_type', 'N/A')}
- Priority: {case_data.get('priority', 'N/A')}
- Status: {case_data.get('status', 'N/A')}

Evidence:
{evidence_text}

FOCUS AREAS:
1. Evidence collection and preservation
2. Regulatory and compliance requirements
3. Stakeholder communication needs
4. Resource allocation and timeline
5. Success metrics and deliverables

RESPONSE FORMAT (JSON):
{{
    "investigation_steps": [
        "detailed step 1",
        "detailed step 2"
    ],
    "priority_actions": [
        "priority action 1",
        "priority action 2"
    ],
    "required_resources": [
        "specific resource 1",
        "specific resource 2"
    ],
    "estimated_timeline": "detailed timeline with phases",
    "success_criteria": [
        "measurable criteria 1",
        "measurable criteria 2"
    ],
    "regulatory_considerations": [
        "applicable regulation 1",
        "compliance requirement 1"
    ],
    "confidence_score": <0-100>,
    "reasoning": "detailed investigation plan explanation"
}}
"""
        return prompt.strip()


# Convenience functions matching existing LLM client
def get_fraud_analysis_prompt(transaction_data: Dict[str, Any], 
                          context: Optional[Dict[str, Any]] = None) -> str:
    """Get fraud analysis prompt."""
    return FraudPrompts.fraud_analysis(transaction_data, context)


def get_risk_assessment_prompt(entity_data: Dict[str, Any], 
                           historical_data: Optional[Dict[str, Any]] = None) -> str:
    """Get risk assessment prompt."""
    return FraudPrompts.risk_assessment(entity_data, historical_data)


def get_investigation_prompt(case_data: Dict[str, Any], 
                         evidence: list) -> str:
    """Get investigation recommendation prompt."""
    return FraudPrompts.investigation_recommendation(case_data, evidence)
