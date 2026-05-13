"""
File-based data loader for fraud investigation system.
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


class DataLoader:
    """File-based data loader for fraud investigation system."""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__))
        self.data_dir = data_dir

        # Cache loaded data
        self._customers_cache = None
        self._transactions_cache = None
        self._kyc_events_cache = None
        self._sanctions_data_cache = None
        self._fraud_memory_cache = None

    def _load_json_file(self, filename: str) -> Any:
        """Load and parse JSON file."""
        try:
            file_path = os.path.join(self.data_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Data file not found: {filename}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON file {filename}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading data file {filename}: {e}")
            return []

    def get_customers(self) -> List[Dict[str, Any]]:
        """Get customer data."""
        if self._customers_cache is None:
            self._customers_cache = self._load_json_file('customers.json')
            logger.info(f"Loaded {len(self._customers_cache)} customers")
        return self._customers_cache

    def get_transactions(self, customer_id: str = None) -> List[Dict[str, Any]]:
        """Get transaction data, optionally filtered by customer."""
        if self._transactions_cache is None:
            self._transactions_cache = self._load_json_file('transactions.json')
            logger.info(f"Loaded {len(self._transactions_cache)} transactions")

        if customer_id:
            return [t for t in self._transactions_cache if t.get("customer_id") == customer_id]
        return self._transactions_cache

    def get_all_transactions(self) -> List[Dict[str, Any]]:
        """Get all transaction data."""
        return self.get_transactions()

    def get_kyc_events(self, customer_id: str = None) -> List[Dict[str, Any]]:
        """Get KYC event data, optionally filtered by customer."""
        if self._kyc_events_cache is None:
            self._kyc_events_cache = self._load_json_file('kyc_events.json')
            logger.info(f"Loaded {len(self._kyc_events_cache)} KYC events")

        if customer_id:
            return [k for k in self._kyc_events_cache if k.get("customer_id") == customer_id]
        return self._kyc_events_cache

    def get_all_kyc_events(self) -> List[Dict[str, Any]]:
        """Get all KYC event data."""
        return self.get_kyc_events()

    def get_sanctions_data(self) -> Dict[str, Any]:
        """Get sanctions data."""
        if self._sanctions_data_cache is None:
            self._sanctions_data_cache = self._load_json_file('sanctions_data.json')
            logger.info(f"Loaded sanctions data with {len(self._sanctions_data_cache.get('sanctions_entries', []))} entries")
        return self._sanctions_data_cache

    def get_fraud_memory(self) -> List[Dict[str, Any]]:
        """Get fraud memory patterns."""
        if self._fraud_memory_cache is None:
            self._fraud_memory_cache = self._load_json_file('fraud_memory.json')
            logger.info(f"Loaded {len(self._fraud_memory_cache)} fraud patterns")
        return self._fraud_memory_cache

    def get_customer_context(self, customer_id: str) -> Dict[str, Any]:
        """Get complete customer context for fraud investigation."""
        customer = next((c for c in self.get_customers() if c["customer_id"] == customer_id), {})

        customer_transactions = [t for t in self.get_transactions() if t["customer_id"] == customer_id]
        customer_kyc = [k for k in self.get_kyc_events() if k["customer_id"] == customer_id]
        customer_patterns = [p for p in self.get_fraud_memory() if p["entity_id"] == customer_id]

        return {
            "customer": customer,
            "transactions": customer_transactions,
            "kyc_events": customer_kyc,
            "fraud_patterns": customer_patterns,
            "risk_summary": self._calculate_customer_risk(customer_transactions, customer_kyc, customer_patterns)
        }

    def _calculate_customer_risk(self, transactions: List, kyc_events: List, patterns: List) -> Dict[str, Any]:
        """Calculate customer risk summary."""
        risk_score = 0.0

        # Transaction risk factors
        high_value_txns = [t for t in transactions if t["amount"] > 10000]
        risk_score += len(high_value_txns) * 0.2

        # KYC risk factors
        suspicious_kyc = [k for k in kyc_events if k.get("anomaly_type")]
        risk_score += len(suspicious_kyc) * 0.3

        # Pattern risk factors
        high_risk_patterns = [p for p in patterns if p["risk_score"] > 0.7]
        risk_score += len(high_risk_patterns) * 0.25

        risk_score = min(risk_score, 1.0)

        return {
            "overall_risk_score": risk_score,
            "risk_level": "HIGH" if risk_score > 0.7 else "MEDIUM" if risk_score > 0.4 else "LOW",
            "risk_factors": {
                "high_value_transactions": len(high_value_txns),
                "suspicious_kyc_events": len(suspicious_kyc),
                "high_risk_patterns": len(high_risk_patterns)
            }
        }

    def get_suspicious_countries(self) -> List[str]:
        """Get list of suspicious countries for demo."""
        sanctions_data = self.get_sanctions_data()
        country_risks = sanctions_data.get("country_risks", [])
        return [cr["country_code"] for cr in country_risks if cr["risk_level"] in ["CRITICAL", "HIGH"]]

    def refresh_cache(self):
        """Refresh all cached data."""
        self._customers_cache = None
        self._transactions_cache = None
        self._kyc_events_cache = None
        self._sanctions_data_cache = None
        self._fraud_memory_cache = None
        logger.info("Data cache refreshed")

    def get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded data."""
        return {
            "customers": len(self.get_customers()),
            "transactions": len(self.get_transactions()),
            "kyc_events": len(self.get_kyc_events()),
            "sanctions_entries": len(self.get_sanctions_data().get("sanctions_entries", [])),
            "fraud_patterns": len(self.get_fraud_memory()),
            "last_loaded": datetime.utcnow().isoformat()
        }


# Global data loader instance
data_loader = DataLoader()
