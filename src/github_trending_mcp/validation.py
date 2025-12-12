"""集中处理参数校验与共享元数据，供 MCP 与 HTTP 端共同使用。"""

from __future__ import annotations

from typing import Dict, List, Optional

from .constants import (
    CURATED_LANGUAGES,
    DEFAULT_LIMIT,
    DEFAULT_TIMEFRAME,
    MAX_LIMIT,
    SUPPORTED_TIMEFRAMES,
)
from .models import TrendingRequest


def validate_inputs(
    languages: Optional[List[str]],
    limit: Optional[int],
    timeframe: Optional[str],
) -> TrendingRequest:
    """校验语言/数量/时间窗口并转换成 TrendingRequest。"""

    langs = languages or []
    cleaned = [language.strip().lower() for language in langs if language]
    if limit is not None:
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if limit > MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {MAX_LIMIT}")
    tf = (timeframe or DEFAULT_TIMEFRAME).lower()
    if tf not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"Timeframe must be one of {SUPPORTED_TIMEFRAMES}")
    for lang in cleaned:
        if lang != "all" and lang not in CURATED_LANGUAGES:
            raise ValueError(f"Language '{lang}' is not in the curated supported list")
    return TrendingRequest(languages=cleaned, limit=limit or DEFAULT_LIMIT, timeframe=tf)


def build_language_metadata() -> Dict[str, object]:
    """提供语言默认值与支持列表，便于客户端展示。"""

    return {
        "default": "all",
        "supported": CURATED_LANGUAGES,
        "notes": "When no language is supplied the server queries for all languages.",
    }
