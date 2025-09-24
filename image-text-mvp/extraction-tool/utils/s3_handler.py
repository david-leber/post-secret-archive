import boto3
from typing import Any

from werkzeug.datastructures import FileStorage
from config import Config
from logging import getLogger

LOG = getLogger(__name__)


class S3Handler:
    def __init__(self):
        self.s3_client: Any = boto3.client(  # type: ignore
            "s3",
            endpoint_url=Config.AWS_ENDPOINT_URL,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_DEFAULT_REGION,
        )
        self.bucket_name = Config.S3_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except Exception:
            LOG.info(
                f"Bucket {self.bucket_name} does not exist. Creating it.", exc_info=True
            )
            self.s3_client.create_bucket(Bucket=self.bucket_name)

    def upload_file(self, file_obj: FileStorage, s3_key: str) -> str:
        """Upload file to S3"""
        self.s3_client.upload_fileobj(file_obj, self.bucket_name, s3_key)
        return f"{Config.AWS_ENDPOINT_URL}/{self.bucket_name}/{s3_key}"

    def get_file_url(self, s3_key: str) -> str:
        """Get URL for file in S3"""
        return f"{Config.AWS_PUBLIC_ENDPOINT_URL}/{self.bucket_name}/{s3_key}"
