"""
S3 File Management Service
- Presigned URL 생성
- 파일 삭제
- 파일 업로드 관리
"""
import boto3
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

from .config import AppConfig
from .logging import get_logger

logger = get_logger(__name__)

class S3Service:
    """S3 파일 관리 서비스"""
    
    def __init__(self, app_config: AppConfig):
        self.config = app_config
        self.bucket_name = app_config.get_config_value('s3_bucket_name', 'your-default-bucket')
        
        # S3 클라이언트 초기화
        if app_config.stage == 'local':
            # 로컬 개발 환경
            self.s3_client = boto3.client('s3')
        else:
            # AWS 환경
            self.s3_client = boto3.client('s3')
    
    def generate_presigned_upload_url(
        self, 
        content_type: str, 
        file_extension: str = None,
        folder: str = "uploads"
    ) -> Dict[str, Any]:
        """
        파일 업로드용 presigned URL 생성
        
        Args:
            content_type: 파일의 MIME 타입 (예: 'image/jpeg', 'image/png')
            file_extension: 파일 확장자 (예: '.jpg', '.png')
            folder: S3 버킷 내 폴더명
            
        Returns:
            Dict containing upload_url, file_key, and expiration info
        """
        try:
            # 고유한 파일 키 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            
            if file_extension:
                if not file_extension.startswith('.'):
                    file_extension = f'.{file_extension}'
                file_key = f"{folder}/{timestamp}_{unique_id}{file_extension}"
            else:
                file_key = f"{folder}/{timestamp}_{unique_id}"
            
            # Presigned URL 생성 (15분 유효)
            expiration = 900  # 15 minutes
            
            upload_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key,
                    'ContentType': content_type
                },
                ExpiresIn=expiration
            )
            
            # 업로드 후 파일 접근 URL
            file_url = f"https://{self.bucket_name}.s3.amazonaws.com/{file_key}"
            
            logger.info(f"Generated presigned URL for {file_key}")
            
            return {
                'upload_url': upload_url,
                'file_key': file_key,
                'file_url': file_url,
                'expires_in': expiration,
                'expires_at': (datetime.now() + timedelta(seconds=expiration)).isoformat()
            }
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise Exception(f"Failed to generate upload URL: {str(e)}")
    
    def delete_file(self, file_key: str) -> bool:
        """
        S3에서 파일 삭제
        
        Args:
            file_key: S3 객체 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            logger.info(f"Deleted file: {file_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting file {file_key}: {str(e)}")
            return False
    
    def delete_files(self, file_keys: List[str]) -> Dict[str, bool]:
        """
        여러 파일을 일괄 삭제
        
        Args:
            file_keys: 삭제할 파일 키 목록
            
        Returns:
            Dict: 각 파일의 삭제 결과
        """
        results = {}
        
        if not file_keys:
            return results
        
        # 배치 삭제 (최대 1000개까지)
        try:
            objects_to_delete = [{'Key': key} for key in file_keys[:1000]]
            
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            
            # 성공한 삭제
            for deleted in response.get('Deleted', []):
                results[deleted['Key']] = True
            
            # 실패한 삭제
            for error in response.get('Errors', []):
                results[error['Key']] = False
                logger.error(f"Failed to delete {error['Key']}: {error['Message']}")
            
            # 요청하지 않은 키들도 실패로 표시
            for key in file_keys:
                if key not in results:
                    results[key] = False
            
            logger.info(f"Batch deleted {len([k for k, v in results.items() if v])} files")
            
        except ClientError as e:
            logger.error(f"Error in batch delete: {str(e)}")
            # 모든 파일을 실패로 표시
            for key in file_keys:
                results[key] = False
        
        return results
    
    def extract_file_key_from_url(self, file_url: str) -> Optional[str]:
        """
        파일 URL에서 S3 키 추출
        
        Args:
            file_url: S3 파일 URL
            
        Returns:
            str: S3 객체 키 또는 None
        """
        if not file_url:
            return None
        
        try:
            # https://bucket-name.s3.amazonaws.com/path/to/file.jpg 형태에서 키 추출
            if f"{self.bucket_name}.s3.amazonaws.com/" in file_url:
                return file_url.split(f"{self.bucket_name}.s3.amazonaws.com/", 1)[1]
            
            # https://s3.amazonaws.com/bucket-name/path/to/file.jpg 형태에서 키 추출
            elif f"s3.amazonaws.com/{self.bucket_name}/" in file_url:
                return file_url.split(f"s3.amazonaws.com/{self.bucket_name}/", 1)[1]
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting file key from URL {file_url}: {str(e)}")
            return None
    
    def get_file_info(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        S3 파일 정보 조회
        
        Args:
            file_key: S3 객체 키
            
        Returns:
            Dict: 파일 정보 또는 None
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            return {
                'file_key': file_key,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType', ''),
                'etag': response['ETag'].strip('"')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"Error getting file info for {file_key}: {str(e)}")
            return None

def get_allowed_content_types(file_type: str = 'all') -> List[str]:
    """허용되는 파일 타입 목록"""
    image_types = [
        'image/jpeg',
        'image/jpg', 
        'image/png',
        'image/gif',
        'image/webp'
    ]
    
    document_types = [
        'application/pdf',
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if file_type == 'image':
        return image_types
    elif file_type == 'document':
        return document_types
    else:
        return image_types + document_types

def get_file_extension_from_content_type(content_type: str) -> str:
    """Content-Type에서 파일 확장자 추출"""
    content_type_map = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'application/pdf': '.pdf',
        'text/plain': '.txt',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
    }
    
    return content_type_map.get(content_type, '')
