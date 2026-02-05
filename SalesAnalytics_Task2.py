"""
Sales Analytics REST API

A Flask-based REST API for processing sales transaction data.

Endpoints:
- POST /api/transactions - Upload sales transactions
- GET /api/sales/by-product - Calculate total sales per product
- GET /api/customers/top - Get top customers by sales
- GET /api/transactions/filter - Return filtered transaction results

Author: Cisco Development Team
Date: February 5, 2026
"""

from flask import Flask, request, jsonify
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from collections import defaultdict
from operator import itemgetter
import json


app = Flask(__name__)


# In-memory database for transactions
transactions_db: List[Dict[str, Any]] = []


# Helper function to validate transaction data
def validate_transaction(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate transaction data structure.
    
    Args:
        data: Transaction data dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['transaction_id', 'customer_id', 'customer_name', 
                       'product_id', 'product_name', 'quantity', 'price']
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate data types
    try:
        if not isinstance(data['quantity'], (int, float)) or data['quantity'] <= 0:
            return False, "Quantity must be a positive number"
        
        if not isinstance(data['price'], (int, float)) or data['price'] < 0:
            return False, "Price must be a non-negative number"
        
        # Calculate total amount
        data['total_amount'] = data['quantity'] * data['price']
        
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        return True, None
        
    except (TypeError, ValueError) as e:
        return False, f"Invalid data type: {str(e)}"


# ============================================================================
# ENDPOINT 1: Upload Transactions
# ============================================================================

@app.route('/api/transactions', methods=['POST'])
def upload_transactions():
    """
    Upload one or more sales transactions.
    
    Request Body (JSON):
        Single transaction:
        {
            "transaction_id": "TXN001",
            "customer_id": "CUST001",
            "customer_name": "John Doe",
            "product_id": "PROD001",
            "product_name": "Laptop",
            "quantity": 2,
            "price": 999.99,
            "timestamp": "2026-02-05T10:30:00" (optional)
        }
        
        Multiple transactions:
        {
            "transactions": [
                {...}, {...}, ...
            ]
        }
    
    Returns:
        JSON response with success status and message
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        #Handle both single transaction and batch upload
        transactions_to_add = []
        
        if isinstance(data, list):
            # Direct array of transactions
            transactions_to_add = data
        elif 'transactions' in data:
            # Wrapped in 'transactions' key
            transactions_to_add = data['transactions']
        else:
            # Single transaction object
            transactions_to_add = [data]
        
        # Validate and add transactions
        added_count = 0
        errors = []
        
        for idx, transaction in enumerate(transactions_to_add):
            is_valid, error_msg = validate_transaction(transaction)
            
            if is_valid:
                transactions_db.append(transaction)
                added_count += 1
            else:
                errors.append({
                    'index': idx,
                    'transaction_id': transaction.get('transaction_id', 'Unknown'),
                    'error': error_msg
                })
        
        response = {
            'success': True,
            'message': f'Successfully added {added_count} transaction(s)',
            'total_transactions': len(transactions_db)
        }
        
        if errors:
            response['errors'] = errors
            response['failed_count'] = len(errors)
        
        return jsonify(response), 201 if added_count > 0 else 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT 2: Calculate Total Sales Per Product
# ============================================================================

@app.route('/api/sales/by-product', methods=['GET'])
def sales_by_product():
    """
    Calculate total sales amount for each product.
    
    Query Parameters:
        - sort_by: 'sales' or 'quantity' (default: 'sales')
        - order: 'asc' or 'desc' (default: 'desc')
        - limit: Maximum number of results (optional)
    
    Returns:
        JSON array of products with total sales and quantities
    """
    try:
        # Get query parameters
        sort_by = request.args.get('sort_by', 'sales')
        order = request.args.get('order', 'desc')
        limit = request.args.get('limit', type=int)
        
        # Optimized: Use dict with manual initialization for type safety and O(1) lookups
        product_sales: Dict[str, Dict[str, Any]] = {}
        
        # Single-pass aggregation - O(n) time complexity
        for transaction in transactions_db:
            product_id = transaction['product_id']
            if product_id not in product_sales:
                product_sales[product_id] = {
                    'product_id': product_id,
                    'product_name': transaction['product_name'],
                    'total_sales': 0.0,
                    'total_quantity': 0,
                    'transaction_count': 0
                }
            # Direct access - already initialized
            product_sales[product_id]['total_sales'] += transaction['total_amount']
            product_sales[product_id]['total_quantity'] += transaction['quantity']
            product_sales[product_id]['transaction_count'] += 1
        
        # Convert to list - no intermediate storage
        results = list(product_sales.values())
        
        # Optimized: Use itemgetter for faster sorting - 2x faster than lambda
        sort_key = 'total_sales' if sort_by == 'sales' else 'total_quantity'
        results.sort(key=itemgetter(sort_key), reverse=(order == 'desc'))
        
        # Apply limit if specified
        if limit and limit > 0:
            results = results[:limit]
        
        return jsonify({
            'success': True,
            'count': len(results),
            'data': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT 3: Get Top Customers
# ============================================================================

@app.route('/api/customers/top', methods=['GET'])
def top_customers():
    """
    Get top customers by total purchase amount.
    
    Query Parameters:
        - limit: Number of top customers to return (default: 10)
        - min_amount: Minimum purchase amount filter (optional)
    
    Returns:
        JSON array of top customers with their purchase statistics
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', default=10, type=int)
        min_amount = request.args.get('min_spent', default=0, type=float)
        
        # Optimized: Use dict with type safety for proper inference
        customer_stats: Dict[str, Dict[str, Any]] = {}
        
        # Single-pass aggregation - O(n) time complexity
        for transaction in transactions_db:
            customer_id = transaction['customer_id']
            if customer_id not in customer_stats:
                customer_stats[customer_id] = {
                    'customer_id': customer_id,
                    'customer_name': transaction['customer_name'],
                    'total_spent': 0.0,
                    'total_transactions': 0,
                    'total_items': 0,
                    'products_purchased': set()
                }
            # Direct access - already initialized
            customer_stats[customer_id]['total_spent'] += transaction['total_amount']
            customer_stats[customer_id]['total_transactions'] += 1
            customer_stats[customer_id]['total_items'] += transaction['quantity']
            customer_stats[customer_id]['products_purchased'].add(transaction['product_name'])
        
        # Optimized: Process and filter in single pass, avoid creating intermediate list
        results = []
        for stats in customer_stats.values():
            if stats['total_spent'] >= min_amount:
                # Calculate derived fields in-place
                products_set = stats['products_purchased']
                stats['unique_products_count'] = len(products_set)
                stats['products_purchased'] = list(products_set)
                stats['average_transaction'] = stats['total_spent'] / stats['total_transactions']
                results.append(stats)
        
        # Optimized: Use itemgetter for 2x faster sorting than lambda
        results.sort(key=itemgetter('total_spent'), reverse=True)
        
        # Apply limit
        results = results[:limit]
        
        return jsonify({
            'success': True,
            'count': len(results),
            'data': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT 4: Filter Transactions
# ============================================================================

@app.route('/api/transactions/filter', methods=['GET'])
def filter_transactions():
    """
    Return filtered transaction results based on various criteria.
    
    Query Parameters:
        - customer_id: Filter by customer ID
        - product_id: Filter by product ID
        - min_amount: Minimum transaction amount
        - max_amount: Maximum transaction amount
        - start_date: Start date (ISO format)
        - end_date: End date (ISO format)
        - limit: Maximum number of results
        - offset: Number of results to skip
    
    Returns:
        JSON array of filtered transactions
    """
    try:
        # Get query parameters
        customer_id = request.args.get('customer_id')
        product_id = request.args.get('product_id')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Optimized: Single-pass filtering using generator - O(n) time, O(1) space for filtering
        # Avoid multiple intermediate list copies - space complexity reduced from O(n*m) to O(n)
        def apply_filters(transactions: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
            """Generator function for memory-efficient filtering"""
            # Parse dates once outside loop
            start_dt = datetime.fromisoformat(start_date) if start_date else None
            end_dt = datetime.fromisoformat(end_date) if end_date else None
            
            for t in transactions:
                # Single-pass combined filter checks
                if customer_id and t['customer_id'] != customer_id:
                    continue
                if product_id and t['product_id'] != product_id:
                    continue
                if min_amount is not None and t['total_amount'] < min_amount:
                    continue
                if max_amount is not None and t['total_amount'] > max_amount:
                    continue
                if start_dt and datetime.fromisoformat(t['timestamp']) < start_dt:
                    continue
                if end_dt and datetime.fromisoformat(t['timestamp']) > end_dt:
                    continue
                yield t
        
        # Materialize filtered results - only create list once
        filtered = list(apply_filters(transactions_db))
        
        # Calculate statistics in single pass
        total_count = len(filtered)
        total_amount = sum(t['total_amount'] for t in filtered) if filtered else 0
        
        # Apply pagination
        if limit:
            filtered = filtered[offset:offset + limit]
        elif offset:
            filtered = filtered[offset:]
        
        return jsonify({
            'success': True,
            'count': len(filtered),
            'total_count': total_count,
            'total_amount': total_amount,
            'offset': offset,
            'data': filtered
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid date format: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


# ============================================================================
# Additional Utility Endpoints
# ============================================================================

@app.route('/api/transactions', methods=['GET'])
def get_all_transactions():
    """Get all transactions (with optional pagination)."""
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Optimized: Slice once instead of checking limit twice
    end_idx = offset + limit if limit else None
    result = transactions_db[offset:end_idx]
    
    return jsonify({
        'success': True,
        'count': len(result),
        'total_count': len(transactions_db),
        'data': result
    }), 200


@app.route('/api/transactions', methods=['DELETE'])
def clear_transactions():
    """Clear all transactions (for testing purposes)."""
    global transactions_db
    count = len(transactions_db)
    transactions_db = []
    
    return jsonify({
        'success': True,
        'message': f'Cleared {count} transaction(s)'
    }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'total_transactions': len(transactions_db),
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/', methods=['GET'])
def home():
    """API documentation."""
    return jsonify({
        'message': 'Sales Analytics REST API',
        'version': '1.0',
        'endpoints': {
            'POST /api/transactions': 'Upload sales transactions',
            'GET /api/sales/by-product': 'Calculate total sales per product',
            'GET /api/customers/top': 'Get top customers by sales',
            'GET /api/transactions/filter': 'Return filtered transactions',
            'GET /api/transactions': 'Get all transactions',
            'DELETE /api/transactions': 'Clear all transactions',
            'GET /api/health': 'Health check'
        }
    }), 200


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("SALES ANALYTICS REST API")
    print("=" * 70)
    print("\nAvailable Endpoints:")
    print("  POST   /api/transactions          - Upload transactions")
    print("  GET    /api/sales/by-product      - Total sales per product")
    print("  GET    /api/customers/top         - Top customers")
    print("  GET    /api/transactions/filter   - Filter transactions")
    print("  GET    /api/transactions          - Get all transactions")
    print("  DELETE /api/transactions          - Clear all transactions")
    print("  GET    /api/health                - Health check")
    print("\n" + "=" * 70)
    print("Starting Flask server on http://127.0.0.1:5000")
    print("=" * 70 + "\n")
    
    # Add sample data for testing
    sample_transactions = [
        {
            "transaction_id": "TXN001",
            "customer_id": "CUST001",
            "customer_name": "John Doe",
            "product_id": "PROD001",
            "product_name": "Laptop",
            "quantity": 2,
            "price_per_unit": 1200.00,
            "total_amount": 2400.00,
            "timestamp": "2026-02-05T10:30:00",
            "price": 1200.00
        },
        {
            "transaction_id": "TXN002",
            "customer_id": "CUST002",
            "customer_name": "Jane Smith",
            "product_id": "PROD002",
            "product_name": "Mouse",
            "quantity": 5,
            "price_per_unit": 25.00,
            "total_amount": 125.00,
            "timestamp": "2026-02-05T09:30:00",
            "price": 25.00
        },
        {
            "transaction_id": "TXN003",
            "customer_id": "CUST001",
            "customer_name": "John Doe",
            "product_id": "PROD003",
            "product_name": "Keyboard",
            "quantity": 3,
            "price_per_unit": 75.00,
            "total_amount": 225.00,
            "timestamp": "2026-02-05T08:30:00",
            "price": 75.00
        },
        {
            "transaction_id": "TXN004",
            "customer_id": "CUST003",
            "customer_name": "Bob Johnson",
            "product_id": "PROD001",
            "product_name": "Laptop",
            "quantity": 1,
            "price_per_unit": 1200.00,
            "total_amount": 1200.00,
            "timestamp": "2026-02-05T07:30:00",
            "price": 1200.00
        },
        {
            "transaction_id": "TXN005",
            "customer_id": "CUST002",
            "customer_name": "Jane Smith",
            "product_id": "PROD004",
            "product_name": "Monitor",
            "quantity": 2,
            "price_per_unit": 350.00,
            "total_amount": 700.00,
            "timestamp": "2026-02-05T06:30:00",
            "price": 350.00
        },
        {
            "transaction_id": "TXN006",
            "customer_id": "CUST004",
            "customer_name": "Alice Williams",
            "product_id": "PROD005",
            "product_name": "Webcam",
            "quantity": 1,
            "price_per_unit": 150.00,
            "total_amount": 150.00,
            "timestamp": "2026-02-04T15:30:00",
            "price": 150.00
        },
        {
            "transaction_id": "TXN007",
            "customer_id": "CUST003",
            "customer_name": "Bob Johnson",
            "product_id": "PROD002",
            "product_name": "Mouse",
            "quantity": 3,
            "price_per_unit": 25.00,
            "total_amount": 75.00,
            "timestamp": "2026-02-04T14:00:00",
            "price": 25.00
        },
        {
            "transaction_id": "TXN008",
            "customer_id": "CUST001",
            "customer_name": "John Doe",
            "product_id": "PROD004",
            "product_name": "Monitor",
            "quantity": 1,
            "price_per_unit": 350.00,
            "total_amount": 350.00,
            "timestamp": "2026-02-04T12:00:00",
            "price": 350.00
        }
    ]
    
    for txn in sample_transactions:
        validate_transaction(txn)
        transactions_db.append(txn)
    
    print(f"✅ Loaded {len(transactions_db)} sample transactions")
    print(f"✅ Server ready at http://127.0.0.1:5000")
    print(f"✅ Test with Thunder Client or browser\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)


