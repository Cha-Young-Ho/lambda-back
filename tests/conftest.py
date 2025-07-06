"""
Test configuration and fixtures for the blog system tests
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch
import boto3
from moto import mock_dynamodb

# Add common layer to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../layers/common-layer/python'))

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables"""
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['DYNAMODB_ENDPOINT'] = 'http://localhost:8001'
    os.environ['STAGE'] = 'test'
    os.environ['TABLE_NAME'] = 'blog-table-test'

@pytest.fixture
def mock_dynamodb_table():
    """Create a mock DynamoDB table for testing"""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        table = dynamodb.create_table(
            TableName='blog-table-test',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        yield table

@pytest.fixture
def dynamodb_table():
    """Create a real DynamoDB table for integration testing (alias for mock_dynamodb_table)"""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        table = dynamodb.create_table(
            TableName='blog-table-test',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        yield table

@pytest.fixture
def mock_app_config():
    """Mock application configuration"""
    return {
        'table_name': 'blog-table-test',
        'dynamodb_endpoint': 'http://localhost:8000',
        'region': 'us-east-1',
        'jwt_secret': 'test-secret-key',
        'stage': 'test'
    }

@pytest.fixture
def sample_news_item():
    """Sample news item for testing"""
    return {
        'id': 'news_test_1',
        'title': 'Test News',
        'content': 'Test content',
        'category': '센터소식',
        'status': 'published',
        'created_at': '2025-07-06T10:00:00Z',
        'updated_at': '2025-07-06T10:00:00Z',
        'image_url': 'https://example.com/image.jpg',
        'short_description': 'Test description',
        'date': '2025-07-06'
    }

@pytest.fixture
def sample_gallery_item():
    """Sample gallery item for testing"""
    return {
        'id': 'gallery_test_1',
        'title': 'Test Gallery',
        'content': 'Test gallery content',
        'category': '공지사항',
        'status': 'published',
        'created_at': '2025-07-06T10:00:00Z',
        'updated_at': '2025-07-06T10:00:00Z',
        'image_url': 'https://example.com/gallery.jpg',
        'short_description': 'Test gallery description',
        'date': '2025-07-06'
    }

@pytest.fixture
def sample_news_data():
    """Sample news data for testing (without id)"""
    return {
        'title': 'Test News Item',
        'content': 'This is test news content for integration testing.',
        'category': '센터소식',
        'status': 'published',
        'image_url': 'https://example.com/test-news.jpg',
        'short_description': 'Test news description for integration testing',
        'date': '2025-07-06'
    }

@pytest.fixture
def admin_token():
    """Mock admin JWT token for testing"""
    # This is a mock token for testing purposes
    # In real tests, you might want to generate a proper JWT
    return 'mock_admin_token_for_testing'

# Add any additional test utilities here
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )