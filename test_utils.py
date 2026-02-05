"""
Shared Test Utilities for Sales Analytics API Testing
Common functions, fixtures, and test data generators
"""

import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

# Base URL for the API
BASE_URL = "http://127.0.0.1:5000/api"


def get_base_url() -> str:
    """Get API base URL"""
    return BASE_URL


def generate_test_data(num_transactions: int = 1000) -> List[Dict[str, Any]]:
    """Generate realistic test data for benchmarking and testing"""
    products = [
        ("PROD001", "Laptop", 1200.00),
        ("PROD002", "Mouse", 25.00),
        ("PROD003", "Keyboard", 75.00),
        ("PROD004", "Monitor", 350.00),
        ("PROD005", "Webcam", 150.00),
        ("PROD006", "Headset", 89.99),
        ("PROD007", "USB Cable", 12.99),
        ("PROD008", "External Drive", 129.99),
        ("PROD009", "Desk Lamp", 45.00),
        ("PROD010", "Phone Stand", 19.99)
    ]
    
    customers = [
        ("CUST001", "John Doe"),
        ("CUST002", "Jane Smith"),
        ("CUST003", "Bob Johnson"),
        ("CUST004", "Alice Williams"),
        ("CUST005", "Charlie Brown"),
        ("CUST006", "Diana Prince"),
        ("CUST007", "Ethan Hunt"),
        ("CUST008", "Fiona Apple"),
        ("CUST009", "George Miller"),
        ("CUST010", "Hannah Montana")
    ]
    
    transactions = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(num_transactions):
        product_id, product_name, price = random.choice(products)
        customer_id, customer_name = random.choice(customers)
        quantity = random.randint(1, 10)
        
        transactions.append({
            "transaction_id": f"TXN{i+1:05d}",
            "customer_id": customer_id,
            "customer_name": customer_name,
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
            "price_per_unit": price,
            "total_amount": price * quantity,
            "timestamp": (base_date + timedelta(hours=i)).isoformat(),
            "price": price
        })
    
    return transactions


def get_sample_transactions() -> List[Dict[str, Any]]:
    """Get predefined sample transaction data for testing"""
    return [
        {
            "transaction_id": "TXN001",
            "customer_id": "CUST001",
            "customer_name": "Alice",
            "product_id": "PROD001",
            "product_name": "Laptop",
            "quantity": 2,
            "price": 1000.00
        },
        {
            "transaction_id": "TXN002",
            "customer_id": "CUST001",
            "customer_name": "Alice",
            "product_id": "PROD002",
            "product_name": "Mouse",
            "quantity": 1,
            "price": 50.00
        },
        {
            "transaction_id": "TXN003",
            "customer_id": "CUST002",
            "customer_name": "Bob",
            "product_id": "PROD001",
            "product_name": "Laptop",
            "quantity": 1,
            "price": 1000.00
        }
    ]


def clear_database() -> Dict[str, Any]:
    """Clear all transactions from database"""
    response = requests.delete(f"{BASE_URL}/transactions")
    return response.json() if response.status_code == 200 else {}


def upload_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Upload transactions to API"""
    response = requests.post(f"{BASE_URL}/transactions", json=transactions)
    return response.json() if response.status_code in [200, 201] else {}


def check_server_health() -> bool:
    """Check if API server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False
