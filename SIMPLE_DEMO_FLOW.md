# 🎯 Simple Demo Flow: Database → Dashboard

## 📋 Step 1: Data Setup (You Have This)

### **Transaction Data in Database**
```
Customer: CUST_001
- TXN_001: $15,000 (New Device, High Risk Country)
- TXN_002: $2,500 (Multiple Failed Logins)  
- TXN_003: $45,000 (Structured Pattern)
- TXN_004: $8,000 (Unusual Time)
- TXN_005: $25,000 (Impossible Travel)
```

### **KYC Data in Database**
```
Customer: CUST_001
- Device: DEV_001 (New, Suspicious Fingerprint)
- Location: US → IR (Impossible Travel in 2 hours)
- Login Pattern: 3AM (Unusual Time)
- Failed Attempts: 5 (Account Takeover Signs)
```

### **Sanctions Data in Database**
```
Entity: Global Trading Corp
- Country: IR (Under Sanctions)
- Watchlist: "weapons", "military" detected
- Risk Score: 0.9 (Critical)
```

---

## 🚨 Step 2: Alert Generation (Automatic)

### **System Detects Fraud**
1. **Transaction Agent** flags TXN_001 (velocity anomaly)
2. **KYC Agent** flags login (new device + impossible travel)
3. **Sanctions Agent** flags entity (sanctioned country)
4. **Hybrid Scoring** calculates: 0.92 (Critical Risk)
5. **Alert Created**: ALERT_001 (High Priority)

---

## 📊 Step 3: Alert Appears in Dashboard

### **Dashboard Shows New Alert**
- **🚨 Alerts Tab**: ALERT_001 appears at top
- **Details**: Transaction fraud, $15,000, critical severity
- **Status**: "Active" (red indicator)
- **Actions**: "Process Alert" button available

---

## 🔍 Step 4: Investigation Creation

### **Click "Process Alert" → Creates Investigation**
1. **System runs triage** (automated)
2. **Investigation created**: CASE_001
3. **Workflow triggered**: LangGraph starts analysis
4. **📋 Investigations Tab**: CASE_001 appears in list

---

## 📋 Step 5: Investigation Details

### **Click CASE_001 → View Details**
- **Case Info**: ID, Title, Status, Priority
- **Financial Info**: $15,000, USD, Customer CUST_001
- **Evidence**: Transaction history, device logs, location data
- **AI Analysis**: "High risk - recommend immediate action"

---

## 🎯 Step 6: Human Decision (HITL)

### **Analyst Reviews & Decides**
1. **Review evidence** in dashboard
2. **Select action**: "FREEZE ACCOUNT"
3. **Add reasoning**: "High-value transaction from new device in sanctioned country"
4. **Submit decision** → System records human input

---

## ⚡ Step 7: Action Execution

### **System Executes Resolution**
1. **Action Engine** processes "FREEZE" command
2. **Account frozen** → Customer CUST_001 locked
3. **SMS sent** → "Account frozen for security review"
4. **Status updated** → CASE_001 shows "Action Completed"

---

## 📋 Step 8: Audit Trail

### **Complete Activity Log**
- **Alert Created**: ALERT_001 at 10:30 AM
- **Investigation Started**: CASE_001 at 10:35 AM  
- **Human Decision**: FREEZE at 11:00 AM
- **Action Executed**: Account frozen at 11:05 AM
- **All steps** logged with timestamps and user IDs

---

## 📈 Step 9: Analytics Update

### **Dashboard Analytics Reflect Activity**
- **Total Alerts**: 1 (new)
- **Active Investigations**: 1 (CASE_001)
- **Priority Distribution**: Critical: 1, High: 0, Medium: 0
- **Resolution Rate**: 0% (still investigating)
- **Recent Activity**: Shows all actions in timeline

---

## 🔄 Complete Demo Flow Summary

### **What You See in Dashboard**
1. **🚨 Alerts Tab**: Real-time fraud alerts
2. **📋 Investigations Tab**: Case management with status
3. **🔍 Details Tab**: Deep dive into specific cases  
4. **📊 Analytics Tab**: System performance metrics
5. **Auto-refresh**: Updates every 5 seconds

### **LangGraph State Flow**
```
INITIAL → DATA_COLLECTION → ANALYSIS → ASSESSMENT → DECISION → ACTION → COMPLETED
    ↓              ↓              ↓           ↓         ↓        ↓
  Transaction      KYC           Sanctions    Human     Action
  Analysis        Analysis       Check        Decision   Execution
```

### **Key Features Demonstrated**
- ✅ **Multi-agent analysis** (Transaction + KYC + Sanctions)
- ✅ **Hybrid risk scoring** (Rules + AI context)
- ✅ **LangGraph orchestration** (State machine workflow)
- ✅ **Human-in-the-loop** (Analyst decision making)
- ✅ **Action execution** (Freeze, reverse, block, SMS)
- ✅ **Real-time monitoring** (Live dashboard updates)
- ✅ **Complete audit trail** (Full activity tracking)

### **Demo Value**
This shows **complete fraud investigation system**:
- From **raw data** (transactions, KYC, sanctions)
- Through **intelligent analysis** (multi-agent + AI scoring)
- To **state-based workflows** (LangGraph orchestration)  
- With **human oversight** (HITL decision making)
- Ending in **action execution** (resolution + audit)

**The system demonstrates enterprise-grade fraud detection with state-based workflow automation!** 🎯
