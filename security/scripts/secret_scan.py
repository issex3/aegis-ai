"""Dependency-free secret scan for the repository. Exit code 1 when a likely secret is found.

Usage: python security/scripts/secret_scan.py [root]
CI should additionally run a maintained scanner (gitleaks) against git history.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {"node_modules", ".venv", "venv", ".next", "__pycache__", ".pytest_cache", ".git", "coverage"}
SKIP_FILES = {".env"}
SKIP_SUFFIXES = {".db", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".woff", ".woff2", ".lock"}
PATTERNS = {
    "stripe_live_key": re.compile(r"sk_live_[A-Za-z0-9]{16,}"),
    "stripe_test_key": re.compile(r"sk_test_[A-Za-z0-9]{16,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "openai_key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{32,}"),
    "fernet_key_assignment": re.compile(r"ENCRYPTION_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{43}=['\"]?"),
    "password_assignment": re.compile(r"(?i)\b(?:password|passwd|secret|api_key)\s*[:=]\s*['\"][^'\"\s{}$]{12,}['\"]"),
}
ALLOWLIST = (
    re.compile(r"replace-with|change-me|placeholder|example", re.IGNORECASE),
    re.compile(r"secret-scan:\s*allow-test-fixture"),
)


def scan(root: Path) -> list[tuple[str, int, str]]:
    hits = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SKIP_FILES or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line) and not any(allowed.search(line) for allowed in ALLOWLIST):
                    hits.append((str(path.relative_to(root)), number, name))
    return hits


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    hits = [hit for hit in scan(root) if not hit[0].replace("\\", "/").startswith("security/scripts/secret_scan.py")]
    for file, line, name in hits:
        print(f"{file}:{line}: possible {name}")
    print(f"secret scan: {len(hits)} finding(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
