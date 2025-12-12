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
            raise ValueError("limit 必须大于 0")
        if limit > MAX_LIMIT:
            raise ValueError(f"limit 不可超过 {MAX_LIMIT}")
    tf = (timeframe or DEFAULT_TIMEFRAME).lower()
    if tf not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"时间窗口必须属于 {SUPPORTED_TIMEFRAMES}")
    for lang in cleaned:
        if lang != "all" and lang not in CURATED_LANGUAGES:
            raise ValueError(f"语言 '{lang}' 不在策划的支持列表中")
    return TrendingRequest(languages=cleaned, limit=limit or DEFAULT_LIMIT, timeframe=tf)


def build_language_metadata() -> Dict[str, object]:
    """提供语言默认值与支持列表，便于客户端展示。"""

    return {
        "default": "all",
        "supported": tuple(CURATED_LANGUAGES),
        "notes": "若未指定语言则默认抓取所有语言的 Trending。",
    }
