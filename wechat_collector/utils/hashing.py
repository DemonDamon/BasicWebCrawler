"""正文 content_hash 计算。"""

from __future__ import annotations

import hashlib
import re


def compute_content_hash(content_text: str | None) -> str | None:
    if not content_text:
        return None
    normalized = re.sub(r"\s+", " ", content_text.strip())
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
