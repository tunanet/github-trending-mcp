"""GitHub Trending MCP 服务器的对外包入口。"""

from .fetcher import TrendingService, build_service_from_env

__all__ = ["TrendingService", "build_service_from_env"]
