# 以精简版 Python 3.11 作为运行时
FROM python:3.11-slim

# 关闭输出缓冲、设置工作目录
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 复制项目元数据与源码
COPY pyproject.toml README.md ./
COPY src ./src

# 安装依赖并注册可执行脚本
RUN pip install --no-cache-dir .

# 默认以 FastMCP SSE 传输启动，便于 n8n 等客户端通过 /sse 对接 MCP
CMD ["github-trending-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
# 若要暴露 HTTP API，可改回下方命令：
# CMD ["github-trending-mcp-http", "--host", "0.0.0.0", "--port", "8000"]
