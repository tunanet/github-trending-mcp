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
| `languages` | 选择一个或多个语言（如 `python javascript go`），使用 `all` 或留空表示所有语言。当前支持：`python`、`javascript`、`typescript`、`go`、`java`、`c`、`c++`、`c#`、`rust`、`ruby`、`php`、`swift`、`kotlin`、`scala`、`dart`、`css`、`shell`、`haskell`、`elixir`、`clojure`、`r`、`perl`、`objective-c`。 | `all` |
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

### 对外暴露 MCP 工具（SSE / HTTP 传输）

`FastMCP` 同时内置了 SSE 与 Streamable HTTP 传输层，方便在 n8n、Claude Desktop Remote MCP 等只能通过 URL 调用的客户端中使用本工具。通过下述命令即可把 MCP 工具以标准协议暴露在 HTTP 端口：

```bash
# SSE 传输，适合 n8n MCP Client 节点
python -m github_trending_mcp.server --transport sse --host 0.0.0.0 --port 8765

# Streamable HTTP 传输（同样是标准 MCP 协议，部分宿主更偏好）
python -m github_trending_mcp.server --transport streamable-http --host 0.0.0.0 --port 8765 --streamable-http-path /mcp
```

- SSE 模式下客户端会访问 `GET http://<host>:<port>/sse` 建立流，并向 `POST http://<host>:<port>/messages/` 发送指令；`--mount-path` 可把整个传输挂载到子路径（例如 `/github`）。
- n8n MCP Client 节点中只需把 `Endpoint URL` 设置为 `http://<公网地址>:8765`（或反向代理后的地址），其默认的 `/sse` 与 `/messages/` 路径即可直接命中上面的服务；如果自定义了 `--sse-path`、`--message-path`，则在 n8n 中一并调整即可。
- Streamable HTTP 模式同样兼容 MCP 规范，单个 `POST http://<host>:<port>/mcp`（默认路径可通过 `--streamable-http-path` 修改）即可完成往返通信。
- `fetch_trending_repositories` 与 `list_trending_languages` 现在都会直接返回结构化 JSON，MCP 客户端（包括 n8n）可以无需再解析文本，直接按字段读取。
- 当一次传入多个语言时，会按照 `limit` 平均分配给每个语言（余数依次分给前若干个语言），确保“python 与 go 各取 5 条”这类需求变为可能；若某个语言不足指定数量，会尽可能补齐其它语言。

> 小贴士：`--host`、`--port`、`--mount-path`、`--sse-path`、`--message-path` 与 `--streamable-http-path` 也能作用在 `stdio` 模式以外的任何传输，便于在反向代理或多实例环境下部署。

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
# 镜像默认启动 HTTP/SSE 服务，映射 8000 端口即可
docker run --rm -p 8000:8000 -e GITHUB_TOKEN=ghp_xxx github-trending-mcp
```

如需改为 stdio MCP，可在 Dockerfile 末尾把 `CMD ["github-trending-mcp-http", ...]` 替换成注释里的 `CMD ["github-trending-mcp"]` 后重新 `docker build`。在对接 MCP 兼容的宿主（如 Claude Desktop、Cursor 等）时，记得根据其要求映射 stdin/stdout。

## 开发说明

- 需要 Python ≥ 3.10
- 依赖 `requests`、`beautifulsoup4`、`modelcontextprotocol`、`fastapi`、`uvicorn`
- 如需增加测试，可使用 `pytest`

## 限制

- GitHub Trending 每个语言/时间窗口仅提供一页数据，因此虽然 `limit` 上限为 100，最终返回数量取决于实际页面结果。
- 未提供 GitHub Token 时，REST API 调用会受每小时 60 次限制。如需长时间抓取，请配置令牌。
