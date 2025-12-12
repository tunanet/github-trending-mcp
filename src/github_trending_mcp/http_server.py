"""FastAPI 版本的 GitHub Trending HTTP/SSE 服务入口。"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import AsyncIterator, Callable, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

from .fetcher import TrendingService, build_service_from_env
from .models import TrendingRequest
from .validation import build_language_metadata, validate_inputs


def _split_languages(raw_languages: Optional[List[str]]) -> Optional[List[str]]:
    """支持 `?languages=python&languages=go` 或 `?languages=python,go` 形式。"""

    if not raw_languages:
        return None
    normalized: List[str] = []
    for entry in raw_languages:
        if not entry:
            continue
        parts = [segment.strip() for segment in entry.split(",") if segment.strip()]
        normalized.extend(parts)
    return normalized or None


async def _run_fetch(service: TrendingService, request: TrendingRequest):
    """将同步抓取封装成线程池调用，避免阻塞事件循环。"""

    return await run_in_threadpool(service.fetch, request)


def _format_sse(data: dict, event: str = "trending") -> str:
    body = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {body}\n\n"


def _create_stream(
    service: TrendingService,
    request: TrendingRequest,
    interval: Optional[float],
) -> AsyncIterator[str]:
    """根据 interval 确定是单次推送还是定期推送。"""

    async def generator() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    payload = await _run_fetch(service, request)
                except RuntimeError as exc:
                    yield _format_sse({"error": str(exc)}, event="error")
                    break
                else:
                    yield _format_sse(payload.to_dict())
                if interval is None:
                    break
                await asyncio.sleep(interval)
        finally:
            service.close()

    return generator()


def create_app(
    service: Optional[TrendingService] = None,
    service_factory: Optional[Callable[[], TrendingService]] = None,
) -> FastAPI:
    """构建 FastAPI 应用，可通过 factory 为每个请求生成新 service。"""

    if service_factory is None:
        if service is not None:
            service_factory = lambda: service  # 单测或注入时复用
        else:
            service_factory = build_service_from_env

    app = FastAPI(title="GitHub Trending MCP HTTP", version="0.1.0")

    @app.get("/health", response_class=JSONResponse)
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/languages", response_class=JSONResponse)
    def list_languages() -> dict:
        return build_language_metadata()

    @app.get("/trending", response_class=JSONResponse)
    async def get_trending(
        languages: Optional[List[str]] = Query(default=None, description="多值或逗号分隔"),
        limit: Optional[int] = Query(default=None, description="返回数量"),
        timeframe: Optional[str] = Query(default=None, description="daily/weekly/monthly"),
    ) -> dict:
        try:
            request = validate_inputs(_split_languages(languages), limit, timeframe)
        except ValueError as exc:  # 转换成 HTTP 400
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        service = service_factory()
        try:
            response = await _run_fetch(service, request)
            return response.to_dict()
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            service.close()

    @app.get("/trending/stream")
    async def stream_trending(
        languages: Optional[List[str]] = Query(default=None, description="多值或逗号分隔"),
        limit: Optional[int] = Query(default=None),
        timeframe: Optional[str] = Query(default=None),
        enable_refresh: bool = Query(
            default=False,
            description="是否启用周期刷新（默认为否）",
        ),
        interval: Optional[float] = Query(
            default=None,
            gt=0,
            description="刷新间隔（秒），仅在启用周期刷新时生效",
        ),
    ) -> StreamingResponse:
        try:
            request = validate_inputs(_split_languages(languages), limit, timeframe)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        service = service_factory()
        effective_interval = interval if enable_refresh else None
        stream = _create_stream(service, request, effective_interval)
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(stream, media_type="text/event-stream", headers=headers)

    return app


app = create_app()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GitHub Trending HTTP/SSE Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="是否自动重载（开发模式）")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    import uvicorn

    uvicorn.run("github_trending_mcp.http_server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
