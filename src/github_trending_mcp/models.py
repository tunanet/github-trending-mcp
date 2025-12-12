"""定义 GitHub Trending 聚合时会用到的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class TrendingHTMLRow:
    """描述从 Trending HTML 页面解析出的一条仓库信息。"""

    owner: str
    name: str
    rank_in_context: int
    language_context: Optional[str]
    description: Optional[str]
    primary_language: Optional[str]
    total_stars: Optional[int]
    forks: Optional[int]
    stars_in_period: Optional[int]
    period_text: Optional[str]
    repo_url: str
    timeframe: str


@dataclass(slots=True)
class RepoMetadata:
    """GitHub REST API 返回的仓库补充信息。"""

    description: Optional[str]
    stargazers_count: Optional[int]
    forks_count: Optional[int]
    updated_at: Optional[str]
    html_url: Optional[str]
    default_branch: Optional[str] = None


@dataclass(slots=True)
class TrendingRepository:
    """最终提供给 MCP 客户端的标准结构。"""

    rank: int
    owner: str
    name: str
    repo_url: str
    timeframe: str
    rank_in_context: int
    language_context: Optional[str]
    description: Optional[str]
    primary_language: Optional[str]
    total_stars: Optional[int]
    forks: Optional[int]
    stars_in_period: Optional[int]
    period_text: Optional[str]
    updated_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """转为 JSON 友好的字典结构。"""
        effective_language = self.language_context or self.primary_language or "all"
        return {
            "rank": self.rank,
            "owner": self.owner,
            "name": self.name,
            "repo_url": self.repo_url,
            "timeframe": self.timeframe,
            "rank_in_context": self.rank_in_context,
            "language_context": effective_language,
            "description": self.description,
            "primary_language": self.primary_language,
            "total_stars": self.total_stars,
            "forks": self.forks,
            "stars_in_timeframe": self.stars_in_period,
            "timeframe_delta_label": self.period_text,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class TrendingRequest:
    """描述 MCP 工具请求时可传入的参数。"""

    languages: List[str] = field(default_factory=list)
    limit: int = 10
    timeframe: str = "daily"

    def normalized_languages(self) -> List[str]:
        """对语言参数做去空格、小写等标准化。"""
        return [language.strip().lower() for language in self.languages if language]


@dataclass(slots=True)
class TrendingResponse:
    """MCP 工具的顶层响应模型。"""

    repos: List[TrendingRepository]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转成字典，方便 JSON 序列化。"""
        return {
            "metadata": self.metadata,
            "repos": [repo.to_dict() for repo in self.repos],
        }
