#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目脚手架生成脚本
一键生成 Spring Boot / FastAPI 项目骨架，包含标准目录结构、配置文件和示例代码。

用法:
    python project_scaffold.py <项目名> --type springboot|fastapi [--package com.example] [--output 输出目录]
"""

import os
import sys
import argparse
from pathlib import Path


def create_file(filepath, content):
    """创建文件并写入内容，自动创建目录"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {filepath}")


def scaffold_springboot(project_name, package_name, output_dir):
    """生成 Spring Boot 项目骨架"""

    pkg_path = package_name.replace(".", "/")
    base_dir = os.path.join(output_dir, project_name)
    src_java = os.path.join(base_dir, "src/main/java", pkg_path)
    src_res = os.path.join(base_dir, "src/main/resources")
    test_java = os.path.join(base_dir, "src/test/java", pkg_path)

    # pom.xml
    create_file(os.path.join(base_dir, "pom.xml"), f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>
    <groupId>{package_name.split('.')[0]}</groupId>
    <artifactId>{project_name}</artifactId>
    <version>1.0.0</version>
    <name>{project_name}</name>
    <properties>
        <java.version>17</java.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>com.baomidou</groupId>
            <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
            <version>3.5.5</version>
        </dependency>
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springdoc</groupId>
            <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
            <version>2.3.0</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
""")

    # Application 主类
    app_class = project_name.replace("-", " ").title().replace(" ", "")
    create_file(os.path.join(src_java, f"{app_class}Application.java"), f"""package {package_name};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {app_class}Application {{
    public static void main(String[] args) {{
        SpringApplication.run({app_class}Application.class, args);
    }}
}}
""")

    # 统一返回
    create_file(os.path.join(src_java, "common/Result.java"), f"""package {package_name}.common;

import lombok.Data;

@Data
public class Result<T> {{
    private int code;
    private String message;
    private T data;

    public static <T> Result<T> success(T data) {{
        Result<T> r = new Result<>();
        r.setCode(200);
        r.setMessage("success");
        r.setData(data);
        return r;
    }}

    public static <T> Result<T> error(int code, String message) {{
        Result<T> r = new Result<>();
        r.setCode(code);
        r.setMessage(message);
        return r;
    }}
}}
""")

    # 全局异常处理
    create_file(os.path.join(src_java, "common/GlobalExceptionHandler.java"), f"""package {package_name}.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {{
    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception e) {{
        log.error("系统异常: ", e);
        return Result.error(500, "系统繁忙，请稍后重试");
    }}
}}
""")

    # 健康检查 Controller
    create_file(os.path.join(src_java, "controller/HealthController.java"), f"""package {package_name}.controller;

import {package_name}.common.Result;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class HealthController {{
    @GetMapping("/health")
    public Result<Map<String, String>> health() {{
        return Result.success(Map.of("status", "ok"));
    }}
}}
""")

    # CORS 配置
    create_file(os.path.join(src_java, "config/CorsConfig.java"), f"""package {package_name}.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

@Configuration
public class CorsConfig {{
    @Bean
    public CorsFilter corsFilter() {{
        CorsConfiguration config = new CorsConfiguration();
        config.addAllowedOriginPattern("*");
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        config.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }}
}}
""")

    # application.yml
    create_file(os.path.join(src_res, "application.yml"), f"""server:
  port: 8080

spring:
  datasource:
    url: jdbc:mysql://localhost:3306/{project_name.replace('-', '_')}?useSSL=false&serverTimezone=Asia/Shanghai
    username: ${{DB_USER:root}}
    password: ${{DB_PASS:}}
    driver-class-name: com.mysql.cj.jdbc.Driver

mybatis-plus:
  mapper-locations: classpath:mapper/*.xml
  configuration:
    map-underscore-to-camel-case: true

springdoc:
  swagger-ui:
    path: /swagger-ui.html
""")

    # application-prod.yml
    create_file(os.path.join(src_res, "application-prod.yml"), """spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USER}
    password: ${DB_PASS}
""")

    # Dockerfile
    create_file(os.path.join(base_dir, "Dockerfile"), """FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=builder /build/target/*.jar app.jar
EXPOSE 8080
ENV JAVA_OPTS="-Xms256m -Xmx512m -Dfile.encoding=UTF-8"
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
""")

    # docker-compose.yml
    create_file(os.path.join(base_dir, "docker-compose.yml"), f"""version: "3.8"
services:
  app:
    build: .
    container_name: {project_name}
    ports:
      - "8080:8080"
    environment:
      - DB_HOST=mysql
      - DB_USER=root
      - DB_PASS=${{DB_PASS:-root123}}
    depends_on:
      - mysql
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  mysql:
    image: mysql:8.0
    container_name: {project_name}-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${{DB_PASS:-root123}}
      MYSQL_DATABASE: {project_name.replace('-', '_')}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped

volumes:
  mysql_data:
""")

    # .gitignore
    create_file(os.path.join(base_dir, ".gitignore"), """target/
.idea/
*.iml
.vscode/
.DS_Store
*.log
""")

    # README
    create_file(os.path.join(base_dir, "README.md"), f"""# {project_name}

## 启动

```bash
# 本地启动
mvn spring-boot:run

# Docker 启动
docker-compose up -d
```

## API文档
http://localhost:8080/swagger-ui.html
""")

    print(f"\nSpring Boot 项目 '{project_name}' 创建完成！")
    print(f"目录: {base_dir}")
    print(f"启动: cd {project_name} && mvn spring-boot:run")


def scaffold_fastapi(project_name, output_dir):
    """生成 FastAPI 项目骨架"""

    base_dir = os.path.join(output_dir, project_name)
    app_dir = os.path.join(base_dir, "app")

    # main.py
    create_file(os.path.join(base_dir, "main.py"), """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
""")

    # config.py
    create_file(os.path.join(app_dir, "config.py"), f"""from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "{project_name}"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = "mysql+pymysql://root:root123@localhost:3306/{project_name.replace('-', '_')}"
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
""")

    # database.py
    create_file(os.path.join(app_dir, "database.py"), """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""")

    # routers/health.py
    create_file(os.path.join(app_dir, "routers/__init__.py"), "")
    create_file(os.path.join(app_dir, "routers/health.py"), """from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}
""")

    # __init__.py
    create_file(os.path.join(app_dir, "__init__.py"), "")
    create_file(os.path.join(app_dir, "models/__init__.py"), "")
    create_file(os.path.join(app_dir, "schemas/__init__.py"), "")
    create_file(os.path.join(app_dir, "services/__init__.py"), "")
    create_file(os.path.join(app_dir, "core/__init__.py"), "")

    # requirements.txt
    create_file(os.path.join(base_dir, "requirements.txt"), """fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pydantic==2.5.3
pydantic-settings==2.1.0
pymysql==1.1.0
python-multipart==0.0.6
""")

    # Dockerfile
    create_file(os.path.join(base_dir, "Dockerfile"), """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

    # docker-compose.yml
    create_file(os.path.join(base_dir, "docker-compose.yml"), f"""version: "3.8"
services:
  app:
    build: .
    container_name: {project_name}
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+pymysql://root:${{DB_PASS:-root123}}@mysql:3306/{project_name.replace('-', '_')}
    depends_on:
      - mysql
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  mysql:
    image: mysql:8.0
    container_name: {project_name}-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${{DB_PASS:-root123}}
      MYSQL_DATABASE: {project_name.replace('-', '_')}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped

volumes:
  mysql_data:
""")

    # .env
    create_file(os.path.join(base_dir, ".env"), f"""DATABASE_URL=mysql+pymysql://root:root123@localhost:3306/{project_name.replace('-', '_')}
""")

    # .gitignore
    create_file(os.path.join(base_dir, ".gitignore"), """__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
dist/
build/
""")

    # README
    create_file(os.path.join(base_dir, "README.md"), f"""# {project_name}

## 启动

```bash
# 安装依赖
pip install -r requirements.txt

# 本地启动
uvicorn main:app --reload

# Docker 启动
docker-compose up -d
```

## API文档
http://localhost:8000/docs
""")

    print(f"\nFastAPI 项目 '{project_name}' 创建完成！")
    print(f"目录: {base_dir}")
    print(f"启动: cd {project_name} && pip install -r requirements.txt && uvicorn main:app --reload")


def main():
    parser = argparse.ArgumentParser(description="项目脚手架生成工具")
    parser.add_argument("project_name", help="项目名称")
    parser.add_argument("--type", required=True, choices=["springboot", "fastapi"],
                        help="项目类型")
    parser.add_argument("--package", default="com.example.app",
                        help="Java 包名 (仅 Spring Boot, 默认 com.example.app)")
    parser.add_argument("--output", default=".",
                        help="输出目录 (默认当前目录)")

    args = parser.parse_args()
    output_dir = os.path.abspath(args.output)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if args.type == "springboot":
        scaffold_springboot(args.project_name, args.package, output_dir)
    else:
        scaffold_fastapi(args.project_name, output_dir)


if __name__ == "__main__":
    main()
