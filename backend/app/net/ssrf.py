"""Strict checks for user-supplied agent endpoints.

Validation happens before connect. The TCP connection is opened to a previously
resolved public address with TLS SNI and certificate verification against the
original hostname, so DNS rebinding after validation cannot steer the socket
onto a private address. socket.getaddrinfo is never patched process-wide.
"""

from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 262_144
ALLOWED_PORT = 443
BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}
_ORIGINAL_GETADDRINFO = socket.getaddrinfo


class OutboundBlocked(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ValidatedTarget:
    url: str
    host: str
    port: int
    addresses: tuple[str, ...]


def _ip_blocked(raw: str) -> bool:
    try:
        address = ipaddress.ip_address(raw.split("%", 1)[0])
    except ValueError:
        return True
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or address in ipaddress.ip_network("169.254.0.0/16")
        or address in ipaddress.ip_network("0.0.0.0/8")
    )


def _literal_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    candidate = host.strip("[]")
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        pass
    if re.fullmatch(r"\d{1,10}", candidate):
        try:
            return ipaddress.ip_address(int(candidate))
        except ValueError:
            return None
    if re.fullmatch(r"0x[0-9a-fA-F]{1,8}", candidate):
        try:
            return ipaddress.ip_address(int(candidate, 16))
        except ValueError:
            return None
    if re.fullmatch(r"(\d{1,4}\.){3}\d{1,4}", candidate):
        parts: list[int] = []
        for part in candidate.split("."):
            base = 8 if part.startswith("0") and len(part) > 1 else 10
            try:
                parts.append(int(part, base))
            except ValueError:
                return None
        try:
            return ipaddress.ip_address(".".join(str(part) for part in parts))
        except ValueError:
            return None
    return None


def validate_outbound_url(url: str) -> ValidatedTarget:
    if not url or any(character in url for character in (" ", "\n", "\r", "\\", "@")):
        raise OutboundBlocked("The endpoint URL is not allowed.")
    parsed = urlsplit(url.strip())
    if parsed.scheme != "https":
        raise OutboundBlocked("Agent endpoints must use HTTPS.")
    if parsed.username or parsed.password:
        raise OutboundBlocked("The endpoint URL is not allowed.")
    host = parsed.hostname
    if not host or host.endswith("."):
        raise OutboundBlocked("The endpoint host is not allowed.")
    lowered = host.lower().rstrip(".")
    if lowered in BLOCKED_HOSTS or lowered.endswith(".localhost") or lowered.endswith(".internal"):
        raise OutboundBlocked("The endpoint host is not allowed.")
    port = parsed.port or ALLOWED_PORT
    if port != ALLOWED_PORT:
        raise OutboundBlocked("Only port 443 is allowed for agent endpoints.")
    literal = _literal_ip(lowered)
    if literal is not None and _ip_blocked(str(literal)):
        raise OutboundBlocked("The endpoint address is not publicly routable.")
    try:
        infos = _ORIGINAL_GETADDRINFO(lowered, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise OutboundBlocked("The endpoint host could not be resolved.") from exc
    if not infos:
        raise OutboundBlocked("The endpoint host could not be resolved.")
    addresses: list[str] = []
    for info in infos:
        ip = info[4][0]
        if _ip_blocked(ip):
            raise OutboundBlocked("The endpoint address is not publicly routable.")
        if ip not in addresses:
            addresses.append(ip)
    return ValidatedTarget(url=url.strip(), host=lowered, port=port, addresses=tuple(addresses))


def outbound_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: bytes,
    timeout: float,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> tuple[int, bytes]:
    """Validate the destination, pin the resolved IP, block redirects, and cap the body."""
    if len(body) > 65_536:
        raise OutboundBlocked("The outbound request is too large.")
    target = validate_outbound_url(url)
    timeout = min(max(timeout, 1), 60)
    parsed = urlsplit(target.url)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    request_headers = {key: value for key, value in headers.items()}
    request_headers.setdefault("Host", target.host)
    request_headers.setdefault("Connection", "close")
    context = ssl.create_default_context()
    last_error: Exception | None = None
    for address in target.addresses:
        if _ip_blocked(address):
            continue
        sock = None
        try:
            sock = socket.create_connection((address, target.port), timeout=timeout)
            ssock = context.wrap_socket(sock, server_hostname=target.host)
            sock = None
            try:
                connection = http.client.HTTPSConnection(target.host, target.port, timeout=timeout, context=context)
                connection.sock = ssock
                connection.request(method, path, body=body, headers=request_headers)
                response = connection.getresponse()
                if response.status in {301, 302, 303, 307, 308}:
                    raise OutboundBlocked("Redirects are not followed for agent endpoints.")
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise OutboundBlocked("The agent response exceeded the size limit.")
                    chunks.append(chunk)
                status = response.status
                connection.close()
                return status, b"".join(chunks)
            finally:
                ssock.close()
        except OutboundBlocked:
            raise
        except OSError as exc:
            last_error = exc
            if sock is not None:
                sock.close()
            continue
    raise OutboundBlocked("The endpoint could not be reached.") from last_error
