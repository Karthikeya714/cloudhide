"""Storage provider tests.

LocalStorageProvider is tested against a real temp directory. MinIOStorageProvider
is tested with the `minio` client mocked out, since a real MinIO server is not
provisioned in this environment -- this still exercises the provider's request
shaping and error translation, per "integration tests where practical".
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from minio.error import S3Error

from app.services.storage.base import StorageProvider
from app.services.storage.local_provider import LocalStorageProvider


@pytest.fixture()
def local_provider(tmp_path: Path) -> LocalStorageProvider:
    return LocalStorageProvider(tmp_path / "cloudhide-storage")


def test_local_provider_is_a_storage_provider(local_provider):
    assert isinstance(local_provider, StorageProvider)


def test_local_provider_upload_creates_readable_file(local_provider, tmp_path):
    location = local_provider.upload_file("encrypted/abc.enc", b"secret bytes")

    assert Path(location).exists()
    assert local_provider.download_file("encrypted/abc.enc") == b"secret bytes"


def test_local_provider_file_exists(local_provider):
    assert local_provider.file_exists("carriers/missing.png") is False
    local_provider.upload_file("carriers/present.png", b"png bytes")
    assert local_provider.file_exists("carriers/present.png") is True


def test_local_provider_download_missing_raises(local_provider):
    with pytest.raises(FileNotFoundError):
        local_provider.download_file("does/not/exist.bin")


def test_local_provider_delete_removes_file(local_provider):
    local_provider.upload_file("fragments/f1.frag", b"chunk")
    assert local_provider.file_exists("fragments/f1.frag") is True

    local_provider.delete_file("fragments/f1.frag")
    assert local_provider.file_exists("fragments/f1.frag") is False


def test_local_provider_delete_missing_is_a_noop(local_provider):
    local_provider.delete_file("nothing/here.bin")  # must not raise


def test_local_provider_creates_nested_subdirectories(local_provider):
    local_provider.upload_file("stego/nested/deep.png", b"data")
    assert local_provider.file_exists("stego/nested/deep.png") is True


def _make_mocked_minio_provider(bucket_exists: bool = True):
    with patch("app.services.storage.minio_provider.Minio") as mock_minio_cls:
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = bucket_exists
        mock_minio_cls.return_value = mock_client

        from app.services.storage.minio_provider import MinIOStorageProvider

        provider = MinIOStorageProvider(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket="cloudhide",
            secure=False,
        )
        return provider, mock_client


def test_minio_provider_creates_bucket_if_missing():
    provider, mock_client = _make_mocked_minio_provider(bucket_exists=False)
    mock_client.make_bucket.assert_called_once_with("cloudhide")


def test_minio_provider_skips_bucket_creation_if_present():
    provider, mock_client = _make_mocked_minio_provider(bucket_exists=True)
    mock_client.make_bucket.assert_not_called()


def test_minio_provider_upload_calls_put_object_and_returns_location():
    provider, mock_client = _make_mocked_minio_provider()

    location = provider.upload_file("stego/img1.png", b"stego bytes")

    assert mock_client.put_object.called
    args, kwargs = mock_client.put_object.call_args
    assert args[0] == "cloudhide"
    assert args[1] == "stego/img1.png"
    assert location == "minio://cloudhide/stego/img1.png"


def test_minio_provider_download_translates_s3error_to_file_not_found():
    provider, mock_client = _make_mocked_minio_provider()
    mock_client.get_object.side_effect = S3Error(
        code="NoSuchKey",
        message="not found",
        resource="x",
        request_id="1",
        host_id="1",
        response=None,
    )

    with pytest.raises(FileNotFoundError):
        provider.download_file("stego/missing.png")


def test_minio_provider_file_exists_true_and_false():
    provider, mock_client = _make_mocked_minio_provider()

    mock_client.stat_object.side_effect = None
    assert provider.file_exists("stego/present.png") is True

    mock_client.stat_object.side_effect = S3Error(
        code="NoSuchKey",
        message="not found",
        resource="x",
        request_id="1",
        host_id="1",
        response=None,
    )
    assert provider.file_exists("stego/missing.png") is False
