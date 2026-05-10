# Agentic AI Fraud Investigator

An MVP fraud investigation system combining rule-based detection with AI-powered analysis for near real-time fraud detection and risk assessment.

## 💡 Motivation

Traditional fraud systems rely heavily on static rules and struggle to detect evolving fraud patterns. This project explores how agentic AI workflows and LLM reasoning can enhance fraud investigation while maintaining explainability through rule-based scoring.

## 🎯 Current MVP Scope

### What's Implemented Today
- ✅ **Hybrid Risk Scoring**: Rule-based + AI context with adaptive weighting
- ✅ **Multi-Provider LLM Support**: Cerebras and Gemini with async architecture
- ✅ **LangGraph Workflow**: Automated investigation orchestration
- ✅ **REST API**: FastAPI endpoints for fraud detection
- ✅ **Low-latency Fraud Scoring**: Transaction analysis with immediate response
- ✅ Structured JSON-based LLM Responses

### What's Not Implemented Yet
- ❌ **SAR Filing**: Automated suspicious activity reporting
- ❌ **Live Sanctions APIs**: Real-time watchlist integration
- ❌ **Dynamic AI Learning**: Model training on new fraud patterns
- ❌ **Advanced Monitoring**: Prometheus/Grafana dashboards
- ❌ **Streaming Pipelines**: Real-time data ingestion

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 FRAUD DETECTION SYSTEM                │
├─────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                │
│  • POST /api/v1/alerts/trigger                      │
│  • POST /api/v1/scoring/calculate                  │
│  • GET /api/v1/investigations/{case_id}           │
├─────────────────────────────────────────────────┤
│  Workflow Layer (LangGraph)                            │
│  • Alert Triage → Analysis → Investigation               │
│  • State Management & Orchestration                     │
├─────────────────────────────────────────────────┤
│  Detection Layer                                       │
│  • Hybrid Scoring Engine (Rules + AI)                   │
│  • Multi-Provider LLM Client (Cerebras, Gemini)          │
│  • Risk Factor Analysis                                   │
├─────────────────────────────────────────────────┤
│  Data Layer                                             │
│  • PostgreSQL (Transaction Storage)                        │
│  • Redis (Cache & Queue)                                 │
└─────────────────────────────────────────────────┘
```

## 🧠 Design Principles

- **Async-first architecture**: Non-blocking I/O for high-throughput processing
- **Hybrid AI + deterministic scoring**: Combines rule-based reliability with AI contextual analysis
- **Provider-agnostic LLM integration**: Clean abstraction for Cerebras, Gemini, OpenAI
- **Explainable fraud analysis**: Transparent risk factors and decision logic
- **Graceful fallback mechanisms**: Robust error handling with rule-based backup

## 🔄 Simple Workflow

```
Alert Triggered → Risk Scoring → Investigation Decision → Action Required
     ↓                    ↓                    ↓                    ↓
  Transaction          Hybrid Score          Generate Case        Block/Allow
  Analysis              (Rules + AI)          Recommendations   Transaction
```

## 🛠️ Tech Stack

### Core Technologies
- **Backend**: FastAPI with async support
- **Workflow**: LangGraph for investigation orchestration
- **AI/LLM**: Cerebras and Gemini integration
- **Database**: PostgreSQL for transaction storage
- **Cache**: Redis for performance optimization

### Key Libraries
- **LangChain**: LLM abstraction and prompts
- **LangSmith**: AI observability and tracking
- **Pydantic**: Data validation and settings
- **Tenacity**: Retry logic with exponential backoff
- **httpx**: Async HTTP client for LLM calls

## 🚀 Quick Start

### Prerequisites
```bash
# Clone repository
git clone https://github.com/habeneyasu/Agentic-AI-Fraud-Investigator.git
cd Agentic-AI-Fraud-Investigator

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment Setup
```bash
# Required API Keys
CEREBRAS_API_KEY=your_cerebras_key
GEMINI_API_KEY=your_gemini_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/fraud_investigator
REDIS_URL=redis://localhost:6379

# Scoring Configuration
TRANSACTION_AMOUNT_THRESHOLD=10000.0
RISK_SCORE_THRESHOLD=0.7
```

### Running the System
```bash
# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production with Docker
docker-compose up -d
```

## 📊 Usage Examples

### Fraud Detection
```python
import asyncio
from app.graph.scoring import calculate_risk_score, ScoringMode

async def detect_fraud():
    transaction_event = {
        'amount': 15000,
        'sender': 'user123',
        'receiver': 'merchant456',
        'new_device': True,
        'high_risk_country': False,
        'failed_attempts': 0
    }
    
    # Hybrid scoring (default)
    result = await calculate_risk_score(transaction_event)
    print(f"Risk Score: {result.risk_score:.3f}")
    print(f"Risk Level: {result.risk_level}")
    print(f"Factors: {[f.description for f in result.factors]}")
    
    # Rules-only scoring
    rules_result = await calculate_risk_score(transaction_event, ScoringMode.RULES_ONLY)
    
    # AI-only scoring
    ai_result = await calculate_risk_score(transaction_event, ScoringMode.AI_ONLY)

asyncio.run(detect_fraud())
```

### LLM Client Integration
```python
from app.llm.client import LLMClient, LLMProvider

# Initialize client
client = LLMClient(LLMProvider.CEREBRAS)

# Analyze transaction
transaction_data = {'amount': 5000, 'sender': 'user123', 'receiver': 'merchant456'}
context = {'customer_risk_profile': 'medium', 'previous_alerts': 2}

result = await client.analyze_transaction(transaction_data, context)
print(f"Analysis: {result['response']}")
```

### Realistic Response Example
```json
{
  "risk_score": 0.82,
  "risk_level": "HIGH",
  "factors": [
    {
      "factor": "new_device",
      "description": "New device detected"
    },
    {
      "factor": "large_amount", 
      "description": "Transaction amount exceeds threshold"
    }
  ],
  "recommended_action": "Manual review required"
}
```

## 📋 Risk Scoring

### Score Interpretation
| Score Range | Risk Level | Action Required |
|-------------|-------------|-----------------|
| 0.80-1.00 | CRITICAL    | Immediate block, investigation |
| 0.60-0.79 | HIGH        | Enhanced monitoring, manual review |
| 0.40-0.59 | MEDIUM      | Standard monitoring, documentation |
| 0.20-0.39 | LOW         | Basic monitoring, periodic review |
| 0.00-0.19 | MINIMAL     | Normal processing, no action |

### Risk Categories
- **Transaction**: Amount anomalies, timing patterns, frequency issues
- **Device**: New/unknown devices, device fingerprinting
- **Geographic**: High-risk countries, unusual locations
- **Sanctions**: Watchlist matches, PEP entities
- **Behavior**: Failed attempts, unusual timing, high frequency
- **AI Context**: LLM-powered contextual analysis

## 📐 Screenshots & Architecture

### Workflow Diagram
```
┌─────────────────────────────────────────┐
│           FRAUD WORKFLOW           │
├─────────────────────────────────────────┤
│  Alert → Analysis → Scoring → Decision → Action   │
├─────────────────────────────────────────┤
│  LangGraph Orchestration                        │
│  • State Management                               │
│  • Error Handling                                   │
│  • Parallel Processing                               │
└─────────────────────────────────────────┘
```

### API Documentation
- Swagger UI at `http://localhost:8000/docs`
- Interactive API testing
- Auto-generated request/response examples

## 🧪 Configuration

### Scoring Rules
```python
# Transaction rules
TRANSACTION_AMOUNT_THRESHOLD = 10000.0
TRANSACTION_WEIGHT = 0.3

# Device rules
NEW_DEVICE_PENALTY = 0.2
UNKNOWN_DEVICE_PENALTY = 0.3

# Geographic rules
HIGH_RISK_COUNTRY_PENALTY = 0.4
UNUSUAL_LOCATION_PENALTY = 0.2

# Sanctions rules
SANCTIONED_ENTITY_PENALTY = 0.8
PEP_ENTITY_PENALTY = 0.5

# Behavior rules
FAILED_LOGIN_PENALTY = 0.15
UNUSUAL_TIMING_PENALTY = 0.1
HIGH_FREQUENCY_PENALTY = 0.2
```

### Adaptive Hybrid Scoring
```python
# Dynamic weighting based on AI confidence
if ai_confidence < 0.5:
    rule_weight = 0.8  # Trust proven rules more
    ai_weight = 0.2
elif ai_confidence > 0.9:
    rule_weight = 0.4  # Trust AI insights more
    ai_weight = 0.6
else:
    rule_weight = 0.6  # Balanced approach
    ai_weight = 0.4
```

## 📈 API Documentation

### Core Endpoints

#### POST /api/v1/alerts/trigger
Trigger fraud investigation workflow
```json
{
  "transaction_id": "txn_123456",
  "amount": 15000.00,
  "currency": "USD",
  "customer_id": "cust_789",
  "alert_type": "high_amount"
}
```

#### POST /api/v1/scoring/calculate
Calculate risk score for event
```json
{
  "event_type": "transaction",
  "amount": 25000.00,
  "sender": "user123",
  "receiver": "merchant456",
  "new_device": true,
  "high_risk_country": false
}
```

#### GET /api/v1/investigations/{case_id}
Get investigation details and recommendations

## 🔒 Security Features

### Input Validation
- Pydantic schemas for all API inputs
- SQL injection protection
- Rate limiting per endpoint

### Authentication
- JWT-based authentication
- API key management
- Role-based access control

## ⚠️ Current Limitations

- Uses prompt-engineered LLM analysis instead of trained fraud models
- No live sanctions provider integration yet
- Limited historical behavioral analysis
- Optimized for demonstration and experimentation
- LLM outputs may vary depending on provider response quality

## 🚀 Deployment

### Docker Configuration
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CEREBRAS_API_KEY=${CEREBRAS_API_KEY}
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=fraud_investigator
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## 📁 Project Structure

```
app/
├── api/           # FastAPI endpoints
├── core/          # Config, logging, security
├── graph/         # LangGraph workflows
├── llm/           # LLM providers and prompts
├── models/        # Pydantic schemas
├── repositories/  # Database access layer
├── services/      # Business logic
└── tests/         # Unit and integration tests
```

## 🔮 Future Enhancements

### Phase 1: Core Features (Next 3 months)
- 🔄 **SAR Filing**: Automated suspicious activity reporting
- 🔄 **Live Sanctions APIs**: Real-time watchlist integration
- 🔄 **Enhanced Monitoring**: Basic metrics and alerting

### Phase 2: Intelligence (Next 6 months)
- 🧠 **Dynamic AI Learning**: Model training on fraud patterns
- 📊 **Advanced Analytics**: Pattern recognition and trend analysis
- 🔗 **External Integrations**: Third-party threat intelligence

### Phase 3: Scale (Next 12 months)
- 🌐 **Microservices Architecture**: Service decomposition
- 📈 **Streaming Pipelines**: Real-time data processing
- 🔧 **Advanced Features**: Case management, collaboration tools

## 🛠️ Local Development

```bash
# Setup development environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black .

# Lint code
ruff check .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Project Wiki](https://github.com/habeneyasu/Agentic-AI-Fraud-Investigator/wiki)
- **Issues**: [GitHub Issues](https://github.com/habeneyasu/Agentic-AI-Fraud-Investigator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/habeneyasu/Agentic-AI-Fraud-Investigator/discussions)

---

**Built to explore agentic AI workflows for fraud detection and investigation.**
