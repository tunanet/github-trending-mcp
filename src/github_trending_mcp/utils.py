"""工具函数模块，供 GitHub Trending MCP 服务器复用。"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


# 过滤除数字外的所有字符，便于解析带单位的星标/增量。
_NUMBER_CLEAN_RE = re.compile(r"[^0-9]")


def parse_int(value: Optional[str]) -> Optional[int]:
    """将字符串中的数字部分提取出来再转成 int，兼容多种格式。"""

    if not value:
        return None
    cleaned = _NUMBER_CLEAN_RE.sub("", value)
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        logger.debug("Failed to parse integer from %s", value)
        return None


def snake_case(text: str) -> str:
    """简单的 snake_case 转换，当前暂未使用，保留以备扩展。"""
    return text.lower().replace(" ", "_")


class LimitedOrderedDict(Dict[str, Any]):
    """带容量限制的有序字典，用于去重时保留插入顺序。"""

    def __init__(self, max_items: int) -> None:
        super().__init__()
        self._max_items = max_items

    def add(self, key: str, value: Any) -> bool:
        """若未超过容量则插入新的键值，返回是否成功。"""
        if key in self:
            return False
        if len(self) >= self._max_items:
            return False
        self[key] = value
        return True

    def values_list(self) -> List[Any]:
        """以列表形式返回当前的值集合。"""
        return list(self.values())
