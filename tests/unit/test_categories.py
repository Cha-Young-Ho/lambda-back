"""
Unit tests for categories module
"""
import pytest
from unittest.mock import patch

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

# Import the module under test
from common.categories import (
    ContentType,
    get_allowed_categories,
    get_default_category,
    validate_category_value,
    is_category_required,
    get_category_info,
    normalize_category,
    get_validation_error_message,
    add_category,
    remove_category,
    get_all_categories,
    CATEGORY_DEFINITIONS
)


class TestContentType:
    """Test ContentType enum"""
    
    def test_content_type_values(self):
        """Test enum values"""
        assert ContentType.NEWS.value == "news"
        assert ContentType.GALLERY.value == "gallery"


@pytest.mark.unit
class TestGetAllowedCategories:
    """Test get_allowed_categories function"""
    
    def test_valid_content_types(self):
        """Test with valid content types"""
        news_categories = get_allowed_categories("news")
        assert isinstance(news_categories, list)
        assert "센터소식" in news_categories
        
        gallery_categories = get_allowed_categories("gallery")
        assert isinstance(gallery_categories, list)
        assert "공지사항" in gallery_categories
    
    def test_invalid_content_type(self):
        """Test with invalid content type"""
        result = get_allowed_categories("invalid")
        assert result == []
        
        result = get_allowed_categories("")
        assert result == []
    
    def test_case_insensitive(self):
        """Test case insensitive input"""
        result = get_allowed_categories("NEWS")
        assert len(result) > 0
        
        result = get_allowed_categories("Gallery")
        assert len(result) > 0


class TestGetDefaultCategory:
    """Test get_default_category function"""
    
    def test_valid_content_types(self):
        """Test with valid content types"""
        news_default = get_default_category("news")
        assert news_default == "기타"
        
        gallery_default = get_default_category("gallery")
        assert gallery_default == "공지사항"
    
    def test_invalid_content_type(self):
        """Test with invalid content type"""
        result = get_default_category("invalid")
        assert result is None


class TestValidateCategoryValue:
    """Test validate_category_value function"""
    
    def test_valid_categories(self):
        """Test with valid categories"""
        assert validate_category_value("news", "센터소식") is True
        assert validate_category_value("gallery", "공지사항") is True
    
    def test_invalid_categories(self):
        """Test with invalid categories"""
        assert validate_category_value("news", "invalid_category") is False
        assert validate_category_value("gallery", "invalid_category") is False
    
    def test_empty_category(self):
        """Test with empty category (should be allowed)"""
        assert validate_category_value("news", "") is True
        assert validate_category_value("news", None) is True


class TestIsCategoryRequired:
    """Test is_category_required function"""
    
    def test_category_requirement(self):
        """Test category requirements for different content types"""
        # Based on CATEGORY_DEFINITIONS, both news and gallery have required: False
        assert is_category_required("news") is False
        assert is_category_required("gallery") is False
    
    def test_invalid_content_type(self):
        """Test with invalid content type"""
        assert is_category_required("invalid") is False


class TestGetCategoryInfo:
    """Test get_category_info function"""
    
    def test_valid_content_types(self):
        """Test with valid content types"""
        news_info = get_category_info("news")
        assert isinstance(news_info, dict)
        assert "allowed_categories" in news_info
        assert "default_category" in news_info
        assert "required" in news_info
        assert "description" in news_info
    
    def test_invalid_content_type(self):
        """Test with invalid content type"""
        result = get_category_info("invalid")
        assert result["allowed_categories"] == []
        assert result["default_category"] is None
        assert result["required"] is False
        assert "Unknown content type" in result["description"]


class TestNormalizeCategory:
    """Test normalize_category function"""
    
    def test_valid_category_normalization(self):
        """Test normalization of valid categories"""
        result = normalize_category("news", "  센터소식  ")
        assert result == "센터소식"
    
    def test_empty_category_handling(self):
        """Test handling of empty categories"""
        # For non-required content types, empty should return None
        result = normalize_category("news", "")
        assert result is None
        
        result = normalize_category("news", "   ")
        assert result is None
    
    def test_invalid_category_handling(self):
        """Test handling of invalid categories"""
        result = normalize_category("news", "invalid_category")
        assert result is None


class TestGetValidationErrorMessage:
    """Test get_validation_error_message function"""
    
    def test_error_message_format(self):
        """Test error message format"""
        message = get_validation_error_message("news", "invalid_category")
        assert "invalid_category" in message
        assert "news" in message
        assert "Allowed categories:" in message


class TestCategoryManagement:
    """Test category management functions"""
    
    def test_add_category(self):
        """Test adding new category"""
        # Save original state
        original_categories = CATEGORY_DEFINITIONS[ContentType.NEWS]["allowed_categories"].copy()
        
        try:
            # Add new category
            result = add_category("news", "새로운카테고리")
            assert result is True
            
            # Verify it was added
            categories = get_allowed_categories("news")
            assert "새로운카테고리" in categories
            
            # Try to add same category again
            result = add_category("news", "새로운카테고리")
            assert result is False
        
        finally:
            # Restore original state
            CATEGORY_DEFINITIONS[ContentType.NEWS]["allowed_categories"] = original_categories
    
    def test_remove_category(self):
        """Test removing category"""
        # Save original state
        original_categories = CATEGORY_DEFINITIONS[ContentType.NEWS]["allowed_categories"].copy()
        
        try:
            # Add a category first
            add_category("news", "임시카테고리")
            
            # Remove it
            result = remove_category("news", "임시카테고리")
            assert result is True
            
            # Verify it was removed
            categories = get_allowed_categories("news")
            assert "임시카테고리" not in categories
            
            # Try to remove non-existent category
            result = remove_category("news", "존재하지않는카테고리")
            assert result is False
        
        finally:
            # Restore original state
            CATEGORY_DEFINITIONS[ContentType.NEWS]["allowed_categories"] = original_categories
    
    def test_invalid_content_type_management(self):
        """Test category management with invalid content type"""
        assert add_category("invalid", "category") is False
        assert remove_category("invalid", "category") is False


class TestGetAllCategories:
    """Test get_all_categories function"""
    
    def test_all_categories_structure(self):
        """Test structure of all categories response"""
        all_categories = get_all_categories()
        assert isinstance(all_categories, dict)
        assert "news" in all_categories
        assert "gallery" in all_categories
        
        # Each should be a list
        assert isinstance(all_categories["news"], list)
        assert isinstance(all_categories["gallery"], list)
        
        # Should contain expected categories
        assert "센터소식" in all_categories["news"]
        assert "공지사항" in all_categories["gallery"]
