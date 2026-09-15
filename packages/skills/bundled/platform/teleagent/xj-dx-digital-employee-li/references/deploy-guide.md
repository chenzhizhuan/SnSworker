---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '281f000f-a781-4d51-a68c-fa8df2010597'
  PropagateID: '281f000f-a781-4d51-a68c-fa8df2010597'
  ReservedCode1: '37d70e9c-9a2e-40c6-871e-7b9cd40e0936'
  ReservedCode2: '37d70e9c-9a2e-40c6-871e-7b9cd40e0936'
---

# 部署运维手册

## 目录

1. [Docker 部署](#docker-部署)
2. [Nginx 反向代理配置](#nginx-反向代理配置)
3. [CI/CD 流水线](#cicd-流水线)
4. [天翼云部署](#天翼云部署)
5. [常用运维命令速查](#常用运维命令速查)

---

## Docker 部署

### Spring Boot Dockerfile（多阶段构建）

```dockerfile
# 构建阶段
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

# 运行阶段
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=builder /build/target/*.jar app.jar
EXPOSE 8080
ENV JAVA_OPTS="-Xms256m -Xmx512m -Dfile.encoding=UTF-8"
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

### FastAPI Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml 模板（多服务编排）

```yaml
version: "3.8"
services:
  app:
    build: .
    container_name: app-server
    ports:
      - "8080:8080"
    environment:
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_USER=root
      - DB_PASS=${DB_PASS}
      - REDIS_HOST=redis
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  mysql:
    image: mysql:8.0
    container_name: app-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASS}
      MYSQL_DATABASE: app_db
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: app-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: app-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:
```

---

## Nginx 反向代理配置

### 基础配置

```nginx
worker_processes auto;
events {
    worker_connections 1024;
}

http {
    upstream app_backend {
        server app:8080;
        # 负载均衡多实例
        # server app2:8080 weight=1;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # HTTP 跳 HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate     /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        # API 代理
        location /api/ {
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket 代理
        location /ws/ {
            proxy_pass http://app_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 300s;
        }

        # 静态文件
        location /static/ {
            root /app/static;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## CI/CD 流水线

### GitHub Actions 部署模板

```yaml
name: Build and Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      - name: Build with Maven
        run: mvn package -DskipTests -B
      - name: Build Docker image
        run: docker build -t app-server:latest .
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/app
            docker-compose pull
            docker-compose up -d --force-recreate
            docker image prune -f
```

### GitLab CI 部署模板

```yaml
stages:
  - build
  - deploy

build:
  stage: build
  image: maven:3.9-eclipse-temurin-17
  script:
    - mvn package -DskipTests -B
  artifacts:
    paths:
      - target/*.jar

deploy:
  stage: deploy
  only:
    - main
  script:
    - scp target/*.jar $SERVER_USER@$SERVER_HOST:/opt/app/
    - ssh $SERVER_USER@$SERVER_HOST "cd /opt/app && docker-compose up -d --force-recreate"
```

---

## 天翼云部署

1. **安全组配置**：仅开放必要端口（80/443/22），数据库端口不对公网开放
2. **SSH 密钥登录**：禁用密码登录，使用密钥对
3. **数据盘挂载**：Docker 数据目录迁移至数据盘 `/data/docker/`
4. **防火墙规则**：
   ```bash
   # 仅放行指定IP访问SSH
   firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=10.0.0.0/8 port=22 protocol=tcp accept'
   firewall-cmd --reload
   ```
5. **日志持久化**：挂载日志目录到数据盘，配置 logrotate 轮转

---

## 常用运维命令速查

```bash
# 查看容器状态
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 查看容器日志（最后200行）
docker logs --tail 200 -f app-server

# 进入容器排查
docker exec -it app-server sh

# 重启单个服务
docker-compose restart app

# 查看资源占用
docker stats --no-stream

# 清理无用镜像
docker image prune -f

# 检查端口监听
ss -tlnp

# Nginx 配置语法检查
nginx -t

# 查看系统资源
df -h && free -m
```