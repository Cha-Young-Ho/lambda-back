"""
업계 표준 예외 클래스 정의
"""

class BlogException(Exception):
    """Base exception for blog application"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BlogException):
    """입력 데이터 검증 실패"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 400, details)


class AuthenticationError(BlogException):
    """인증 실패"""
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message, 401, details)


class AuthorizationError(BlogException):
    """권한 없음"""
    def __init__(self, message: str = "Access denied", details: dict = None):
        super().__init__(message, 403, details)


class ResourceNotFoundError(BlogException):
    """리소스 없음"""
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__(message, 404, details)


class ConflictError(BlogException):
    """중복 리소스"""
    def __init__(self, message: str = "Resource already exists", details: dict = None):
        super().__init__(message, 409, details)


class DatabaseError(BlogException):
    """데이터베이스 오류"""
    def __init__(self, message: str = "Database operation failed", details: dict = None):
        super().__init__(message, 500, details)


class ExternalServiceError(BlogException):
    """외부 서비스 오류"""
    def __init__(self, message: str = "External service error", details: dict = None):
        super().__init__(message, 502, details)
