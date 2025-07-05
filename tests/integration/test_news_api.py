"""
Integration tests for News API
"""
import pytest
import json
from unittest.mock import patch, MagicMock

# Import the News app
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../news'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../layers/common-layer/python'))

from app import lambda_handler
from common.config import AppConfig


@pytest.mark.integration
class TestNewsAPI:
    """Integration tests for News API endpoints"""
    
    def test_get_news_list(self, mock_app_config, dynamodb_table, sample_news_data):
        """Test GET /news endpoint"""
        # Insert test data
        dynamodb_table.put_item(Item={
            'id': 'news_1',
            'content_type': 'news',
            'created_at': '2025-07-06T10:00:00Z',
            'updated_at': '2025-07-06T10:00:00Z',
            'status': 'published',
            **sample_news_data
        })
        
        # Create request event
        event = {
            'httpMethod': 'GET',
            'path': '/news',
            'queryStringParameters': None,
            'headers': {},
            'body': None
        }
        
        context = {}
        
        # Mock the AppConfig
        with patch('app.AppConfig', return_value=mock_app_config):
            response = lambda_handler(event, context)
        
        # Assertions
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'items' in body
        assert 'pagination' in body
        assert len(body['items']) >= 1
        
        # Check first item
        first_item = body['items'][0]
        assert first_item['title'] == sample_news_data['title']
        assert first_item['category'] == sample_news_data['category']
    
    def test_get_news_by_id(self, mock_app_config, dynamodb_table, sample_news_data):
        """Test GET /news/{id} endpoint"""
        news_id = 'news_test_1'
        
        # Insert test data
        dynamodb_table.put_item(Item={
            'id': news_id,
            'content_type': 'news',
            'created_at': '2025-07-06T10:00:00Z',
            'updated_at': '2025-07-06T10:00:00Z',
            'status': 'published',
            **sample_news_data
        })
        
        # Create request event
        event = {
            'httpMethod': 'GET',
            'path': f'/news/{news_id}',
            'pathParameters': {'newsId': news_id},
            'queryStringParameters': None,
            'headers': {},
            'body': None
        }
        
        context = {}
        
        # Mock the AppConfig
        with patch('app.AppConfig', return_value=mock_app_config):
            response = lambda_handler(event, context)
        
        # Assertions
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['id'] == news_id
        assert body['title'] == sample_news_data['title']
        assert body['content'] == sample_news_data['content']
    
    def test_get_news_by_id_not_found(self, mock_app_config, dynamodb_table):
        """Test GET /news/{id} with non-existent ID"""
        event = {
            'httpMethod': 'GET',
            'path': '/news/non_existent',
            'pathParameters': {'newsId': 'non_existent'},
            'queryStringParameters': None,
            'headers': {},
            'body': None
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            response = lambda_handler(event, context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_create_news_without_auth(self, mock_app_config, dynamodb_table, sample_news_data):
        """Test POST /news without authentication"""
        event = {
            'httpMethod': 'POST',
            'path': '/news',
            'headers': {},
            'body': json.dumps(sample_news_data)
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            response = lambda_handler(event, context)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_create_news_with_auth(self, mock_app_config, dynamodb_table, sample_news_data, admin_token):
        """Test POST /news with authentication"""
        event = {
            'httpMethod': 'POST',
            'path': '/news',
            'headers': {
                'Authorization': f'Bearer {admin_token}'
            },
            'body': json.dumps(sample_news_data)
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            # Mock JWT validation
            with patch('common.jwt_service.validate_token', return_value={'username': 'admin'}):
                response = lambda_handler(event, context)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'id' in body
        assert body['title'] == sample_news_data['title']
    
    def test_create_news_invalid_category(self, mock_app_config, dynamodb_table, admin_token):
        """Test POST /news with invalid category"""
        invalid_data = {
            'title': 'Test News',
            'content': 'Test content',
            'category': 'InvalidCategory'  # Invalid category
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/news',
            'headers': {
                'Authorization': f'Bearer {admin_token}'
            },
            'body': json.dumps(invalid_data)
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            with patch('common.jwt_service.validate_token', return_value={'username': 'admin'}):
                response = lambda_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'category' in body['error'].lower()
    
    def test_update_news(self, mock_app_config, dynamodb_table, sample_news_data, admin_token):
        """Test PUT /news/{id} endpoint"""
        news_id = 'news_update_test'
        
        # Insert test data
        dynamodb_table.put_item(Item={
            'id': news_id,
            'content_type': 'news',
            'created_at': '2025-07-06T10:00:00Z',
            'updated_at': '2025-07-06T10:00:00Z',
            'status': 'published',
            **sample_news_data
        })
        
        # Update data
        update_data = {
            'title': 'Updated News Title',
            'content': 'Updated content'
        }
        
        event = {
            'httpMethod': 'PUT',
            'path': f'/news/{news_id}',
            'pathParameters': {'newsId': news_id},
            'headers': {
                'Authorization': f'Bearer {admin_token}'
            },
            'body': json.dumps(update_data)
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            with patch('common.jwt_service.validate_token', return_value={'username': 'admin'}):
                response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['title'] == 'Updated News Title'
    
    def test_delete_news(self, mock_app_config, dynamodb_table, sample_news_data, admin_token):
        """Test DELETE /news/{id} endpoint"""
        news_id = 'news_delete_test'
        
        # Insert test data
        dynamodb_table.put_item(Item={
            'id': news_id,
            'content_type': 'news',
            'created_at': '2025-07-06T10:00:00Z',
            'updated_at': '2025-07-06T10:00:00Z',
            'status': 'published',
            **sample_news_data
        })
        
        event = {
            'httpMethod': 'DELETE',
            'path': f'/news/{news_id}',
            'pathParameters': {'newsId': news_id},
            'headers': {
                'Authorization': f'Bearer {admin_token}'
            }
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            with patch('common.jwt_service.validate_token', return_value={'username': 'admin'}):
                response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        
        # Verify item is deleted
        response = dynamodb_table.get_item(Key={'id': news_id})
        assert 'Item' not in response
    
    def test_get_recent_news(self, mock_app_config, dynamodb_table, sample_news_data):
        """Test GET /news/recent endpoint"""
        # Insert multiple news items with different timestamps
        for i in range(3):
            dynamodb_table.put_item(Item={
                'id': f'news_recent_{i}',
                'content_type': 'news',
                'title': f'Recent News {i}',
                'content': 'Recent content',
                'category': '센터소식',
                'created_at': f'2025-07-0{6-i}T10:00:00Z',  # Different dates
                'updated_at': f'2025-07-0{6-i}T10:00:00Z',
                'status': 'published'
            })
        
        event = {
            'httpMethod': 'GET',
            'path': '/news/recent',
            'queryStringParameters': {'limit': '2'},
            'headers': {},
            'body': None
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'items' in body
        assert len(body['items']) <= 2  # Should respect limit
    
    def test_cors_headers(self, mock_app_config, dynamodb_table):
        """Test CORS headers are present in responses"""
        event = {
            'httpMethod': 'GET',
            'path': '/news',
            'queryStringParameters': None,
            'headers': {},
            'body': None
        }
        
        context = {}
        
        with patch('app.AppConfig', return_value=mock_app_config):
            response = lambda_handler(event, context)
        
        # Check CORS headers
        headers = response.get('headers', {})
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Methods' in headers
        assert 'Access-Control-Allow-Headers' in headers
