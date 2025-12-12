"""封装 GitHub Trending 抓取、解析、补全与格式化的核心逻辑。"""

from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

from .constants import (
    CURATED_LANGUAGES,
    DEFAULT_LIMIT,
    DEFAULT_TIMEFRAME,
    GITHUB_API_URL,
    GITHUB_TRENDING_URL,
    MAX_LIMIT,
    SUPPORTED_TIMEFRAMES,
    USER_AGENT,
)
from .models import RepoMetadata, TrendingHTMLRow, TrendingRepository, TrendingRequest, TrendingResponse
from .utils import parse_int

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FetchContext:
    """方便调试或扩展的抓取上下文描述。"""

    languages: List[str]
    timeframe: str
    limit: int


class GitHubAPIClient:
    """GitHub REST API 的轻量封装，按需拉取仓库元数据。"""

    def __init__(self, token: Optional[str] = None, timeout: int = 20) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout

    def fetch_repo(self, owner: str, name: str) -> Optional[RepoMetadata]:
        """根据 owner/name 调用 REST API，失败时返回 None。"""
        url = f"{GITHUB_API_URL}/repos/{owner}/{name}"
        logger.debug("开始拉取仓库详情：%s", url)
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            logger.error("请求 GitHub API 时发生异常 %s/%s：%s", owner, name, exc)
            return None
        if response.status_code != 200:
            logger.warning("请求 GitHub API 失败 %s/%s，状态码：%s", owner, name, response.status_code)
            return None
        data = response.json()
        return RepoMetadata(
            description=data.get("description"),
            stargazers_count=data.get("stargazers_count"),
            forks_count=data.get("forks_count"),
            updated_at=data.get("pushed_at") or data.get("updated_at"),
            html_url=data.get("html_url"),
            default_branch=data.get("default_branch"),
        )

    def close(self) -> None:
        """释放会话资源。"""
        self.session.close()


class TrendingPageClient:
    """负责抓取 Trending 页面 HTML，并解析为结构化结果。"""

    def __init__(self, timeout: int = 20) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.timeout = timeout

    def _build_url(self, language: Optional[str], timeframe: str) -> str:
        """根据语言/时间范围生成 Trending 页面 URL。"""
        safe_lang = (language or "").strip()
        if safe_lang:
            slug = quote(safe_lang, safe="")
            return f"{GITHUB_TRENDING_URL}/{slug}?since={timeframe}"
        return f"{GITHUB_TRENDING_URL}?since={timeframe}"

    def fetch(self, language: Optional[str], timeframe: str) -> List[TrendingHTMLRow]:
        """抓取页面并转换为 TrendingHTMLRow 列表。"""
        url = self._build_url(language, timeframe)
        logger.debug("拉取 Trending 页面：%s", url)
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.error("请求 Trending 页面失败 %s：%s", url, exc)
            raise RuntimeError("GitHub Trending 页面请求失败") from exc
        return self._parse_html(response.text, language, timeframe)

    def _parse_html(self, html: str, language: Optional[str], timeframe: str) -> List[TrendingHTMLRow]:
        """解析 HTML DOM，提取需要的字段。"""
        soup = BeautifulSoup(html, "html.parser")
        repo_sections = soup.select("article.Box-row")
        results: List[TrendingHTMLRow] = []
        for idx, section in enumerate(repo_sections, start=1):
            header = section.select_one("h2.h3 a")
            if not header:
                continue
            repo_identifier = header.get_text(strip=True).replace(" ", "")
            if "/" not in repo_identifier:
                continue
            owner, name = [part.strip() for part in repo_identifier.split("/")[:2]]
            repo_url = f"https://github.com/{owner}/{name}"
            description_el = section.select_one("p")
            description = description_el.get_text(strip=True) if description_el else None
            primary_language_el = section.select_one('[itemprop="programmingLanguage"]')
            primary_language = primary_language_el.get_text(strip=True) if primary_language_el else None
            stats_links = section.select("a.Link--muted")
            total_stars = None
            forks = None
            for link in stats_links:
                href = link.get("href", "")
                if href.endswith("/stargazers"):
                    total_stars = parse_int(link.get_text(strip=True))
                elif any(segment in href for segment in ("/forks", "/network/members")):
                    forks = parse_int(link.get_text(strip=True))
            delta_el = section.select_one("span.d-inline-block.float-sm-right") or section.select_one("span.color-fg-muted.text-normal")
            delta_text = delta_el.get_text(strip=True) if delta_el else None
            stars_in_period = None
            if delta_text:
                stars_in_period = parse_int(delta_text)
            results.append(
                TrendingHTMLRow(
                    owner=owner,
                    name=name,
                    rank_in_context=idx,
                    language_context=language,
                    description=description,
                    primary_language=primary_language,
                    total_stars=total_stars,
                    forks=forks,
                    stars_in_period=stars_in_period,
                    period_text=delta_text,
                    repo_url=repo_url,
                    timeframe=timeframe,
                )
            )
        return results

    def close(self) -> None:
        """关闭 HTTP 会话。"""
        self.session.close()


class TrendingService:
    """将 Trending 页面解析与 REST API 数据融合，输出标准结构。"""

    def __init__(self, token: Optional[str] = None) -> None:
        self.page_client = TrendingPageClient()
        self.api_client = GitHubAPIClient(token=token)

    def fetch(self, request: TrendingRequest) -> TrendingResponse:
        """执行抓取流程：校验参数 -> 抓取 -> 去重 -> 补全 -> 输出。"""
        timeframe = (request.timeframe or DEFAULT_TIMEFRAME).lower()
        if timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"不支持的时间窗口 '{request.timeframe}'，允许值：{SUPPORTED_TIMEFRAMES}")
        requested_limit = request.limit or DEFAULT_LIMIT
        if requested_limit <= 0:
            raise ValueError("limit 必须是正整数")
        per_language_limit = min(requested_limit, MAX_LIMIT)
        normalized_languages = [lang.lower() for lang in request.languages if lang]
        languages_to_fetch: List[Optional[str]] = []
        if normalized_languages:
            if "all" in normalized_languages:
                languages_to_fetch = [None]
            else:
                for language in normalized_languages:
                    if language not in CURATED_LANGUAGES:
                        raise ValueError(f"语言 '{language}' 不在策划的支持列表中")
                    languages_to_fetch.append(language)
        else:
            languages_to_fetch.append(None)
        # all_mode 表示不区分语言，limit 即总条数；否则按语言配额抓取，最后用 overall_limit 限制绝对上限。
        is_all_mode = len(languages_to_fetch) == 1 and languages_to_fetch[0] is None
        intended_total = per_language_limit if is_all_mode else per_language_limit * len(languages_to_fetch)
        overall_limit = min(intended_total, MAX_LIMIT if is_all_mode else MAX_LIMIT * len(languages_to_fetch))
        remaining = overall_limit
        aggregated: "OrderedDict[str, TrendingHTMLRow]" = OrderedDict()
        language_rows: Dict[Optional[str], List[TrendingHTMLRow]] = {}
        for idx, language in enumerate(languages_to_fetch):
            if remaining <= 0:
                break
            rows = self.page_client.fetch(language, timeframe)
            language_rows[language] = rows
            taken = 0
            for row in rows:
                if not is_all_mode and taken >= per_language_limit:
                    break
                key = f"{row.owner.lower()}/{row.name.lower()}"
                if key in aggregated:
                    continue
                aggregated[key] = row
                taken += 1
                remaining -= 1
                if remaining <= 0:
                    break
            if len(languages_to_fetch) > 1 and not is_all_mode and remaining > 0 and idx < len(languages_to_fetch) - 1:
                time.sleep(0.5)
        # 第二轮用于补齐“配额不足”的语言，但仍会检查每种语言的上限，避免单一语言无限扩张。
        if remaining > 0 and not is_all_mode:
            for language in languages_to_fetch:
                if remaining <= 0:
                    break
                rows = language_rows.get(language)
                if not rows:
                    continue
                taken = sum(1 for row in aggregated.values() if row.language_context == language)
                for row in rows:
                    if taken >= per_language_limit:
                        break
                    key = f"{row.owner.lower()}/{row.name.lower()}"
                    if key in aggregated:
                        continue
                    aggregated[key] = row
                    taken += 1
                    remaining -= 1
                    if remaining <= 0:
                        break
        repos: List[TrendingRepository] = []
        for idx, row in enumerate(aggregated.values(), start=1):
            metadata = self.api_client.fetch_repo(row.owner, row.name)
            description = metadata.description if metadata and metadata.description else row.description
            repo_url = metadata.html_url if metadata and metadata.html_url else row.repo_url
            total_stars = metadata.stargazers_count if metadata and metadata.stargazers_count is not None else row.total_stars
            forks = metadata.forks_count if metadata and metadata.forks_count is not None else row.forks
            updated_at = metadata.updated_at if metadata else None
            # 当语言参数为 all 时，language_context 为空；此处尝试回填 primary_language 方便客户端识别。
            effective_language = row.language_context or row.primary_language
            if effective_language is None and is_all_mode:
                effective_language = "all"
            repos.append(
                TrendingRepository(
                    rank=idx,
                    owner=row.owner,
                    name=row.name,
                    repo_url=repo_url,
                    timeframe=row.timeframe,
                    rank_in_context=row.rank_in_context,
                    language_context=effective_language,
                    description=description,
                    primary_language=row.primary_language,
                    total_stars=total_stars,
                    forks=forks,
                    stars_in_period=row.stars_in_period,
                    period_text=row.period_text,
                    updated_at=updated_at,
                )
            )
            if len(repos) >= overall_limit:
                break
        # metadata_block 中记录原始请求、有效配额与模式，方便客户端调试/展示。
        metadata_block: Dict[str, Any] = {
            "timeframe": timeframe,
            "languages": normalized_languages or ["all"],
            "retrieved": len(repos),
            "limit_mode": "shared" if is_all_mode else "per_language",
            "requested_limit": requested_limit,
        }
        if is_all_mode:
            metadata_block["limit"] = per_language_limit
        else:
            metadata_block["limit_per_language"] = per_language_limit
            metadata_block["limit_total"] = intended_total
        metadata_block["effective_limit"] = overall_limit
        return TrendingResponse(repos=repos, metadata=metadata_block)

    def close(self) -> None:
        """确保底层 HTTP 会话被释放。"""
        self.page_client.close()
        self.api_client.close()

def build_service_from_env() -> TrendingService:
    """从环境变量读取 token，构造带鉴权的服务实例。"""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")
    return TrendingService(token=token)
