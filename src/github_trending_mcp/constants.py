"""GitHub Trending MCP 服务器的核心常量，便于全局复用。"""

from __future__ import annotations

# 策划后的语言列表，过滤掉不常用或噪声较大的语言，方便前端展示。
CURATED_LANGUAGES: list[str] = [
    "all",
    "python",
    "javascript",
    "typescript",
    "go",
    "java",
    "c",
    "c++",
    "c#",
    "rust",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "dart",
    "css",
    "shell",
    "haskell",
    "elixir",
    "clojure",
    "r",
    "perl",
    "objective-c",
]

# 支持的时间窗口
SUPPORTED_TIMEFRAMES: tuple[str, ...] = ("daily", "weekly", "monthly")
# 默认时间窗口
DEFAULT_TIMEFRAME = "daily"
# 默认返回数量
DEFAULT_LIMIT = 10
# 最大返回数量，避免频繁请求
MAX_LIMIT = 100
# GitHub Trending 页面入口
GITHUB_TRENDING_URL = "https://github.com/trending"
# GitHub REST API 入口
GITHUB_API_URL = "https://api.github.com"
# 统一的 User-Agent，友好表明来源
USER_AGENT = "GitHub-Trending-MCP/0.1 (+https://github.com)"
