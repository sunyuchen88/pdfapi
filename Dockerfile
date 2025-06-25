# 使用官方 Python 运行时作为父镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录内容到容器的 /app 中
COPY . /app

# 安装所需的包
RUN pip install --no-cache-dir -r requirements.txt

# 确保 entrypoint.sh 是可执行的
RUN chmod +x /app/entrypoint.sh

# 创建 Gunicorn 日志文件目录
RUN mkdir -p /app/logs
# 创建上传目录
RUN mkdir -p /app/static/png_output

# 暴露端口，以便外部可以访问
EXPOSE 8080

# 定义环境变量
ENV FLASK_APP=main_app.py

# 运行 app.py
CMD ["/app/entrypoint.sh", "production"]
