"""
Pytest Test Suite for Sales Analytics API
Tests all endpoints with edge cases, validation, and performance benchmarking
"""

import pytest
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from test_utils import (
    BASE_URL,
    get_base_url,
    generate_test_data,
    get_sample_transactions,
    clear_database,
    upload_transactions,
    check_server_health
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def clean_db():
    """Clear database before and after each test"""
    clear_database()
    yield
    clear_database()


@pytest.fixture
def sample_transactions():
    """Sample transaction data for testing"""
    return get_sample_transactions()


# ============================================================================
# TEST: Upload Transactions - Edge Cases
# ============================================================================

class TestUploadTransactions:
    """Test POST /api/transactions endpoint with edge cases"""
    
    def test_upload_single_transaction(self, clean_db):
        """Test uploading a single transaction"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "John",
            "product_id": "P001",
            "product_name": "Item",
            "quantity": 1,
            "price": 10.0
        }
        
        response = requests.post(f"{BASE_URL}/transactions", json=transaction)
        assert response.status_code == 201
        data = response.json()
        assert data['success'] == True
        assert data['total_transactions'] == 1
    
    def test_upload_multiple_transactions_as_array(self, clean_db, sample_transactions):
        """Test uploading array of transactions"""
        response = requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        assert response.status_code == 201
        data = response.json()
        assert data['success'] == True
        assert data['total_transactions'] == 3
    
    def test_upload_empty_array(self, clean_db):
        """Edge Case: Empty array"""
        response = requests.post(f"{BASE_URL}/transactions", json=[])
        assert response.status_code == 400
    
    def test_upload_missing_required_field(self, clean_db):
        """Edge Case: Missing required field"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001"
            # Missing customer_name, product_id, etc.
        }
        
        response = requests.post(f"{BASE_URL}/transactions", json=transaction)
        assert response.status_code == 400
    
    def test_upload_zero_quantity(self, clean_db):
        """Edge Case: Zero quantity (invalid)"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "John",
            "product_id": "P001",
            "product_name": "Item",
            "quantity": 0,  # Invalid
            "price": 10.0
        }
        
        response = requests.post(f"{BASE_URL}/transactions", json=transaction)
        assert response.status_code == 400
    
    def test_upload_negative_quantity(self, clean_db):
        """Edge Case: Negative quantity (invalid)"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "John",
            "product_id": "P001",
            "product_name": "Item",
            "quantity": -5,  # Invalid
            "price": 10.0
        }
        
        response = requests.post(f"{BASE_URL}/transactions", json=transaction)
        assert response.status_code == 400
    
    def test_upload_negative_price(self, clean_db):
        """Edge Case: Negative price (invalid)"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "John",
            "product_id": "P001",
            "product_name": "Item",
            "quantity": 1,
            "price": -10.0  # Invalid
        }
        
        response = requests.post(f"{BASE_URL}/transactions", json=transaction)
        assert response.status_code == 400
    
    def test_upload_large_quantity(self, clean_db):
        """Edge Case: Very large quantity"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "John",
            "product_id": "P001",
            "product_name": "Item",
            "quantity": 1000000,
            "price": 10.0
        }
        
        response = requests.post(f"{BASE_URL}/transactions", json=transaction)
        assert response.status_code == 201
    
    def test_upload_decimal_quantity(self, clean_db):
        """Edge Case: Decimal quantity (should be accepted)"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "John",
            "product_id": "P001",
            "product_name": "Item",
            "quantity": 2.5,  # Decimal quantity
            "price": 10.0
        }
        
        response = requests.post(f"{BASE_URL}/transactions", json=transaction)
        assert response.status_code == 201


# ============================================================================
# TEST: Sales By Product - Edge Cases
# ============================================================================

class TestSalesByProduct:
    """Test GET /api/sales/by-product endpoint with edge cases"""
    
    def test_sales_empty_database(self, clean_database):
        """Edge Case: No transactions in database"""
        response = requests.get(f"{BASE_URL}/sales/by-product")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert data['data'] == []
    
    def test_sales_single_product(self, clean_database):
        """Edge Case: Only one product"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "John",
            "product_id": "P001",
            "product_name": "Laptop",
            "quantity": 2,
            "price": 1000.0
        }
        requests.post(f"{BASE_URL}/transactions", json=transaction)
        
        response = requests.get(f"{BASE_URL}/sales/by-product")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['data'][0]['total_sales'] == 2000.0
    
    def test_sales_sort_by_sales_desc(self, clean_database, sample_transactions):
        """Test sorting by sales descending"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/sales/by-product?sort_by=sales&order=desc")
        assert response.status_code == 200
        data = response.json()
        
        # Should be sorted descending
        assert data['data'][0]['total_sales'] >= data['data'][1]['total_sales']
    
    def test_sales_sort_by_quantity(self, clean_database, sample_transactions):
        """Test sorting by quantity"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/sales/by-product?sort_by=quantity&order=desc")
        assert response.status_code == 200
    
    def test_sales_with_limit(self, clean_database, sample_transactions):
        """Test limit parameter"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/sales/by-product?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
    
    def test_sales_same_product_multiple_transactions(self, clean_database):
        """Edge Case: Multiple transactions for same product"""
        transactions = [
            {"transaction_id": "T1", "customer_id": "C1", "customer_name": "A",
             "product_id": "P1", "product_name": "Item", "quantity": 1, "price": 10.0},
            {"transaction_id": "T2", "customer_id": "C2", "customer_name": "B",
             "product_id": "P1", "product_name": "Item", "quantity": 2, "price": 10.0},
            {"transaction_id": "T3", "customer_id": "C3", "customer_name": "C",
             "product_id": "P1", "product_name": "Item", "quantity": 3, "price": 10.0}
        ]
        requests.post(f"{BASE_URL}/transactions", json=transactions)
        
        response = requests.get(f"{BASE_URL}/sales/by-product")
        data = response.json()
        
        assert data['count'] == 1
        assert data['data'][0]['total_quantity'] == 6
        assert data['data'][0]['total_sales'] == 60.0
        assert data['data'][0]['transaction_count'] == 3


# ============================================================================
# TEST: Top Customers - Edge Cases
# ============================================================================

class TestTopCustomers:
    """Test GET /api/customers/top endpoint with edge cases"""
    
    def test_customers_empty_database(self, clean_database):
        """Edge Case: No customers"""
        response = requests.get(f"{BASE_URL}/customers/top")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert data['data'] == []
    
    def test_customers_single_customer(self, clean_database):
        """Edge Case: Only one customer"""
        transaction = {
            "transaction_id": "T001",
            "customer_id": "C001",
            "customer_name": "Alice",
            "product_id": "P001",
            "product_name": "Laptop",
            "quantity": 1,
            "price": 1000.0
        }
        requests.post(f"{BASE_URL}/transactions", json=transaction)
        
        response = requests.get(f"{BASE_URL}/customers/top")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['data'][0]['total_spent'] == 1000.0
    
    def test_customers_with_limit(self, clean_database, sample_transactions):
        """Test limit parameter"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/customers/top?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
    
    def test_customers_min_spent_filter(self, clean_database, sample_transactions):
        """Test minimum spending filter"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/customers/top?min_spent=2000")
        assert response.status_code == 200
        data = response.json()
        
        # Only Alice spent >= 2000
        assert data['count'] == 1
        assert data['data'][0]['customer_name'] == "Alice"
    
    def test_customers_min_spent_zero(self, clean_database, sample_transactions):
        """Edge Case: min_spent = 0 (all customers)"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/customers/top?min_spent=0")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2  # Both customers
    
    def test_customers_unique_products_count(self, clean_database, sample_transactions):
        """Test unique products count calculation"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/customers/top")
        data = response.json()
        
        alice = next(c for c in data['data'] if c['customer_name'] == 'Alice')
        assert alice['unique_products_count'] == 2  # Laptop and Mouse
    
    def test_customers_average_transaction(self, clean_database):
        """Test average transaction calculation"""
        transactions = [
            {"transaction_id": "T1", "customer_id": "C1", "customer_name": "Alice",
             "product_id": "P1", "product_name": "Item1", "quantity": 1, "price": 100.0},
            {"transaction_id": "T2", "customer_id": "C1", "customer_name": "Alice",
             "product_id": "P2", "product_name": "Item2", "quantity": 1, "price": 200.0}
        ]
        requests.post(f"{BASE_URL}/transactions", json=transactions)
        
        response = requests.get(f"{BASE_URL}/customers/top")
        data = response.json()
        
        assert data['data'][0]['total_spent'] == 300.0
        assert data['data'][0]['average_transaction'] == 150.0


# ============================================================================
# TEST: Filter Transactions - Edge Cases
# ============================================================================

class TestFilterTransactions:
    """Test GET /api/transactions/filter endpoint with edge cases"""
    
    def test_filter_empty_database(self, clean_database):
        """Edge Case: Filter on empty database"""
        response = requests.get(f"{BASE_URL}/transactions/filter?customer_id=C001")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
    
    def test_filter_by_customer_no_match(self, clean_database, sample_transactions):
        """Edge Case: Filter with no matching results"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/transactions/filter?customer_id=NONEXISTENT")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
    
    def test_filter_by_customer(self, clean_database, sample_transactions):
        """Test filtering by customer"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/transactions/filter?customer_id=CUST001")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2  # Alice has 2 transactions
    
    def test_filter_by_product(self, clean_database, sample_transactions):
        """Test filtering by product"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/transactions/filter?product_id=PROD001")
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2  # Laptop appears twice
    
    def test_filter_by_min_amount(self, clean_database, sample_transactions):
        """Test filtering by minimum amount"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/transactions/filter?min_amount=100")
        assert response.status_code == 200
        data = response.json()
        assert all(t['total_amount'] >= 100 for t in data['data'])
    
    def test_filter_by_max_amount(self, clean_database, sample_transactions):
        """Test filtering by maximum amount"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/transactions/filter?max_amount=100")
        assert response.status_code == 200
        data = response.json()
        assert all(t['total_amount'] <= 100 for t in data['data'])
    
    def test_filter_by_amount_range(self, clean_database, sample_transactions):
        """Test filtering by amount range"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/transactions/filter?min_amount=50&max_amount=1500")
        assert response.status_code == 200
        data = response.json()
        assert all(50 <= t['total_amount'] <= 1500 for t in data['data'])
    
    def test_filter_combined_filters(self, clean_database, sample_transactions):
        """Edge Case: Multiple filters combined"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(
            f"{BASE_URL}/transactions/filter?customer_id=CUST001&min_amount=100"
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should match Alice's transactions with amount >= 100
        assert all(t['customer_id'] == 'CUST001' for t in data['data'])
        assert all(t['total_amount'] >= 100 for t in data['data'])
    
    def test_filter_total_amount_calculation(self, clean_database, sample_transactions):
        """Test that total_amount is calculated correctly in filter"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.get(f"{BASE_URL}/transactions/filter?customer_id=CUST001")
        data = response.json()
        
        assert data['total_amount'] == 2050.0  # 2000 + 50


# ============================================================================
# TEST: Utility Endpoints - Edge Cases
# ============================================================================

class TestUtilityEndpoints:
    """Test utility endpoints with edge cases"""
    
    def test_get_all_empty(self, clean_database):
        """Edge Case: Get all from empty database"""
        response = requests.get(f"{BASE_URL}/transactions")
        assert response.status_code == 200
        data = response.json()
        assert data['total_count'] == 0
        assert data['data'] == []
    
    def test_get_all_with_pagination(self, clean_database):
        """Test pagination"""
        transactions = [
            {"transaction_id": f"T{i}", "customer_id": "C1", "customer_name": "A",
             "product_id": "P1", "product_name": "Item", "quantity": 1, "price": 10.0}
            for i in range(10)
        ]
        requests.post(f"{BASE_URL}/transactions", json=transactions)
        
        response = requests.get(f"{BASE_URL}/transactions?limit=5&offset=0")
        data = response.json()
        assert data['count'] == 5
        assert data['total_count'] == 10
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'healthy'
    
    def test_clear_transactions(self, clean_database, sample_transactions):
        """Test clearing all transactions"""
        requests.post(f"{BASE_URL}/transactions", json=sample_transactions)
        
        response = requests.delete(f"{BASE_URL}/transactions")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        
        # Verify database is empty
        check = requests.get(f"{BASE_URL}/transactions")
        assert check.json()['total_count'] == 0


# ============================================================================
# TEST: Performance & Stress Tests
# ============================================================================

class TestPerformance:
    """Performance and stress testing"""
    
    def test_large_batch_upload(self, clean_database):
        """Stress Test: Upload 1000 transactions"""
        transactions = [
            {
                "transaction_id": f"T{i:05d}",
                "customer_id": f"C{i % 10}",
                "customer_name": f"Customer{i % 10}",
                "product_id": f"P{i % 20}",
                "product_name": f"Product{i % 20}",
                "quantity": 1,
                "price": 100.0
            }
            for i in range(1000)
        ]
        
        response = requests.post(f"{BASE_URL}/transactions", json=transactions)
        assert response.status_code == 201
        assert response.json()['total_transactions'] == 1000
    
    def test_aggregation_performance(self, clean_database):
        """Performance Test: Aggregation on 1000 transactions"""
        transactions = [
            {
                "transaction_id": f"T{i:05d}",
                "customer_id": f"C{i % 10}",
                "customer_name": f"Customer{i % 10}",
                "product_id": f"P{i % 20}",
                "product_name": f"Product{i % 20}",
                "quantity": 1,
                "price": 100.0
            }
            for i in range(1000)
        ]
        requests.post(f"{BASE_URL}/transactions", json=transactions)
        
        response = requests.get(f"{BASE_URL}/sales/by-product")
        assert response.status_code == 200
        assert response.elapsed.total_seconds() < 1.0  # Should be fast


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
