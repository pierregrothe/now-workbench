# src/now_workbench/platform/s3.py
# Upload one object to an S3-compatible bucket, signed with AWS Signature Version 4 (ADR-029).
# Author: Pierre Grothe
# Date: 2026-11-07
"""S3 upload.

One signed `PUT` through httpx, so backups need no AWS SDK. The payload's SHA-256 is part of
the signature, so the bucket rejects a body altered in transit. Works with AWS S3 and with
S3-compatible stores (Cloudflare R2, MinIO, Backblaze B2) through a custom endpoint, using
path-style addressing (`<endpoint>/<bucket>/<key>`).
"""

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote, urlsplit

import httpx

from now_workbench.platform.clock import utc_now

__all__ = ["S3Target", "put_object", "sign_v4"]

_ALGORITHM = "AWS4-HMAC-SHA256"
_SERVICE = "s3"
_TIMEOUT = httpx.Timeout(60.0)
# S3 bucket naming rules; a valid name needs no escaping in the path.
_BUCKET = re.compile(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]")
_SIGNED = ("host", "x-amz-content-sha256", "x-amz-date", "content-type")
_AUTHORIZATION = "authorization"
_CONTENT_TYPE = "application/octet-stream"


@dataclass(frozen=True)
class S3Target:
    """Where and as whom to upload.

    Attributes:
        bucket: Bucket name.
        region: Signing region (`auto` for Cloudflare R2).
        access_key_id: Access key id.
        secret_access_key: Secret access key.
        endpoint: Base URL; empty means AWS (`https://s3.<region>.amazonaws.com`).
    """

    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str
    endpoint: str = ""

    def base_url(self) -> str:
        """The endpoint, defaulting to the regional AWS one."""
        return (self.endpoint or f"https://s3.{self.region}.amazonaws.com").rstrip("/")


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _signing_key(secret: str, day: str, region: str) -> bytes:
    key = _hmac(f"AWS4{secret}".encode(), day)
    for part in (region, _SERVICE, "aws4_request"):
        key = _hmac(key, part)
    return key


def sign_v4(
    target: S3Target, method: str, url: str, headers: dict[str, str], payload_hash: str
) -> str:
    """Return the `Authorization` header value for a request.

    Args:
        target: Credentials and region.
        method: HTTP method.
        url: Full URL; its path must already be URI-encoded and it carries no query.
        headers: Every header to sign, `host` and `x-amz-date` included.
        payload_hash: Hex SHA-256 of the body (also sent as `x-amz-content-sha256`).

    Returns:
        The SigV4 authorization string.
    """
    signed = {k.lower(): " ".join(v.split()) for k, v in headers.items()}
    names = sorted(signed)
    canonical = "\n".join(
        [
            method,
            urlsplit(url).path or "/",
            "",
            "".join(f"{n}:{signed[n]}\n" for n in names),
            ";".join(names),
            payload_hash,
        ]
    )
    stamp = signed["x-amz-date"]
    scope = f"{stamp[:8]}/{target.region}/{_SERVICE}/aws4_request"
    to_sign = "\n".join([_ALGORITHM, stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    key = _signing_key(target.secret_access_key, stamp[:8], target.region)
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    return (
        f"{_ALGORITHM} Credential={target.access_key_id}/{scope}, "
        f"SignedHeaders={';'.join(names)}, Signature={signature}"
    )


def put_object(
    target: S3Target,
    key: str,
    body: bytes,
    now: datetime | None = None,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Upload `body` as `key` and return its `s3://` location.

    Args:
        target: Bucket, region, credentials and endpoint.
        key: Object key, e.g. "now-workbench/workbench-20261107T020000Z.db".
        body: The bytes to store.
        now: Signing time (tests); the current UTC time when omitted.
        transport: HTTP transport override (tests).

    Returns:
        "s3://<bucket>/<key>".

    Raises:
        ValueError: The endpoint is not HTTPS, or the bucket name is not valid.
        RuntimeError: The bucket refused the upload (status and reply included).
    """
    base = target.base_url()
    if not base.startswith("https://"):
        raise ValueError(f"S3 endpoint must use https: {base}")
    if not _BUCKET.fullmatch(target.bucket):
        raise ValueError(f"Not a valid S3 bucket name: {target.bucket!r}")
    url = f"{base}/{target.bucket}/{quote(key)}"
    payload_hash = hashlib.sha256(body).hexdigest()
    stamp = (now or utc_now()).strftime("%Y%m%dT%H%M%SZ")
    headers = dict(zip(_SIGNED, (urlsplit(url).netloc, payload_hash, stamp, _CONTENT_TYPE)))
    headers[_AUTHORIZATION] = sign_v4(target, "PUT", url, headers, payload_hash)
    with httpx.Client(timeout=_TIMEOUT, transport=transport) as http:
        res = http.put(url, content=body, headers=headers)
    if res.status_code != 200:
        raise RuntimeError(f"S3 refused the upload ({res.status_code}): {res.text[:300]}")
    return f"s3://{target.bucket}/{key}"
