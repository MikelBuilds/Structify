"""Private Cloudflare R2 objects; no permanent local storage."""
from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import quote
from uuid import uuid4

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from app.config import settings


def new_storage_key(filename):
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename.replace("\\", "/").rsplit("/", 1)[-1])
    return f"documents/{uuid4()}/{safe_name[:180] or 'document.pdf'}"


def content_disposition(filename):
    return "inline; filename*=UTF-8''" + quote(filename, safe="")


class R2Storage:
    def __init__(self):
        settings.validate_storage()
        self.bucket = settings.R2_BUCKET_NAME
        self.client = boto3.client(
            "s3", endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4", connect_timeout=10, read_timeout=60,
                          retries={"max_attempts": 2, "mode": "standard"},
                          request_checksum_calculation="when_required",
                          response_checksum_validation="when_required"),
        )

    def upload_pdf(self, path, key, filename):
        with Path(path).open("rb") as body:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body,
                                   ContentType="application/pdf",
                                   ContentDisposition=content_disposition(filename))

    def download_pdf(self, key, path):
        self.client.download_file(self.bucket, key, str(path),
                                  Config=TransferConfig(use_threads=False))

    def signed_pdf_url(self, key, filename):
        # Report missing objects through the existing API before redirecting.
        self.client.head_object(Bucket=self.bucket, Key=key)
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key,
                                  "ResponseContentType": "application/pdf",
                                  "ResponseContentDisposition": content_disposition(filename)},
            ExpiresIn=300,
        )


@lru_cache(maxsize=1)
def get_storage():
    return R2Storage()
