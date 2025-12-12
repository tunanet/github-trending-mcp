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

# 通过 setuptools entry point 启动 MCP 服务器
CMD ["github-trending-mcp"]
