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

try:  # pragma: no cover - 尽力加载的可选依赖
    try:
        from mcp.server.fastmcp import FastMCPServer  # type: ignore[attr-defined]
    except ImportError:  # 若仅存在 FastMCP 类名则降级使用
        from mcp.server.fastmcp import FastMCP as FastMCPServer  # type: ignore
except Exception:  # pragma: no cover - 全量捕获避免运行期失败
    FastMCPServer = None  # type: ignore


def _format_json(data: Dict[str, Any]) -> str:
    """格式化 JSON，便于 CLI 或 TextContent 输出。"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _register_tools(server: "FastMCPServer") -> None:
    """在 FastMCPServer 上挂载工具实现。"""
    service = build_service_from_env()

    @server.tool(
        name="fetch_trending_repositories",
        description="返回 GitHub Trending 热门仓库的结构化 JSON 数据。"
    )
    def fetch_trending_tool(
        languages: Optional[List[str]] = None,
        limit: Optional[int] = None,
        timeframe: Optional[str] = None,
    ) -> Dict[str, Any]:
        request = validate_inputs(languages, limit, timeframe)
        response = service.fetch(request)
        return response.to_dict()

    @server.tool(
        name="list_trending_languages",
        description="列出服务器策划支持的编程语言。"
    )
    def list_languages_tool() -> Dict[str, Any]:
        return build_language_metadata()


def run_server(args: argparse.Namespace) -> None:
    """启动 MCP 服务器，可切换 stdio、SSE 或 Streamable HTTP。"""
    if FastMCPServer is None:
        raise RuntimeError(
            "运行 MCP 服务器需要先安装 'modelcontextprotocol'，可执行 `pip install modelcontextprotocol`。"
        )
    logging.basicConfig(level=logging.INFO)
    server = FastMCPServer(
        "github-trending-repos-mcp",
        host=args.host,
        port=args.port,
        mount_path=args.mount_path,
        sse_path=args.sse_path,
        message_path=args.message_path,
        streamable_http_path=args.streamable_http_path,
    )
    _register_tools(server)
    server.run(transport=args.transport)


def run_cli(args: argparse.Namespace) -> None:
    """在不接入 MCP 宿主时，直接打印 JSON 到终端。"""
    service = build_service_from_env()
    request = validate_inputs(args.languages, args.limit, args.timeframe)
    response = service.fetch(request)
    print(_format_json(response.to_dict()))


def build_arg_parser() -> argparse.ArgumentParser:
    """构建统一的 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(description="GitHub Trending MCP 服务器")
    parser.add_argument("--languages", nargs="*", help="筛选的语言列表（以空格分隔）")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="需要返回的仓库数量")
    parser.add_argument(
        "--timeframe",
        default=DEFAULT_TIMEFRAME,
        choices=SUPPORTED_TIMEFRAMES,
        help="GitHub Trending 使用的时间窗口",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="以 CLI 模式运行并直接输出 JSON，而非启动 MCP 服务器",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="运行 MCP 服务器时使用的传输协议",
    )
    parser.add_argument("--host", default="127.0.0.1", help="供 MCP HTTP 传输监听的主机地址")
    parser.add_argument("--port", type=int, default=8000, help="供 MCP HTTP 传输监听的端口")
    parser.add_argument(
        "--mount-path",
        default="/",
        help="SSE 传输的可选路径前缀（便于挂载到反向代理）",
    )
    parser.add_argument("--sse-path", default="/sse", help="供 MCP 客户端连接的 SSE 流路径")
    parser.add_argument("--message-path", default="/messages/", help="SSE 传输使用的消息 POST 路径")
    parser.add_argument(
        "--streamable-http-path",
        default="/mcp",
        help="使用 streamable-http 传输时的 HTTP Endpoint 路径",
    )
    return parser


def main() -> None:
    """根据 --cli 开关切换 CLI 或 MCP 运行模式。"""
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.cli:
        run_cli(args)
    else:
        run_server(args)


if __name__ == "__main__":
    main()
