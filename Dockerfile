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

# 默认以 FastMCP Streamable HTTP 传输启动，客户端可走单一 /mcp Endpoint
CMD ["github-trending-mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000", "--streamable-http-path", "/mcp"]
# 如需 SSE 传输，可改为：
# CMD ["github-trending-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
# 若要暴露 REST/SSE HTTP API，可使用：
# CMD ["github-trending-mcp-http", "--host", "0.0.0.0", "--port", "8000"]
