"""
Unit tests for repositories module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

# Import the module under test
from common.repositories import BaseRepository, NewsRepository, GalleryRepository


class ConcreteTestRepository(BaseRepository):
    """Concrete test implementation of BaseRepository"""
    
    def _get_updatable_fields(self):
        return ['title', 'content', 'category']
    
    def _clean_item_data(self, data):
        return data
    
    def _clean_output_data(self, data):
        return data


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
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
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
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
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
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Call method
        result = repo.get_item_by_id('test-id')
        
        # Assertions
        assert result == test_item
        mock_table.get_item.assert_called_once_with(Key={'id': 'test-id'})
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_get_item_by_id_not_found(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test get_item_by_id when item doesn't exist"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        mock_table.get_item.return_value = {}  # No 'Item' key
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Call method
        result = repo.get_item_by_id('non-existent-id')
        
        # Assertions
        assert result is None
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
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
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Call method
        result = repo.get_item_by_id('test-id')
        
        # Assertions
        assert result is None
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_update_item_success(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test update_item method with successful update"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Mock existing item check
        existing_item = {'id': 'test-id', 'title': 'Old Title'}
        repo.get_item_by_id = Mock(return_value=existing_item)
        
        # Test data
        update_data = {'title': 'New Title', 'content': 'New Content'}
        
        # Call method
        result = repo.update_item('test-id', update_data)
        
        # Assertions
        assert result is True
        mock_table.update_item.assert_called_once()
        
        # Check update expression
        call_args = mock_table.update_item.call_args[1]
        assert 'SET updated_at = :updated_at' in call_args['UpdateExpression']
        assert 'title = :title' in call_args['UpdateExpression']
        assert 'content = :content' in call_args['UpdateExpression']
        assert ':updated_at' in call_args['ExpressionAttributeValues']
        assert ':title' in call_args['ExpressionAttributeValues']
        assert ':content' in call_args['ExpressionAttributeValues']
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_update_item_not_found(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test update_item method when item doesn't exist"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Mock existing item check - return None (not found)
        repo.get_item_by_id = Mock(return_value=None)
        
        # Test data
        update_data = {'title': 'New Title'}
        
        # Call method
        result = repo.update_item('test-id', update_data)
        
        # Assertions
        assert result is False
        mock_table.update_item.assert_not_called()
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_update_item_no_valid_fields(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test update_item method with no valid fields to update"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Mock existing item check
        existing_item = {'id': 'test-id', 'title': 'Old Title'}
        repo.get_item_by_id = Mock(return_value=existing_item)
        
        # Test data with no updatable fields
        update_data = {'invalid_field': 'Some Value'}
        
        # Call method
        result = repo.update_item('test-id', update_data)
        
        # Assertions - should return True because there's nothing to update
        assert result is True
        mock_table.update_item.assert_not_called()
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_delete_item_success(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test delete_item method with successful deletion"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Mock existing item check
        existing_item = {'id': 'test-id', 'title': 'Test Title'}
        repo.get_item_by_id = Mock(return_value=existing_item)
        
        # Call method
        result = repo.delete_item('test-id')
        
        # Assertions
        assert result is True
        mock_table.delete_item.assert_called_once_with(Key={'id': 'test-id'})
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_delete_item_not_found(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test delete_item method when item doesn't exist"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Mock existing item check - return None (not found)
        repo.get_item_by_id = Mock(return_value=None)
        
        # Call method
        result = repo.delete_item('test-id')
        
        # Assertions
        assert result is False
        mock_table.delete_item.assert_not_called()
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_list_items_basic(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test list_items method with basic functionality"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        # Mock scan response
        mock_items = [
            {'id': 'item1', 'content_type': 'test', 'title': 'Title 1', 'created_at': '2025-07-06T10:00:00Z'},
            {'id': 'item2', 'content_type': 'test', 'title': 'Title 2', 'created_at': '2025-07-05T10:00:00Z'}
        ]
        mock_table.scan.return_value = {'Items': mock_items}
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Call method
        result = repo.list_items()
        
        # Assertions
        assert 'items' in result
        assert 'next_key' in result
        assert 'total' in result
        assert len(result['items']) == 2
        assert result['total'] == 2
        
        # Check scan was called with correct parameters
        call_args = mock_table.scan.call_args[1]
        assert 'FilterExpression' in call_args
        assert call_args['Limit'] == 50
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_list_items_with_category_filter(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test list_items method with category filter"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        # Mock scan response
        mock_items = [
            {'id': 'item1', 'content_type': 'test', 'category': 'news', 'created_at': '2025-07-06T10:00:00Z'}
        ]
        mock_table.scan.return_value = {'Items': mock_items}
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Call method with category filter
        result = repo.list_items(category='news')
        
        # Assertions
        assert len(result['items']) == 1
        mock_table.scan.assert_called_once()
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_list_items_with_pagination(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test list_items method with pagination"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        # Mock scan response with LastEvaluatedKey
        mock_items = [
            {'id': 'item1', 'content_type': 'test', 'created_at': '2025-07-06T10:00:00Z'}
        ]
        mock_table.scan.return_value = {
            'Items': mock_items,
            'LastEvaluatedKey': {'id': 'item1'}
        }
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Call method with pagination
        result = repo.list_items(limit=10, last_evaluated_key='prev-key')
        
        # Assertions
        assert result['next_key'] == 'item1'
        
        # Check scan was called with ExclusiveStartKey
        call_args = mock_table.scan.call_args[1]
        assert call_args['ExclusiveStartKey'] == {'id': 'prev-key'}
        assert call_args['Limit'] == 10
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_get_recent_items(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test get_recent_items method"""
        # Setup mocks
        mock_table = Mock()
        mock_get_table.return_value = mock_table
        
        repo = ConcreteTestRepository(mock_app_config, 'test')
        
        # Mock list_items method
        mock_recent_items = [
            {'id': 'item1', 'title': 'Recent 1'},
            {'id': 'item2', 'title': 'Recent 2'}
        ]
        repo.list_items = Mock(return_value={'items': mock_recent_items})
        
        # Call method
        result = repo.get_recent_items(5)
        
        # Assertions
        assert result == mock_recent_items
        repo.list_items.assert_called_once_with(limit=5)
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_clean_item_data(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test _clean_item_data method"""
        repo = NewsRepository(mock_app_config)
        
        test_data = {
            'title': 'Test News',
            'content': 'Test Content',
            'category': '센터소식'
        }
        
        result = repo._clean_item_data(test_data)
        
        # Check that original data is preserved
        assert result['title'] == 'Test News'
        assert result['content'] == 'Test Content'
        assert result['category'] == '센터소식'
        
        # Check that default values are set
        assert result['image_url'] == ''
        assert result['short_description'] == ''
    
    @patch('common.repositories.get_dynamodb')
    @patch('common.repositories.get_table')
    def test_clean_item_data_gallery(self, mock_get_table, mock_get_dynamodb, mock_app_config):
        """Test _clean_item_data method for GalleryRepository"""
        repo = GalleryRepository(mock_app_config)
        
        test_data = {
            'title': 'Test Gallery',
            'content': 'Test Content',
            'category': '공지사항'
        }
        
        result = repo._clean_item_data(test_data)
        
        # Check that original data is preserved
        assert result['title'] == 'Test Gallery'
        assert result['content'] == 'Test Content'
        assert result['category'] == '공지사항'
        
        # Check that default values are set
        assert result['image_url'] == ''
        assert result['short_description'] == ''
