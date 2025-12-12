# GitHub Trending Repos MCP Server

本项目实现了一个 [Model Context Protocol](https://modelcontextprotocol.io/) 服务器，用于聚合 [GitHub Trending](https://github.com/trending) 上的热门仓库，并以结构化 JSON 输出，适合内容聚合或情报调研等场景。

## 功能亮点

- **精准抓取**：直接解析 Trending 页面卡片，再通过 GitHub REST API 丰富描述、星标、fork 与更新时间等信息。
- **灵活筛选**：支持多语言多选、时间范围（`daily`/`weekly`/`monthly`）以及返回数量（默认 10，最大 100）。
- **JSON 优先**：MCP 工具默认返回 JSON 文本，方便下游系统直接消费。
- **安全限流**：内置限额与轻量延时，避免在抓取时对 GitHub 造成压力。
- **容器化部署**：提供 Dockerfile，可快速在任何环境中运行。

## 安装

```bash
pip install -e .
```

> **提示**：`modelcontextprotocol` 提供 MCP 运行时，安装本项目时会自动拉取，请确保位于可联网环境。

## 配置项

| 配置项 | 说明 | 默认值 |
| ------ | ---- | ------ |
| `languages` | 选择一个或多个语言（如 `python javascript go`），使用 `all` 或留空表示所有语言。 | `all` |
| `limit` | 返回热门仓库数量，范围 1~100。 | `10` |
| `timeframe` | Trending 时间窗口，支持 `daily`、`weekly`、`monthly`。 | `daily` |
| `GITHUB_TOKEN` | 可选，提供后可提升 GitHub API 速率限制。 | 未设置 |

支持语言列表可以通过 `list_trending_languages` 工具或 CLI 查询：

```bash
python -m github_trending_mcp.server --cli --languages all --limit 1 --timeframe daily
```

## 运行 MCP 服务器

```bash
python -m github_trending_mcp.server
```

该命令会启动一个 MCP stdio 服务器，暴露以下工具：

- `fetch_trending_repositories`：按配置返回 Trending 仓库列表（JSON）。
- `list_trending_languages`：返回策划语种与默认信息。

## CLI 调试模式

为了便于排查或本地定时抓取，可直接运行 CLI：

```bash
python -m github_trending_mcp.server --cli --languages python go --limit 20 --timeframe weekly
```

命令会在终端输出 JSON，其中包含排名、趋势增量、星标、fork、更新时间等字段。

## HTTP / SSE 服务

除了 stdio MCP，还提供 FastAPI 实现的 HTTP 接口：

```bash
python -m github_trending_mcp.http_server --host 0.0.0.0 --port 8000
# 或使用入口脚本
github-trending-mcp-http --host 0.0.0.0 --port 8000
```

- 拉取一次数据：

  ```bash
  curl 'http://localhost:8000/trending?languages=python,go&limit=10&timeframe=weekly'
  ```

- 订阅 SSE 流（默认只推送一次，可通过 `interval` 设置秒级刷新）：

  ```bash
  # 持续每 60 秒推送一次
  curl -N 'http://localhost:8000/trending/stream?languages=python&limit=5'
  ```

  默认只推送一次。如需周期刷新，可加 `enable_refresh=true&interval=60` 表示每分钟推送一次：

  ```bash
  curl -N 'http://localhost:8000/trending/stream?languages=python&limit=5&enable_refresh=true&interval=60'
  ```

还可访问 `GET /languages` 查看语言列表；`GET /health` 可用于探活。

## Docker 部署

```bash
docker build -t github-trending-mcp .
docker run --rm -e GITHUB_TOKEN=ghp_xxx github-trending-mcp

# 作为 HTTP/SSE 服务运行
docker run --rm -p 8000:8000 -e GITHUB_TOKEN=ghp_xxx github-trending-mcp \
  python -m github_trending_mcp.http_server --host 0.0.0.0 --port 8000
```

在对接 MCP 兼容的宿主（如 Claude Desktop、Cursor 等）时，请根据各平台要求映射 stdin/stdout。

## 开发说明

- 需要 Python ≥ 3.10
- 依赖 `requests`、`beautifulsoup4`、`modelcontextprotocol`、`fastapi`、`uvicorn`
- 如需增加测试，可使用 `pytest`

## 限制

- GitHub Trending 每个语言/时间窗口仅提供一页数据，因此虽然 `limit` 上限为 100，最终返回数量取决于实际页面结果。
- 未提供 GitHub Token 时，REST API 调用会受每小时 60 次限制。如需长时间抓取，请配置令牌。
