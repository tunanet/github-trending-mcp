"""GitHub Trending Repos MCP 服务器的入口与工具定义。"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_LIMIT, DEFAULT_TIMEFRAME, SUPPORTED_TIMEFRAMES
from .fetcher import build_service_from_env
from .validation import build_language_metadata, validate_inputs

logger = logging.getLogger(__name__)

try:  # pragma: no cover - best-effort optional dependency
    from mcp.server.fastmcp import FastMCPServer
    from mcp.types import TextContent
except Exception:  # pragma: no cover
    FastMCPServer = None  # type: ignore
    TextContent = None  # type: ignore


def _format_json(data: Dict[str, Any]) -> str:
    """格式化 JSON，便于 CLI 或 TextContent 输出。"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _register_tools(server: "FastMCPServer") -> None:
    """在 FastMCPServer 上挂载工具实现。"""
    service = build_service_from_env()

    @server.tool(
        name="fetch_trending_repositories",
        description="Return GitHub Trending repositories as structured JSON."
    )
    def fetch_trending_tool(
        languages: Optional[List[str]] = None,
        limit: Optional[int] = None,
        timeframe: Optional[str] = None,
    ) -> List[Any]:
        request = validate_inputs(languages, limit, timeframe)
        response = service.fetch(request)
        payload = response.to_dict()
        assert TextContent is not None
        return [TextContent(type="text", text=_format_json(payload))]

    @server.tool(
        name="list_trending_languages",
        description="List curated programming languages supported by the GitHub Trending server."
    )
    def list_languages_tool() -> List[Any]:
        payload = build_language_metadata()
        assert TextContent is not None
        return [TextContent(type="text", text=_format_json(payload))]


def run_server() -> None:
    """启动 stdio MCP 服务器。"""
    if FastMCPServer is None:
        raise RuntimeError(
            "The 'modelcontextprotocol' package is required to expose the MCP server. "
            "Install it with `pip install modelcontextprotocol`."
        )
    logging.basicConfig(level=logging.INFO)
    server = FastMCPServer("github-trending-repos-mcp")
    _register_tools(server)
    server.run()


def run_cli(args: argparse.Namespace) -> None:
    """在不接入 MCP 宿主时，直接打印 JSON 到终端。"""
    service = build_service_from_env()
    request = validate_inputs(args.languages, args.limit, args.timeframe)
    response = service.fetch(request)
    print(_format_json(response.to_dict()))


def build_arg_parser() -> argparse.ArgumentParser:
    """构建统一的 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(description="GitHub Trending MCP Server")
    parser.add_argument("--languages", nargs="*", help="Languages to filter (space separated)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Number of repos to fetch")
    parser.add_argument(
        "--timeframe",
        default=DEFAULT_TIMEFRAME,
        choices=SUPPORTED_TIMEFRAMES,
        help="GitHub Trending time window",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode and print JSON instead of starting the MCP server",
    )
    return parser


def main() -> None:
    """根据 --cli 开关切换 CLI 或 MCP 运行模式。"""
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.cli:
        run_cli(args)
    else:
        run_server()


if __name__ == "__main__":
    main()
