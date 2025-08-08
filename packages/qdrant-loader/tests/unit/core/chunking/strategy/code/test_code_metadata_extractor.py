"""Comprehensive tests for Code Metadata Extractor to achieve 80%+ coverage."""

from unittest.mock import Mock


from qdrant_loader.core.chunking.strategy.code.code_metadata_extractor import CodeMetadataExtractor
from qdrant_loader.core.document import Document


class TestCodeMetadataExtractor:
    """Comprehensive tests for CodeMetadataExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock settings
        self.mock_settings = Mock()
        self.mock_global_config = Mock()
        self.mock_chunking = Mock()
        self.mock_strategies = Mock()
        self.mock_code_config = Mock()
        
        self.mock_strategies.code = self.mock_code_config
        self.mock_chunking.strategies = self.mock_strategies
        self.mock_global_config.chunking = self.mock_chunking
        self.mock_settings.global_config = self.mock_global_config
        
        self.extractor = CodeMetadataExtractor(self.mock_settings)

    def test_initialization(self):
        """Test CodeMetadataExtractor initialization."""
        assert self.extractor.settings is self.mock_settings
        assert self.extractor.logger is not None
        assert self.extractor.code_config is self.mock_code_config

    def test_initialization_no_code_config(self):
        """Test initialization when code config is not available."""
        self.mock_strategies.code = None
        extractor = CodeMetadataExtractor(self.mock_settings)
        assert extractor.code_config is None

    def test_extract_hierarchical_metadata_python(self):
        """Test hierarchical metadata extraction for Python code."""
        python_code = '''
def calculate_factorial(n):
    """Calculate factorial of a number.
    
    Args:
        n: Integer number
        
    Returns:
        Factorial of n
    """
    if n < 0:
        raise ValueError("Negative numbers not allowed")
    elif n == 0 or n == 1:
        return 1
    else:
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

class MathUtilities:
    """Utility class for mathematical operations."""
    
    PI = 3.14159
    
    @staticmethod
    def square(x):
        """Square a number."""
        return x * x
    
    def test_factorial(self):
        assert calculate_factorial(5) == 120
'''
        
        chunk_metadata = {"language": "python", "file_type": ".py"}
        document = Mock(spec=Document)
        
        metadata = self.extractor.extract_hierarchical_metadata(
            python_code, chunk_metadata, document
        )
        
        # Check basic metadata structure
        assert "dependency_graph" in metadata
        assert "complexity_metrics" in metadata
        assert "code_patterns" in metadata
        assert "documentation_coverage" in metadata
        assert "test_indicators" in metadata
        assert "security_indicators" in metadata
        assert "performance_indicators" in metadata
        assert "maintainability_metrics" in metadata
        assert metadata["content_type"] == "code"
        
        # Check documentation coverage
        doc_coverage = metadata["documentation_coverage"]
        assert doc_coverage["total_functions"] >= 2  # calculate_factorial, square
        assert doc_coverage["total_classes"] == 1   # MathUtilities
        assert doc_coverage["documentation_coverage_percent"] > 0
        assert doc_coverage["has_module_docstring"] is False
        
        # Check test indicators
        test_indicators = metadata["test_indicators"]
        assert test_indicators["is_test_file"] is True  # has test_factorial
        assert test_indicators["test_count"] >= 1
        assert test_indicators["assertion_count"] >= 1

    def test_extract_hierarchical_metadata_javascript(self):
        """Test hierarchical metadata extraction for JavaScript code."""
        js_code = '''
/**
 * User management utilities
 */

const API_KEY = "secret-key-123";

class UserManager {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
        this.users = [];
    }
    
    async fetchUsers() {
        const response = await fetch(this.apiUrl + "/users");
        return response.json();
    }
    
    validateEmail(email) {
        const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
        return emailRegex.test(email);
    }
}

function calculateTotal(items) {
    let total = 0;
    for (const item of items) {
        if (item.price > 0) {
            total += item.price;
        }
    }
    return total;
}

// Test function
function testCalculateTotal() {
    const items = [{price: 10}, {price: 20}];
    console.assert(calculateTotal(items) === 30);
}
'''
        
        chunk_metadata = {"language": "javascript", "file_type": ".js"}
        document = Mock(spec=Document)
        
        metadata = self.extractor.extract_hierarchical_metadata(
            js_code, chunk_metadata, document
        )
        
        # Check security indicators
        security = metadata["security_indicators"]
        assert "credentials" in security["sensitive_data_handling"]  # API_KEY
        
        # Check performance indicators
        performance = metadata["performance_indicators"]
        assert len(performance["optimization_patterns"]) >= 0
        
        # Check code patterns
        patterns = metadata["code_patterns"]
        assert isinstance(patterns["design_patterns"], list)
        assert isinstance(patterns["best_practices"], list)

    def test_extract_entities_python(self):
        """Test entity extraction from Python code."""
        python_code = '''
class DatabaseManager:
    """Manages database connections."""
    
    MAX_CONNECTIONS = 100
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, host):
        self.host = host
    
    def connect(self):
        """Establish database connection."""
        pass
    
    def disconnect(self):
        """Close database connection."""
        pass

def calculate_average(numbers):
    """Calculate average of numbers."""
    return sum(numbers) / len(numbers)

GLOBAL_CONFIG = {"debug": True}
'''
        
        entities = self.extractor.extract_entities(python_code)
        
        # Should find class names
        assert "DatabaseManager" in entities
        
        # Should find function names
        assert "connect" in entities or "disconnect" in entities or "calculate_average" in entities
        
        # Should find constants
        assert "MAX_CONNECTIONS" in entities
        assert "DEFAULT_TIMEOUT" in entities
        assert "GLOBAL_CONFIG" in entities

    def test_extract_entities_java(self):
        """Test entity extraction from Java code."""
        java_code = '''
public class UserService {
    private static final String API_VERSION = "v1.0";
    private final Logger logger;
    
    public UserService(Logger logger) {
        this.logger = logger;
    }
    
    public User findUserById(Long id) {
        logger.info("Finding user with id: " + id);
        return userRepository.findById(id);
    }
    
    private boolean validateUser(User user) {
        return user != null && user.getEmail() != null;
    }
}

interface UserRepository {
    User findById(Long id);
}
'''
        
        entities = self.extractor.extract_entities(java_code)
        
        # Should find class and interface names
        assert "UserService" in entities
        assert "UserRepository" in entities
        
        # Should find constants
        assert "API_VERSION" in entities

    def test_build_dependency_graph(self):
        """Test dependency graph building."""
        code = '''
import os
import sys
from pathlib import Path
from typing import Optional, List

import requests
import numpy as np
from flask import Flask, request

app = Flask(__name__)
'''
        
        dependencies = self.extractor._build_dependency_graph(code)
        
        assert "stdlib_imports" in dependencies
        assert "third_party_imports" in dependencies
        
        # Check standard library imports
        assert "os" in dependencies["stdlib_imports"]
        assert "sys" in dependencies["stdlib_imports"]
        
        # Check third-party imports
        assert "requests" in dependencies["third_party_imports"]
        assert "numpy" in dependencies["third_party_imports"]
        assert "flask" in dependencies["third_party_imports"]

    def test_calculate_complexity_metrics(self):
        """Test complexity metrics calculation."""
        simple_code = '''
def simple_function():
    return "hello"
'''
        
        complex_code = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    if i % 2 == 0:
                        while i > 0:
                            i -= 1
                            if i == 5:
                                break
                    else:
                        continue
            else:
                return None
        else:
            return False
    else:
        return True
'''
        
        simple_metrics = self.extractor._calculate_complexity_metrics(simple_code)
        complex_metrics = self.extractor._calculate_complexity_metrics(complex_code)
        
        # Simple code should have low complexity
        assert simple_metrics["cyclomatic_complexity"] == 1
        assert simple_metrics["lines_of_code"] < 5
        
        # Complex code should have higher complexity
        assert complex_metrics["cyclomatic_complexity"] > 5
        assert complex_metrics["lines_of_code"] > 10
        assert complex_metrics["nesting_depth"] > 3

    def test_calculate_maintainability_index(self):
        """Test maintainability index calculation."""
        # Test with valid code
        code = '''
def test_function():
    x = 1 + 2
    y = x * 3
    return y
'''
        
        mi = self.extractor._calculate_maintainability_index(code)
        assert 0 <= mi <= 100
        
        # Test with empty code
        empty_mi = self.extractor._calculate_maintainability_index("")
        assert empty_mi == 50

    def test_identify_code_patterns(self):
        """Test code pattern identification."""
        pattern_code = '''
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

class UserFactory:
    @staticmethod
    def create_user(user_type):
        if user_type == "admin":
            return AdminUser()
        return RegularUser()

class EventManager:
    def __init__(self):
        self.observers = []
    
    def notify(self, event):
        for observer in self.observers:
            observer.update(event)

def long_function():
    # This function has too many lines
    line1 = 1
    # ... imagine 100+ lines here
    global global_var
    global_var = "bad practice"
    
    if condition1:
        if condition2:
            if condition3:
                if condition4:
                    if condition5:
                        pass

def test_something():
    \"\"\"Test function with docstring\"\"\"
    assert True
'''
        
        patterns = self.extractor._identify_code_patterns(pattern_code)
        
        # Should identify design patterns
        assert "singleton" in patterns["design_patterns"]
        assert "factory" in patterns["design_patterns"]
        assert "observer" in patterns["design_patterns"]
        
        # Should identify anti-patterns
        assert "global_variables" in patterns["anti_patterns"]
        
        # Should identify code smells
        assert "too_many_conditionals" in patterns["code_smells"]
        
        # Should identify best practices
        assert "documentation" in patterns["best_practices"]
        assert "testing" in patterns["best_practices"]

    def test_calculate_doc_coverage(self):
        """Test documentation coverage calculation."""
        documented_code = '''
"""Module docstring."""

class WellDocumented:
    """Class with docstring."""
    
    def method1(self):
        """Method with docstring."""
        pass
    
    def method2(self):
        """Another documented method."""
        pass

def function1():
    """Documented function."""
    pass

def function2():
    # Only comment, no docstring
    pass
'''
        
        coverage = self.extractor._calculate_doc_coverage(documented_code)
        
        assert coverage["total_functions"] == 4  # 2 methods + 2 functions
        assert coverage["total_classes"] == 1
        assert coverage["documented_elements"] >= 3  # At least 3 docstrings
        assert coverage["has_module_docstring"] is True
        assert coverage["documentation_coverage_percent"] > 50

    def test_identify_test_code_pytest(self):
        """Test identification of pytest test code."""
        pytest_code = '''
import pytest
from unittest.mock import Mock, patch

class TestUserService:
    @pytest.fixture
    def user_service(self):
        return UserService()
    
    def test_create_user(self, user_service):
        """Test user creation."""
        user = user_service.create_user("john@example.com")
        assert user.email == "john@example.com"
    
    def test_user_validation(self):
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            result = validate_user("test@test.com")
            assert result is True
    
    def test_error_handling(self):
        with pytest.raises(ValueError):
            create_user("")
'''
        
        test_indicators = self.extractor._identify_test_code(pytest_code)
        
        assert test_indicators["is_test_file"] is True
        assert test_indicators["test_framework"] == "pytest"
        assert test_indicators["test_count"] >= 3
        assert test_indicators["assertion_count"] >= 3
        assert test_indicators["mock_usage"] is True
        assert test_indicators["fixture_usage"] is True

    def test_identify_test_code_unittest(self):
        """Test identification of unittest test code."""
        unittest_code = '''
import unittest
from unittest.mock import Mock

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = Calculator()
    
    def tearDown(self):
        self.calculator = None
    
    def test_addition(self):
        result = self.calculator.add(2, 3)
        self.assertEqual(result, 5)
    
    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            self.calculator.divide(10, 0)

if __name__ == '__main__':
    unittest.main()
'''
        
        test_indicators = self.extractor._identify_test_code(unittest_code)
        
        assert test_indicators["is_test_file"] is True
        assert test_indicators["test_framework"] == "unittest"
        assert test_indicators["test_count"] >= 2
        assert test_indicators["assertion_count"] >= 2
        assert test_indicators["fixture_usage"] is True  # setUp/tearDown

    def test_analyze_security_patterns(self):
        """Test security pattern analysis."""
        security_code = '''
import hashlib
import bcrypt
from cryptography.fernet import Fernet

API_KEY = "secret-api-key"
password = "plaintext_password"  # Bad practice

def hash_password(password):
    """Hash password securely."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)

def execute_query(user_input):
    # Dangerous: SQL injection risk
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return execute(query)

def dangerous_eval(user_code):
    # Very dangerous
    return eval(user_code)

def secure_request():
    response = requests.get("https://api.secure.com/data")
    return response

def handle_user_data(email, phone, ssn):
    # Processing PII data
    pass
'''
        
        security = self.extractor._analyze_security_patterns(security_code)
        
        # Should identify vulnerabilities
        assert "eval_usage" in security["potential_vulnerabilities"]
        assert "sql_queries" in security["potential_vulnerabilities"]
        assert "plaintext_password" in security["potential_vulnerabilities"]
        
        # Should identify good practices
        assert "password_hashing" in security["security_practices"]
        assert "secure_transport" in security["security_practices"]
        
        # Should identify sensitive data handling
        assert "credentials" in security["sensitive_data_handling"]
        assert "pii_data" in security["sensitive_data_handling"]

    def test_analyze_performance_patterns(self):
        """Test performance pattern analysis."""
        performance_code = '''
import asyncio
from functools import lru_cache
import multiprocessing as mp

@lru_cache(maxsize=128)
def expensive_calculation(n):
    """Cached expensive operation."""
    return sum(i**2 for i in range(n))

async def async_operation():
    """Asynchronous operation."""
    await asyncio.sleep(0.1)
    return "result"

def inefficient_loop():
    # Nested loops - potential bottleneck
    result = []
    for i in range(1000):
        for j in range(1000):
            for k in range(100):
                result.append(i * j * k)
    return result

def recursive_fibonacci(n):
    # Inefficient recursion
    if n <= 1:
        return n
    return recursive_fibonacci(n-1) + recursive_fibonacci(n-2)

class MemoryIntensive:
    def __init__(self):
        # Large data structure
        self.data = [0] * 1000000
'''
        
        performance = self.extractor._analyze_performance_patterns(performance_code)
        
        # Should identify optimization patterns
        assert "caching" in performance["optimization_patterns"]
        assert "async_programming" in performance["optimization_patterns"]
        
        # Should identify potential bottlenecks
        assert "nested_loops" in performance["potential_bottlenecks"]
        assert "recursion" in performance["potential_bottlenecks"]
        
        # Should identify resource usage
        assert "memory_allocation" in performance["resource_usage"]

    def test_extract_language_specific_metadata_python(self):
        """Test Python-specific metadata extraction."""
        python_code = '''
from typing import Optional, List, Dict
import asyncio

class AsyncProcessor:
    async def process_data(self, data: List[Dict]) -> Optional[str]:
        await asyncio.sleep(0.1)
        return "processed"
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def generator_function():
    for i in range(10):
        yield i

lambda_func = lambda x: x * 2
'''
        
        metadata = self.extractor._extract_language_specific_metadata(python_code, "python")
        
        python_features = metadata["python_features"]
        assert "async_await" in python_features
        assert "type_hints" in python_features
        assert "context_managers" in python_features
        assert "generators" in python_features
        assert "lambda_functions" in python_features

    def test_extract_language_specific_metadata_javascript(self):
        """Test JavaScript-specific metadata extraction."""
        js_code = '''
const arrow = (x) => x * 2;

class ModernClass {
    constructor(name) {
        this.name = name;
    }
    
    async fetchData() {
        const response = await fetch('/api/data');
        return response.json();
    }
    
    get displayName() {
        return `User: ${this.name}`;
    }
}

const {name, age} = user;
const numbers = [1, 2, 3];
const doubled = numbers.map(n => n * 2);

function* generatorFunc() {
    yield 1;
    yield 2;
}
'''
        
        metadata = self.extractor._extract_language_specific_metadata(js_code, "javascript")
        
        js_features = metadata["javascript_features"]
        assert "arrow_functions" in js_features
        assert "async_await" in js_features
        assert "destructuring" in js_features
        assert "template_literals" in js_features
        assert "generators" in js_features

    def test_extract_language_specific_metadata_unknown_language(self):
        """Test metadata extraction for unknown language."""
        code = "some generic code"
        metadata = self.extractor._extract_language_specific_metadata(code, "unknown")
        
        # Should return empty metadata for unknown languages
        assert metadata == {}

    def test_extract_hierarchical_metadata_unknown_language(self):
        """Test metadata extraction with unknown language."""
        code = "generic code content"
        chunk_metadata = {"language": "unknown"}
        document = Mock(spec=Document)
        
        metadata = self.extractor.extract_hierarchical_metadata(code, chunk_metadata, document)
        
        # Should still extract basic metadata
        assert "complexity_metrics" in metadata
        assert "code_patterns" in metadata
        assert metadata["content_type"] == "code"

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty content
        empty_metadata = self.extractor.extract_hierarchical_metadata("", {}, Mock())
        assert empty_metadata["content_type"] == "code"
        
        # Very short content
        short_metadata = self.extractor.extract_hierarchical_metadata("x=1", {}, Mock())
        assert short_metadata["complexity_metrics"]["lines_of_code"] == 1
        
        # Content with only whitespace
        whitespace_metadata = self.extractor.extract_hierarchical_metadata("   \n\n  ", {}, Mock())
        assert whitespace_metadata["complexity_metrics"]["lines_of_code"] >= 0
        
        # Test with None values
        entities = self.extractor.extract_entities("")
        assert entities == []

    def test_complex_real_world_code(self):
        """Test with complex real-world-like code example."""
        complex_code = '''
"""
E-commerce order processing system.
"""

import logging
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    product_id: str
    quantity: int
    price: float

class OrderProcessor:
    """Processes e-commerce orders with complex business logic."""
    
    MAX_RETRY_ATTEMPTS = 3
    TIMEOUT_SECONDS = 30
    
    def __init__(self, payment_service, inventory_service):
        self.payment_service = payment_service
        self.inventory_service = inventory_service
        self.retry_count = 0
    
    async def process_order(self, order_data: Dict) -> Optional[str]:
        """Process an order through the complete pipeline."""
        try:
            # Validate order
            if not self._validate_order(order_data):
                raise ValueError("Invalid order data")
            
            # Check inventory
            for item in order_data.get("items", []):
                if not await self._check_inventory(item):
                    return None
            
            # Process payment
            payment_result = await self._process_payment(order_data)
            if not payment_result:
                await self._handle_payment_failure(order_data)
                return None
            
            # Update inventory
            await self._update_inventory(order_data)
            
            # Send confirmation
            await self._send_order_confirmation(order_data)
            
            logger.info(f"Order {order_data['id']} processed successfully")
            return order_data["id"]
            
        except Exception as e:
            logger.error(f"Failed to process order: {e}")
            await self._handle_order_failure(order_data, str(e))
            return None
    
    def _validate_order(self, order_data: Dict) -> bool:
        """Validate order data."""
        required_fields = ["id", "customer_id", "items"]
        for field in required_fields:
            if field not in order_data:
                return False
        
        if not order_data["items"]:
            return False
        
        for item in order_data["items"]:
            if item.get("quantity", 0) <= 0:
                return False
            if item.get("price", 0) <= 0:
                return False
        
        return True
    
    async def _check_inventory(self, item: Dict) -> bool:
        """Check if item is available in inventory."""
        available = await self.inventory_service.check_availability(
            item["product_id"], item["quantity"]
        )
        return available
    
    async def _process_payment(self, order_data: Dict) -> bool:
        """Process payment for the order."""
        total_amount = sum(
            item["price"] * item["quantity"] 
            for item in order_data["items"]
        )
        
        payment_data = {
            "customer_id": order_data["customer_id"],
            "amount": total_amount,
            "currency": "USD"
        }
        
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                result = await asyncio.wait_for(
                    self.payment_service.charge(payment_data),
                    timeout=self.TIMEOUT_SECONDS
                )
                return result.success
            except asyncio.TimeoutError:
                logger.warning(f"Payment timeout, attempt {attempt + 1}")
                continue
            except Exception as e:
                logger.error(f"Payment error: {e}")
                break
        
        return False

# Unit tests
class TestOrderProcessor:
    """Test suite for OrderProcessor."""
    
    def test_validate_order_success(self):
        processor = OrderProcessor(None, None)
        valid_order = {
            "id": "order-123",
            "customer_id": "customer-456", 
            "items": [{"product_id": "prod-1", "quantity": 2, "price": 10.99}]
        }
        assert processor._validate_order(valid_order) is True
    
    def test_validate_order_missing_fields(self):
        processor = OrderProcessor(None, None)
        invalid_order = {"id": "order-123"}
        assert processor._validate_order(invalid_order) is False
'''
        
        chunk_metadata = {"language": "python", "file_type": ".py"}
        document = Mock(spec=Document)
        
        metadata = self.extractor.extract_hierarchical_metadata(
            complex_code, chunk_metadata, document
        )
        
        # Verify comprehensive analysis
        assert metadata["complexity_metrics"]["cyclomatic_complexity"] > 10
        assert metadata["complexity_metrics"]["lines_of_code"] > 50
        assert metadata["complexity_metrics"]["nesting_depth"] >= 3
        
        # Should identify patterns
        patterns = metadata["code_patterns"]
        assert "documentation" in patterns["best_practices"]
        assert "type_hints" in patterns["best_practices"]
        assert "testing" in patterns["best_practices"]
        
        # Should identify test code
        test_indicators = metadata["test_indicators"]
        assert test_indicators["is_test_file"] is True
        assert test_indicators["test_count"] >= 2
        
        # Should identify performance patterns
        performance = metadata["performance_indicators"]
        assert "async_programming" in performance["optimization_patterns"]
        
        # Should identify Python-specific features
        assert "python_features" in metadata
        python_features = metadata["python_features"]
        assert "async_await" in python_features
        assert "type_hints" in python_features
        assert "dataclasses" in python_features