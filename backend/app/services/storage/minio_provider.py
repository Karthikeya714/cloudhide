"""MinIO (S3-compatible) storage provider."""
import logging
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.services.storage.base import StorageProvider

logger = logging.getLogger(__name__)


class MinIOStorageProvider(StorageProvider):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ):
        self.bucket = bucket
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
            logger.info("Created MinIO bucket %s", bucket)

    def upload_file(self, key: str, data: bytes) -> str:
        self.client.put_object(self.bucket, key, BytesIO(data), length=len(data))
        return f"minio://{self.bucket}/{key}"

    def download_file(self, key: str) -> bytes:
        try:
            response = self.client.get_object(self.bucket, key)
        except S3Error as exc:
            raise FileNotFoundError(f"No such object: {key}") from exc

        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, key: str) -> None:
        self.client.remove_object(self.bucket, key)

    def file_exists(self, key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error:
            return False
