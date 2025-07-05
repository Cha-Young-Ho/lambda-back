"""
Unit tests for repositories module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

# Import the module under test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../layers/common-layer/python'))

from common.repositories import BaseRepository, NewsRepository, GalleryRepository


class TestBaseRepository:
    """Test BaseRepository class"""
    
    @pytest.fixture
    def mock_app_config(self):
        """Mock app config"""
        config = Mock()
        config.get_dynamodb_config.return_value = {
            'region': 'us-east-1',
            'table_name': 'test-table',
            'endpoint_url': None
        }
        return config
    
    @pytest.fixture
    def mock_table(self):
        """Mock DynamoDB table"""
        table = Mock()
        return table
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_init(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test repository initialization"""
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        repo = BaseRepository(mock_app_config, 'test')
        
        assert repo.content_type == 'test'
        assert repo.app_config == mock_app_config
        mock_get_dynamodb.assert_called_once()
        mock_get_table.assert_called_once()
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    @patch('common.repositories.uuid.uuid4')
    def test_create_item(self, mock_uuid, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test create_item method"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        mock_uuid.return_value = Mock()
        mock_uuid.return_value.__str__ = Mock(return_value = 'test-id')
        
        repo = BaseRepository(mock_app_config, 'test')
        repo._clean_item_data = Mock(side_effect=lambda x: x)
        
        # Test data
        test_data = {'title': 'Test Title', 'content': 'Test Content'}
        
        # Call method
        result = repo.create_item(test_data)
        
        # Assertions
        assert result == 'test-id'
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        assert call_args['id'] == 'test-id'
        assert call_args['content_type'] == 'test'
        assert call_args['title'] == 'Test Title'
        assert call_args['content'] == 'Test Content'
        assert 'created_at' in call_args
        assert 'updated_at' in call_args
        assert call_args['status'] == 'published'
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_get_item_by_id_found(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test get_item_by_id when item exists"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        test_item = {
            'id': 'test-id',
            'content_type': 'test',
            'title': 'Test Title'
        }
        mock_table.get_item.return_value = {'Item': test_item}
        
        repo = BaseRepository(mock_app_config, 'test')
        repo._clean_output_data = Mock(side_effect=lambda x: x)
        
        # Call method
        result = repo.get_item_by_id('test-id')
        
        # Assertions
        assert result == test_item
        mock_table.get_item.assert_called_once_with(Key={'id': 'test-id'})
        repo._clean_output_data.assert_called_once_with(test_item)
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_get_item_by_id_not_found(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test get_item_by_id when item doesn't exist"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        mock_table.get_item.return_value = {}  # No 'Item' key
        
        repo = BaseRepository(mock_app_config, 'test')
        
        # Call method
        result = repo.get_item_by_id('non-existent-id')
        
        # Assertions
        assert result is None
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.layers.get_table')
    def test_get_item_by_id_wrong_content_type(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test get_item_by_id with wrong content type"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        test_item = {
            'id': 'test-id',
            'content_type': 'different',  # Different content type
            'title': 'Test Title'
        }
        mock_table.get_item.return_value = {'Item': test_item}
        
        repo = BaseRepository(mock_app_config, 'test')
        
        # Call method
        result = repo.get_item_by_id('test-id')
        
        # Assertions
        assert result is None


class TestNewsRepository:
    """Test NewsRepository class"""
    
    @pytest.fixture
    def mock_app_config(self):
        """Mock app config"""
        config = Mock()
        config.get_dynamodb_config.return_value = {
            'region': 'us-east-1',
            'table_name': 'test-table',
            'endpoint_url': None
        }
        return config
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_init(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test NewsRepository initialization"""
        repo = NewsRepository(mock_app_config)
        assert repo.content_type == 'news'
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_get_updatable_fields(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test get_updatable_fields method"""
        repo = NewsRepository(mock_app_config)
        fields = repo._get_updatable_fields()
        
        expected_fields = ['title', 'content', 'category', 'image_url', 'short_description']
        assert fields == expected_fields
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_clean_output_data(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test _clean_output_data method"""
        repo = NewsRepository(mock_app_config)
        
        test_data = {
            'id': 'news-1',
            'title': 'Test News',
            'content': 'Test Content',
            'category': '센터소식',
            'created_at': '2025-07-06T10:00:00Z',
            'updated_at': '2025-07-06T10:00:00Z',
            'status': 'published',
            'image_url': 'http://example.com/image.jpg',
            'short_description': 'Test description',
            'extra_field': 'should_not_appear'  # This should be filtered out
        }
        
        result = repo._clean_output_data(test_data)
        
        # Check expected fields are present
        assert result['id'] == 'news-1'
        assert result['title'] == 'Test News'
        assert result['content'] == 'Test Content'
        assert result['category'] == '센터소식'
        assert result['image_url'] == 'http://example.com/image.jpg'
        assert result['short_description'] == 'Test description'
        assert result['date'] == '2025-07-06'  # Extracted from created_at
        
        # Check extra field is not present
        assert 'extra_field' not in result


class TestGalleryRepository:
    """Test GalleryRepository class"""
    
    @pytest.fixture
    def mock_app_config(self):
        """Mock app config"""
        config = Mock()
        config.get_dynamodb_config.return_value = {
            'region': 'us-east-1',
            'table_name': 'test-table',
            'endpoint_url': None
        }
        return config
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_init(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test GalleryRepository initialization"""
        repo = GalleryRepository(mock_app_config)
        assert repo.content_type == 'gallery'
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_get_updatable_fields(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test get_updatable_fields method"""
        repo = GalleryRepository(mock_app_config)
        fields = repo._get_updatable_fields()
        
        expected_fields = ['title', 'content', 'category', 'image_url', 'short_description']
        assert fields == expected_fields
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_clean_output_data(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test _clean_output_data method"""
        repo = GalleryRepository(mock_app_config)
        
        test_data = {
            'id': 'gallery-1',
            'title': 'Test Gallery',
            'content': 'Test Content',
            'category': '공지사항',
            'created_at': '2025-07-06T10:00:00Z',
            'updated_at': '2025-07-06T10:00:00Z',
            'status': 'published',
            'image_url': 'http://example.com/image.jpg',
            'short_description': 'Test description',
            'extra_field': 'should_not_appear'  # This should be filtered out
        }
        
        result = repo._clean_output_data(test_data)
        
        # Check expected fields are present
        assert result['id'] == 'gallery-1'
        assert result['title'] == 'Test Gallery'
        assert result['content'] == 'Test Content'
        assert result['category'] == '공지사항'
        assert result['image_url'] == 'http://example.com/image.jpg'
        assert result['short_description'] == 'Test description'
        assert result['date'] == '2025-07-06'  # Extracted from created_at
        
        # Check extra field is not present
        assert 'extra_field' not in result
