# 🚀 Complete Demo Preparation Guide

## 📋 Project Overview

This **Agentic AI Fraud Investigator** provides a comprehensive fraud detection system with multiple analysis layers:

### 🏗️ Architecture Components

#### **🔍 Data Analysis Agents**
- **Transaction Agent**: Velocity analysis, fraud patterns, memory lookup
- **KYC Device Agent**: Device fingerprinting, geo-location, login patterns
- **Sanctions Agent**: Country risk, sanctions lists, watchlist keywords

#### **📊 Core Systems**
- **Hybrid Scoring Engine**: Rule-based + AI context scoring
- **LangGraph Workflow**: Orchestration with conditional routing
- **LLM Integration**: OpenAI/Anthropic with structured prompts
- **Action Engine**: Freeze, reverse, block, SMS resolution actions

#### **🎯 API Layer**
- **Alerts API**: Processing, triage, workflow triggering
- **HITL API**: Human-in-the-loop decisions and escalation
- **Audit API**: Complete audit trail with filtering
- **Investigations**: Case management and status tracking

#### **📱 Dashboard Options**
- **Streamlit**: Python-based, rapid prototyping, data science friendly
- **React**: Production-ready, component-based, modern UI

---

## 🎬 End-to-End Demo Workflow

### **Step 1: Data Ingestion**
```python
# Transaction Data
transaction_data = {
    "transaction_id": "TXN_001",
    "customer_id": "CUST_001",
    "amount": 15000.00,
    "currency": "USD",
    "timestamp": "2025-05-10T10:30:00Z",
    "merchant_id": "MERCH_001",
    "device_id": "DEV_001",
    "location": "US",
    "ip_address": "192.168.1.1"
}

# KYC Event Data
kyc_event = {
    "customer_id": "CUST_001",
    "event_type": "login",
    "device_info": {
        "device_id": "DEV_001",
        "fingerprint": {"screen_resolution": "1920x1080", "timezone": "UTC"},
        "user_agent": "Mozilla/5.0..."
    },
    "location": {
        "ip_address": "192.168.1.1",
        "country": "US",
        "latitude": 40.7128,
        "longitude": -74.0060
    }
}

# Sanctions Check Data
sanctions_data = {
    "entity_name": "Global Trading Corp",
    "country_code": "US",
    "entity_type": "organization",
    "description": "International trading company"
}
```

### **Step 2: Agent Analysis**
```python
# Transaction Analysis
from app.agents.transaction import analyze_transaction
transaction_result = await analyze_transaction(transaction_data, customer_history)

# KYC Analysis  
from app.agents.kyc_device import analyze_kyc_event
kyc_result = await analyze_kyc_event(kyc_event)

# Sanctions Analysis
from app.agents.sanctions import analyze_sanctions_risk
sanctions_result = await analyze_sanctions_risk(sanctions_data)
```

### **Step 3: Risk Scoring**
```python
# Hybrid Risk Calculation
from app.graph.scoring import calculate_risk_score
risk_result = await calculate_risk_score({
    "transaction_analysis": transaction_result,
    "kyc_analysis": kyc_result,
    "sanctions_analysis": sanctions_result
})
```

### **Step 4: Workflow Orchestration**
```python
# LangGraph Workflow
from app.graph.workflow import execute_fraud_workflow
workflow_result = await execute_fraud_workflow(InvestigationState(
    case_id="CASE_001",
    case_type="TRANSACTION_FRAUD",
    transaction_data=[transaction_data],
    kyc_data=[kyc_event],
    entities=[sanctions_data]
))
```

### **Step 5: Alert Generation**
```python
# Create Alert
import requests
alert_response = requests.post("http://localhost:8000/api/alerts/process", json={
    "alert_type": "TRANSACTION_FRAUD",
    "severity": "high",
    "source": "transaction_monitoring",
    "case_data": {
        "case_id": "CASE_001",
        "title": "Suspicious High-Value Transaction",
        "description": "Multiple fraud indicators detected"
    }
})
```

### **Step 6: Investigation Management**
```python
# Get Investigation Status
case_status = requests.get("http://localhost:8000/api/hitl/CASE_001/status")

# Submit Human Decision
decision_response = requests.post("http://localhost:8000/api/hitl/CASE_001/decision", json={
    "decision": "FREEZE",
    "reasoning": "High-risk transaction with multiple fraud indicators",
    "confidence": 0.9
})
```

### **Step 7: Action Execution**
```python
# Execute Resolution Actions
action_response = requests.post("http://localhost:8000/api/actions/execute", json={
    "action_type": "freeze",
    "case_id": "CASE_001",
    "reason": "Account freeze due to fraud investigation",
    "target_id": "CUST_001"
})
```

---

## 🖥 Dashboard Deployment Options

### **Option A: Streamlit Dashboard** 🐍
**Best for**: Rapid prototyping, data science teams, quick demos

#### **Setup & Run**
```bash
# Install dependencies
source .venv/bin/activate
pip install streamlit requests pandas

# Run dashboard
streamlit run dashboard/streamlit_app.py --server.port 8501
```

#### **Features**
- ✅ Real-time investigation monitoring
- ✅ Alert processing interface
- ✅ Analytics and charts
- ✅ Auto-refresh with configurable intervals
- ✅ Mock data fallback for offline testing
- ✅ Four-tab layout: Investigations, Details, Analytics, Alerts

#### **Access**: `http://localhost:8501`

### **Option B: React Dashboard** ⚛️
**Best for**: Production deployment, modern UI, component reusability

#### **Setup & Run**
```bash
# Create React app
npx create-react-app fraud-dashboard
cd fraud-dashboard

# Install dependencies
npm install axios recharts @mui/material @emotion/react @emotion/styled

# Run development server
npm start
```

#### **Key Components**
```jsx
// InvestigationList.jsx
const InvestigationList = () => {
  const [investigations, setInvestigations] = useState([]);
  
  useEffect(() => {
    fetch('/api/investigations')
      .then(res => res.json())
      .then(setInvestigations);
  }, []);

  return (
    <Table>
      {investigations.map(inv => (
        <TableRow key={inv.case_id}>
          <TableCell>{inv.title}</TableCell>
          <TableCell>{inv.status}</TableCell>
          <TableCell>{inv.priority}</TableCell>
        </TableRow>
      ))}
    </Table>
  );
};
```

#### **Access**: `http://localhost:3000`

---

## 🛠️ Complete Demo Script

### **Automated Demo Setup**
```python
# demo_setup.py
import asyncio
import requests
from datetime import datetime

async def run_complete_demo():
    """Run end-to-end fraud investigation demo."""
    
    print("🚀 Starting Agentic AI Fraud Investigator Demo")
    
    # Step 1: Create fraudulent transaction
    transaction_data = {
        "transaction_id": f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "customer_id": "DEMO_CUSTOMER",
        "amount": 25000.00,
        "currency": "USD",
        "timestamp": datetime.now().isoformat(),
        "merchant_id": "HIGH_RISK_MERCHANT",
        "device_id": "NEW_DEVICE_001",
        "location": "HIGH_RISK_COUNTRY"
    }
    
    print("📊 Step 1: Processing transaction...")
    alert_response = requests.post("http://localhost:8000/api/alerts/from-transaction", 
                               json=transaction_data)
    
    if alert_response.status_code == 200:
        alert_data = alert_response.json()
        case_id = alert_data.get('case_id')
        print(f"✅ Alert created: {alert_data.get('alert_id')}")
        print(f"📋 Case generated: {case_id}")
        
        # Step 2: Trigger investigation workflow
        print("🔍 Step 2: Triggering investigation workflow...")
        workflow_response = requests.post("http://localhost:8000/api/alerts/trigger-workflow",
                                    json={"case_id": case_id})
        
        if workflow_response.status_code == 200:
            print("✅ Workflow triggered successfully")
            
            # Step 3: Human decision
            print("👤 Step 3: Submitting human decision...")
            decision_response = requests.post(f"http://localhost:8000/api/hitl/{case_id}/decision",
                                       json={
                                           "decision": "FREEZE",
                                           "reasoning": "High-value transaction from new device in high-risk location",
                                           "confidence": 0.9
                                       })
            
            if decision_response.status_code == 200:
                print("✅ Human decision submitted")
                
                # Step 4: Execute action
                print("⚡ Step 4: Executing resolution action...")
                action_response = requests.post("http://localhost:8000/api/actions/execute",
                                           json={
                                               "action_type": "freeze",
                                               "case_id": case_id,
                                               "reason": "Account freeze due to fraud investigation"
                                           })
                
                if action_response.status_code == 200:
                    print("✅ Action executed successfully")
                    print("🎉 Demo completed successfully!")
                else:
                    print("❌ Action execution failed")
            else:
                print("❌ Human decision failed")
        else:
            print("❌ Workflow trigger failed")
    else:
        print("❌ Alert creation failed")
    
    # Step 5: Check audit trail
    print("📋 Step 5: Checking audit trail...")
    audit_response = requests.get("http://localhost:8000/api/audit/all")
    
    if audit_response.status_code == 200:
        audit_data = audit_response.json()
        print(f"✅ Audit trail contains {len(audit_data)} entries")
    
    print("🏁 Demo complete!")

if __name__ == "__main__":
    asyncio.run(run_complete_demo())
```

---

## 🎯 Demo Scenarios

### **Scenario 1: Transaction Fraud** 💳
```python
fraudulent_transaction = {
    "amount": 50000.00,  # High value
    "new_device": True,  # New device
    "high_risk_country": True,  # Sanctioned country
    "velocity_anomaly": True,  # Unusual frequency
    "failed_attempts": 5  # Multiple login failures
}
```

### **Scenario 2: Account Takeover** 🔐
```python
account_takeover = {
    "impossible_travel": True,  # Login from different continent
    "suspicious_device": True,  # Bot fingerprint
    "multiple_failed_attempts": True,  # Brute force attempt
    "unusual_time": True  # 3AM login
}
```

### **Scenario 3: Money Laundering** 💰
```python
money_laundering = {
    "structured_transactions": True,  # Round amounts, regular intervals
    "sanctioned_entity": True,  # Known bad actor
    "high_risk_country": True,  # Tax haven
    "watchlist_keywords": True  # Suspicious terminology
}
```

---

## 🚀 Quick Start Commands

### **Streamlit Dashboard**
```bash
# Terminal 1: Start API server
cd /home/haben/Project/Agentic-AI-Fraud-Investigator
source .venv/bin/activate
python -m app.main

# Terminal 2: Start dashboard
cd /home/haben/Project/Agentic-AI-Fraud-Investigator
source .venv/bin/activate
streamlit run dashboard/streamlit_app.py --server.port 8501

# Terminal 3: Run demo
python demo_setup.py
```

### **React Dashboard**
```bash
# Terminal 1: Start API server
cd /home/haben/Project/Agentic-AI-Fraud-Investigator
source .venv/bin/activate
python -m app.main

# Terminal 2: Start React app
cd fraud-dashboard
npm start

# Terminal 3: Run demo
python demo_setup.py
```

---

## 📊 Monitoring & Analytics

### **Key Metrics to Track**
- **Alert Volume**: Number of fraud alerts generated
- **Detection Rate**: Percentage of fraud caught vs. total
- **False Positive Rate**: Legitimate transactions flagged
- **Investigation Time**: Average time to resolution
- **Action Success Rate**: Resolution actions completed

### **Dashboard Analytics**
- **Status Distribution**: Open vs. resolved cases
- **Priority Breakdown**: Critical, high, medium, low
- **Risk Score Trends**: Over time analysis
- **Agent Performance**: Individual agent effectiveness

---

## 🎯 Success Criteria

### **Functional Requirements**
- ✅ All agents process data correctly
- ✅ Risk scoring produces accurate results
- ✅ Workflow orchestrates end-to-end
- ✅ Dashboard displays real-time data
- ✅ Actions execute successfully
- ✅ Audit trail captures all activities

### **Performance Requirements**
- ✅ Sub-second response times for analysis
- ✅ Real-time dashboard updates
- ✅ Concurrent processing capability
- ✅ Error handling and recovery
- ✅ Mock data fallback for testing

---

## 🔧 Troubleshooting

### **Common Issues**
1. **API Connection Failed**: Ensure backend server is running on port 8000
2. **Dashboard Not Loading**: Check Streamlit installation and port conflicts
3. **Mock Data Only**: API endpoints not accessible, using fallback data
4. **Actions Not Executing**: Verify action engine configuration

### **Debug Commands**
```bash
# Check API health
curl http://localhost:8000/health

# Check dashboard
curl http://localhost:8501

# View logs
tail -f logs/fraud_investigator.log
```

---

## 🏁 Conclusion

This comprehensive demo showcases the complete **Agentic AI Fraud Investigator** system with:

- **Multi-layered fraud detection** (Transaction, KYC, Sanctions)
- **Intelligent risk scoring** (Hybrid rule-based + AI)
- **Workflow orchestration** (LangGraph with conditional routing)
- **Human-in-the-loop** (Decision making and escalation)
- **Action execution** (Freeze, reverse, block, SMS)
- **Real-time monitoring** (Dashboard with analytics)
- **Complete audit trail** (Full activity tracking)

Choose **Streamlit** for rapid development and data science workflows, or **React** for production-ready modern UI deployment.

**The system is ready for immediate demonstration!** 🚀
