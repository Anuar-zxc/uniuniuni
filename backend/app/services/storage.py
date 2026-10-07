"""Object storage abstraction (local disk or S3-compatible) with optional at-rest encryption."""

import uuid
from pathlib import Path

from app.core.config import get_settings


class Storage:
    def __init__(self) -> None:
        s = get_settings()
        self.backend = s.storage_backend
        self._fernet = None
        if s.file_encryption_key:
            from cryptography.fernet import Fernet

            self._fernet = Fernet(s.file_encryption_key.encode())
        if self.backend == "none":
            return
        if self.backend == "s3":
            import boto3

            self._s3 = boto3.client(
                "s3", endpoint_url=s.s3_endpoint_url, aws_access_key_id=s.s3_access_key,
                aws_secret_access_key=s.s3_secret_key, region_name=s.s3_region,
            )
            self._bucket = s.s3_bucket
        else:
            self._root = Path(s.storage_local_dir)
            self._root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, prefix: str, ext: str) -> str | None:
        if self.backend == "none":
            return None  # only the extracted text is kept
        key = f"{prefix}/{uuid.uuid4().hex}{ext}"
        payload = self._fernet.encrypt(data) if self._fernet else data
        if self.backend == "s3":
            self._s3.put_object(Bucket=self._bucket, Key=key, Body=payload)
        else:
            path = self._root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        return key

    def load(self, key: str) -> bytes:
        if self.backend == "none":
            raise FileNotFoundError(key)
        if self.backend == "s3":
            payload = self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read()
        else:
            payload = (self._root / key).read_bytes()
        return self._fernet.decrypt(payload) if self._fernet else payload

    def delete(self, key: str) -> None:
        if self.backend == "none":
            return
        try:
            if self.backend == "s3":
                self._s3.delete_object(Bucket=self._bucket, Key=key)
            else:
                (self._root / key).unlink(missing_ok=True)
        except Exception:  # pragma: no cover - best effort
            pass


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage
