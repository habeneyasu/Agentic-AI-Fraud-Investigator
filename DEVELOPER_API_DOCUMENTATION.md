# Agentic AI Fraud Investigator - Developer API Documentation

## Overview

The Agentic AI Fraud Investigator provides a comprehensive REST API for fraud detection and investigation workflows. This document covers all available endpoints, request/response formats, and integration patterns.

## Base URL

```
Production: https://api.fraud-investigator.example.com
Development: http://localhost:8000
```

## Authentication

**Local development (default):** no API key is required. Leave `API_KEY` unset (or empty) in the environment; route guards in `app/api/deps.py` then skip the check.

**Deployed / locked-down environments:** set the `API_KEY` environment variable to a strong secret. Clients must send the same value in the header:

```http
X-API-Key: <your API_KEY value>
```

## API Endpoints

### 🚨 Alert Management

#### Create Fraud Alert
```http
POST /alerts
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction_id": "TX123456789",
  "amount": 15000.00,
  "currency": "USD",
  "account_id": "ACC987654321",
  "recipient_country": "IR",
  "alert_hash": "abc123def456",
  "timestamp": "2026-05-12T14:30:00Z",
  "metadata": {
    "severity": "high",
    "source": "transaction_monitoring",
    "device_id": "DEV001"
  }
}
```

**Response (202):**
```json
{
  "investigation_id": "inv_abc123def456",
  "alert_id": "ALERT_TX123456789_1",
  "status": "OPEN",
  "message": "Alert received and queued for investigation"
}
```

#### Get Alert Details
```http
GET /alerts/{alert_id}
```

**Response (200):**
```json
{
  "alert_id": "ALERT_TX123456789_1",
  "investigation_id": "inv_abc123def456",
  "transaction_id": "TX123456789",
  "amount": 15000.00,
  "currency": "USD",
  "account_id": "ACC987654321",
  "recipient_country": "IR",
  "status": "UNDER_INVESTIGATION",
  "created_at": "2026-05-12T14:30:00Z",
  "updated_at": "2026-05-12T14:35:00Z",
  "risk_score": 0.85,
  "metadata": {
    "severity": "high",
    "source": "transaction_monitoring"
  }
}
```

### 🔍 Investigation Management

#### Start Investigation
```http
POST /investigation/start
Content-Type: application/json
```

**Request Body:**
```json
{
  "investigation": {
    "transaction_id": "TX123456789",
    "customer_id": "CUST001",
    "amount": 15000.00,
    "currency": "USD",
    "destination_country": "IR",
    "device_id": "DEV001",
    "ip_address": "192.168.1.100",
    "risk_indicators": ["high_amount", "off_hours", "high_risk_country"],
    "metadata": {
      "source": "transaction_monitoring",
      "alert_type": "suspicious_transaction"
    }
  }
}
```

**Response (200):**
```json
{
  "investigation_id": "inv_abc123def456",
  "status": "STARTED",
  "agents_triggered": ["transaction", "kyc_device", "sanctions"],
  "estimated_completion": "2026-05-12T14:40:00Z"
}
```

#### Get Investigation Status
```http
GET /investigation/{investigation_id}/status
```

**Response (200):**
```json
{
  "investigation_id": "inv_abc123def456",
  "status": "IN_PROGRESS",
  "progress": 0.65,
  "current_stage": "specialist_agents",
  "agents": {
    "transaction": {
      "status": "COMPLETED",
      "risk_score": 0.78,
      "confidence": 0.92,
      "findings": ["unusual_velocity", "pattern_anomaly"]
    },
    "kyc_device": {
      "status": "COMPLETED",
      "risk_score": 0.65,
      "confidence": 0.88,
      "findings": ["device_mismatch", "behavioral_anomaly"]
    },
    "sanctions": {
      "status": "IN_PROGRESS",
      "progress": 0.80,
      "findings": []
    }
  },
  "created_at": "2026-05-12T14:30:00Z",
  "updated_at": "2026-05-12T14:38:00Z"
}
```

#### Run Specific Agent
```http
POST /investigation/{investigation_id}/agents/{agent_type}
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction_data": {
    "transaction_id": "TX123456789",
    "amount": 15000.00,
    "timestamp": "2026-05-12T14:30:00Z",
    "recipient_account": "REC789456123"
  },
  "customer_context": {
    "customer_id": "CUST001",
    "account_age": 365,
    "transaction_history": ["TX001", "TX002", "TX003"]
  }
}
```

**Response (200):**
```json
{
  "agent_type": "transaction",
  "status": "COMPLETED",
  "risk_score": 0.78,
  "confidence": 0.92,
  "findings": [
    {
      "type": "velocity_anomaly",
      "description": "Transaction amount 3x higher than customer average",
      "severity": "high",
      "confidence": 0.95
    },
    {
      "type": "timing_anomaly",
      "description": "Transaction occurred outside normal business hours",
      "severity": "medium",
      "confidence": 0.88
    }
  ],
  "recommendations": ["manual_review", "enhanced_monitoring"],
  "execution_time": 2.3
}
```

#### Synthesize Investigation Results
```http
POST /investigation/{investigation_id}/synthesize
Content-Type: application/json
```

**Request Body:**
```json
{
  "agent_results": {
    "transaction": {
      "risk_score": 0.78,
      "confidence": 0.92,
      "findings": ["velocity_anomaly", "timing_anomaly"]
    },
    "kyc_device": {
      "risk_score": 0.65,
      "confidence": 0.88,
      "findings": ["device_mismatch", "behavioral_anomaly"]
    },
    "sanctions": {
      "risk_score": 0.45,
      "confidence": 0.95,
      "findings": ["no_matches"]
    }
  }
}
```

**Response (200):**
```json
{
  "investigation_id": "inv_abc123def456",
  "composite_risk_score": 0.73,
  "risk_level": "HIGH",
  "confidence": 0.91,
  "executive_summary": "High-value transaction to high-risk jurisdiction with multiple behavioral anomalies. Recommended for immediate human review.",
  "key_findings": [
    "Transaction amount significantly exceeds customer historical patterns",
    "Unusual timing and device usage detected",
    "No sanctions matches found"
  ],
  "recommendations": [
    "escalate_to_human_review",
    "enhanced_monitoring",
    "consider_temporary_restriction"
  ],
  "evidence_package": {
    "transaction_analysis": {...},
    "kyc_analysis": {...},
    "sanctions_analysis": {...}
  }
}
```

### 📊 Data Sources

#### Get Customer Context
```http
GET /data/customers/{customer_id}
```

**Response (200):**
```json
{
  "customer_id": "CUST001",
  "account_id": "ACC987654321",
  "customer_type": "individual",
  "account_age_days": 365,
  "risk_profile": "medium",
  "kyc_status": "verified",
  "transaction_summary": {
    "total_transactions": 156,
    "total_amount": 45678.90,
    "average_amount": 292.82,
    "last_transaction": "2026-05-11T16:45:00Z"
  },
  "device_profile": {
    "primary_device": "DEV001",
    "device_trust_score": 0.82,
    "last_seen": "2026-05-12T14:25:00Z"
  },
  "behavioral_patterns": {
    "typical_hours": "09:00-17:00",
    "typical_amount_range": "50-500",
    "frequency_pattern": "2-3_transactions_per_week"
  }
}
```

#### Get Transaction History
```http
GET /data/transactions/{customer_id}?limit=50&days=30
```

**Response (200):**
```json
{
  "customer_id": "CUST001",
  "transactions": [
    {
      "transaction_id": "TX123456788",
      "amount": 250.00,
      "currency": "USD",
      "timestamp": "2026-05-11T16:45:00Z",
      "recipient_country": "US",
      "status": "completed",
      "risk_score": 0.12
    },
    {
      "transaction_id": "TX123456787",
      "amount": 180.00,
      "currency": "USD",
      "timestamp": "2026-05-10T14:22:00Z",
      "recipient_country": "CA",
      "status": "completed",
      "risk_score": 0.08
    }
  ],
  "summary": {
    "total_count": 48,
    "total_amount": 12456.78,
    "average_amount": 259.51,
    "risk_distribution": {
      "low": 0.75,
      "medium": 0.20,
      "high": 0.05
    }
  }
}
```

### 🎯 HITL (Human-in-the-Loop)

#### Submit Analyst Decision
```http
POST /investigation/{investigation_id}/hitl/decision
Content-Type: application/json
```

**Request Body:**
```json
{
  "analyst_id": "ANALYST001",
  "decision": "CONFIRM_FRAUD",
  "confidence": 0.95,
  "reasoning": "Transaction pattern clearly indicates fraudulent activity based on velocity anomalies and timing.",
  "actions": ["block_account", "freeze_transaction", "report_authorities"],
  "additional_evidence": {
    "manual_notes": "Customer account shows signs of takeover",
    "external_references": ["police_report_123"]
  }
}
```

**Response (200):**
```json
{
  "investigation_id": "inv_abc123def456",
  "decision_id": "dec_xyz789uvw456",
  "status": "RESOLVED",
  "resolution": "CONFIRMED_FRAUD",
  "actions_taken": [
    {
      "action": "block_account",
      "status": "completed",
      "timestamp": "2026-05-12T14:45:00Z"
    },
    {
      "action": "freeze_transaction",
      "status": "completed",
      "timestamp": "2026-05-12T14:45:00Z"
    }
  ],
  "fraud_memory_updated": true,
  "compliance_report_generated": true
}
```

#### Get HITL Queue
```http
GET /investigation/hitl/queue?status=pending&priority=high
```

**Response (200):**
```json
{
  "queue_items": [
    {
      "investigation_id": "inv_abc123def456",
      "priority": "high",
      "risk_score": 0.85,
      "alert_type": "suspicious_transaction",
      "customer_id": "CUST001",
      "amount": 15000.00,
      "queued_at": "2026-05-12T14:30:00Z",
      "ai_recommendation": "CONFIRM_FRAUD",
      "ai_confidence": 0.91
    }
  ],
  "queue_summary": {
    "total_pending": 5,
    "high_priority": 2,
    "medium_priority": 2,
    "low_priority": 1,
    "average_wait_time": 12.5
  }
}
```

### 📈 Analytics & Reporting

#### Get Investigation Metrics
```http
GET /analytics/metrics?period=7d
```

**Response (200):**
```json
{
  "period": "7d",
  "metrics": {
    "total_investigations": 156,
    "confirmed_fraud": 23,
    "false_positives": 12,
    "pending_review": 8,
    "average_processing_time": 4.2,
    "ai_accuracy": 0.89,
    "hitl_approval_rate": 0.78
  },
  "trends": {
    "daily_investigations": [22, 18, 25, 20, 23, 24, 24],
    "fraud_detection_rate": [0.12, 0.15, 0.18, 0.14, 0.16, 0.13, 0.15],
    "processing_times": [4.1, 3.8, 4.5, 4.2, 3.9, 4.3, 4.2]
  },
  "agent_performance": {
    "transaction_agent": {
      "accuracy": 0.91,
      "avg_processing_time": 1.2,
      "success_rate": 0.98
    },
    "kyc_agent": {
      "accuracy": 0.87,
      "avg_processing_time": 1.8,
      "success_rate": 0.96
    },
    "sanctions_agent": {
      "accuracy": 0.99,
      "avg_processing_time": 0.8,
      "success_rate": 0.99
    }
  }
}
```

#### Generate Compliance Report
```http
POST /reports/compliance
Content-Type: application/json
```

**Request Body:**
```json
{
  "report_type": "weekly",
  "start_date": "2026-05-06",
  "end_date": "2026-05-12",
  "include_details": true,
  "format": "json"
}
```

**Response (200):**
```json
{
  "report_id": "rpt_456def789abc",
  "report_type": "weekly",
  "period": "2026-05-06 to 2026-05-12",
  "summary": {
    "total_alerts": 156,
    "investigations_completed": 148,
    "fraud_confirmed": 23,
    "false_positives": 12,
    "detection_rate": 0.147,
    "accuracy_rate": 0.889
  },
  "detailed_investigations": [...],
  "compliance_metrics": {
    "regulatory_filings": 23,
    "audit_trail_complete": true,
    "data_retention_compliant": true
  },
  "generated_at": "2026-05-12T15:00:00Z"
}
```

### 🔧 System Administration

#### Health Check
```http
GET /health
```

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2026-05-12T15:00:00Z",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "ai_services": "healthy"
  },
  "metrics": {
    "uptime": 99.98,
    "memory_usage": 0.67,
    "cpu_usage": 0.34,
    "active_investigations": 8
  }
}
```

#### System Status
```http
GET /system/status
```

**Response (200):**
```json
{
  "system_status": "operational",
  "version": "1.0.0",
  "deployment": "production",
  "last_updated": "2026-05-12T14:45:00Z",
  "components": {
    "api_gateway": "healthy",
    "investigation_engine": "healthy",
    "ai_agents": "healthy",
    "database": "healthy",
    "cache": "healthy",
    "monitoring": "healthy"
  },
  "performance": {
    "response_time_p95": 245,
    "throughput_rps": 156,
    "error_rate": 0.002
  },
  "active_resources": {
    "investigations_in_progress": 8,
    "agents_running": 6,
    "queue_depth": 3
  }
}
```

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "amount",
      "issue": "Amount must be greater than 0"
    },
    "timestamp": "2026-05-12T15:00:00Z",
    "request_id": "req_abc123def456"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing API key |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Rate Limiting

- **Standard**: 100 requests per minute
- **Burst**: 200 requests per minute
- **Enterprise**: 1000 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 16467890
```

## Webhooks

### Configure Webhook Endpoints

```http
POST /webhooks/configure
Content-Type: application/json
```

**Request Body:**
```json
{
  "url": "https://your-system.com/webhooks/fraud-alerts",
  "events": ["investigation_completed", "fraud_confirmed", "high_risk_alert"],
  "secret": "webhook-secret-key",
  "active": true
}
```

### Webhook Event Payloads

#### Investigation Completed
```json
{
  "event": "investigation_completed",
  "investigation_id": "inv_abc123def456",
  "status": "COMPLETED",
  "risk_score": 0.73,
  "resolution": "NO_FRAUD",
  "timestamp": "2026-05-12T15:00:00Z"
}
```

#### Fraud Confirmed
```json
{
  "event": "fraud_confirmed",
  "investigation_id": "inv_abc123def456",
  "customer_id": "CUST001",
  "transaction_id": "TX123456789",
  "amount": 15000.00,
  "risk_score": 0.92,
  "actions_taken": ["block_account", "freeze_transaction"],
  "timestamp": "2026-05-12T15:00:00Z"
}
```

## SDK Integration

### Python SDK Example

```python
from fraud_investigator import FraudInvestigatorClient

# Initialize client (api_key=None for local when API_KEY is unset on the server)
client = FraudInvestigatorClient(
    api_key=None,
    base_url="http://localhost:8000"
)

# Create alert
alert = client.create_alert(
    transaction_id="TX123456789",
    amount=15000.00,
    currency="USD",
    account_id="ACC987654321",
    recipient_country="IR"
)

# Start investigation
investigation = client.start_investigation(
    transaction_id="TX123456789",
    customer_id="CUST001",
    amount=15000.00,
    destination_country="IR"
)

# Get status
status = client.get_investigation_status(investigation.investigation_id)
print(f"Status: {status.status}, Progress: {status.progress}")
```

### JavaScript SDK Example

```javascript
import { FraudInvestigatorClient } from '@fraud-investigator/sdk';

const client = new FraudInvestigatorClient({
  apiKey: undefined, // omit for local when API_KEY is unset on the server
  baseUrl: 'http://localhost:8000'
});

// Create alert and start investigation
async function processTransaction(transactionData) {
  const alert = await client.createAlert(transactionData);
  const investigation = await client.startInvestigation({
    transaction_id: transactionData.id,
    customer_id: transactionData.customerId,
    amount: transactionData.amount,
    destination_country: transactionData.recipientCountry
  });
  
  return investigation;
}
```

## Testing

### Test Environment

- **URL**: `https://api-test.fraud-investigator.example.com`
- **API key**: not used locally; if the test server sets `API_KEY`, send matching `X-API-Key`
- **Database**: Isolated test database with sample data

### Sample Test Cases

```bash
# Health check
curl -X GET https://api-test.fraud-investigator.example.com/health

# Create test alert
curl -X POST https://api-test.fraud-investigator.example.com/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TEST001",
    "amount": 5000.00,
    "currency": "USD",
    "account_id": "TEST_ACC001",
    "recipient_country": "IR"
  }'
```

## Support

- **Documentation**: https://docs.fraud-investigator.example.com
- **Support Email**: api-support@fraud-investigator.example.com
- **Status Page**: https://status.fraud-investigator.example.com
- **API Version**: v1.0.0

## Changelog

### v1.0.0 (2026-05-12)
- Initial API release
- Core fraud investigation endpoints
- HITL decision support
- Analytics and reporting
- Webhook integration
- Python and JavaScript SDKs

---

*This documentation is for the Agentic AI Fraud Investigator API v1.0.0. For the most up-to-date information, visit our developer portal.*
