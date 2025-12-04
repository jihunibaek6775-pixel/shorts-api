import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

# S3 클라이언트 생성
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

def upload_file_to_s3(file_content: bytes, filename: str, content_type: str) -> str:
    """
    S3에 파일 업로드
    Returns: S3 URL
    """
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=file_content,
            ContentType=content_type
        )
        
        # S3 URL 생성
        s3_url = f"https://{BUCKET_NAME}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{filename}"
        return s3_url
    
    except ClientError as e:
        print(f"S3 업로드 에러: {e}")
        raise

def get_file_from_s3(filename: str):
    """
    S3에서 파일 가져오기
    """
    try:
        response = s3_client.get_object(
            Bucket=BUCKET_NAME,
            Key=filename
        )
        return response
    except ClientError as e:
        print(f"S3 다운로드 에러: {e}")
        raise

def delete_file_from_s3(filename: str):
    """
    S3에서 파일 삭제
    """
    try:
        s3_client.delete_object(
            Bucket=BUCKET_NAME,
            Key=filename
        )
    except ClientError as e:
        print(f"S3 삭제 에러: {e}")
        raise