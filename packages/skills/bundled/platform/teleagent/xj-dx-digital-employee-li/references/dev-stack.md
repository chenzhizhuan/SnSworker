---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '424b5e3d-a6a4-4bea-9d3e-c588a5de7855'
  PropagateID: '424b5e3d-a6a4-4bea-9d3e-c588a5de7855'
  ReservedCode1: '539fa526-5248-4bc5-836c-f657be05ee85'
  ReservedCode2: '539fa526-5248-4bc5-836c-f657be05ee85'
---

# 开发指南

## 目录

1. [技术选型决策表](#技术选型决策表)
2. [Java - Spring Boot 项目模板](#java---spring-boot-项目模板)
3. [Python - FastAPI 项目模板](#python---fastapi-项目模板)
4. [数据库设计规范](#数据库设计规范)
5. [代码规范要点](#代码规范要点)

---

## 技术选型决策表

| 场景 | 推荐技术栈 | 理由 |
|------|-----------|------|
| 企业级REST API | Spring Boot 3.x + MyBatis-Plus | 成熟稳定，生态完善 |
| 微服务架构 | Spring Cloud + Nacos + Gateway | 服务注册/配置/网关一体化 |
| 高性能API | FastAPI + Uvicorn | 异步IO，自动文档 |
| 快速原型/管理后台 | Django + DRF | 自带ORM/Admin/Auth |
| 轻量服务/工具 | Flask + SQLAlchemy | 简洁灵活 |
| 实时通信 | Spring Boot + WebSocket / FastAPI + WebSocket | 按团队技术栈选 |
| 任务队列 | Celery (Python) / RabbitMQ (Java) | 异步任务解耦 |
| 缓存 | Redis | 通用缓存 + 会话存储 |

---

## Java - Spring Boot 项目模板

### 项目结构

```
project-name/
├── pom.xml
├── src/main/java/com/example/project/
│   ├── ProjectApplication.java
│   ├── config/
│   │   ├── CorsConfig.java
│   │   ├── SwaggerConfig.java
│   │   └── SecurityConfig.java
│   ├── controller/
│   │   └── UserController.java
│   ├── service/
│   │   ├── UserService.java
│   │   └── impl/UserServiceImpl.java
│   ├── mapper/
│   │   └── UserMapper.java
│   ├── entity/
│   │   └── User.java
│   ├── dto/
│   │   ├── UserDTO.java
│   │   └── UserQueryDTO.java
│   ├── common/
│   │   ├── Result.java
│   │   ├── PageResult.java
│   │   └── GlobalExceptionHandler.java
│   └── utils/
│       └── JwtUtil.java
├── src/main/resources/
│   ├── application.yml
│   ├── application-dev.yml
│   ├── application-prod.yml
│   └── mapper/
│       └── UserMapper.xml
└── src/test/java/
```

### 核心 pom.xml 依赖 (Spring Boot 3.x)

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.2.0</version>
</parent>
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
        <version>3.5.5</version>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-api</artifactId>
        <version>0.12.3</version>
    </dependency>
    <dependency>
        <groupId>org.springdoc</groupId>
        <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
        <version>2.3.0</version>
    </dependency>
    <dependency>
        <groupId>com.mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
    </dependency>
</dependencies>
```

### 统一返回格式

```java
@Data
public class Result<T> {
    private int code;
    private String message;
    private T data;

    public static <T> Result<T> success(T data) {
        Result<T> r = new Result<>();
        r.setCode(200);
        r.setMessage("success");
        r.setData(data);
        return r;
    }

    public static <T> Result<T> error(int code, String message) {
        Result<T> r = new Result<>();
        r.setCode(code);
        r.setMessage(message);
        return r;
    }
}
```

### Controller 模板

```java
@RestController
@RequestMapping("/api/users")
@Tag(name = "用户管理")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping("/{id}")
    @Operation(summary = "根据ID查询用户")
    public Result<UserDTO> getById(@PathVariable Long id) {
        return Result.success(userService.getById(id));
    }

    @GetMapping
    @Operation(summary = "分页查询用户")
    public Result<PageResult<UserDTO>> page(UserQueryDTO query) {
        return Result.success(userService.page(query));
    }

    @PostMapping
    @Operation(summary = "创建用户")
    public Result<Long> create(@Validated @RequestBody UserDTO dto) {
        return Result.success(userService.create(dto));
    }

    @PutMapping
    @Operation(summary = "更新用户")
    public Result<Void> update(@Validated @RequestBody UserDTO dto) {
        userService.update(dto);
        return Result.success(null);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除用户")
    public Result<Void> delete(@PathVariable Long id) {
        userService.delete(id);
        return Result.success(null);
    }
}
```

### application.yml 模板

```yaml
server:
  port: 8080
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/db_name?useSSL=false&serverTimezone=Asia/Shanghai
    username: ${DB_USER:root}
    password: ${DB_PASS:}
    driver-class-name: com.mysql.cj.jdbc.Driver
  redis:
    host: ${REDIS_HOST:localhost}
    port: 6379
mybatis-plus:
  mapper-locations: classpath:mapper/*.xml
  configuration:
    map-underscore-to-camel-case: true
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl
springdoc:
  swagger-ui:
    path: /swagger-ui.html
jwt:
  secret: ${JWT_SECRET:change-me-in-production}
  expiration: 86400000
```

---

## Python - FastAPI 项目模板

### 项目结构

```
project-name/
├── requirements.txt
├── main.py
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py
│   └── core/
│       ├── __init__.py
│       ├── security.py
│       └── exceptions.py
├── tests/
└── Dockerfile
```

### requirements.txt

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
pydantic==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pymysql==1.1.0
redis==5.0.1
python-multipart==0.0.6
```

### main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user
from app.config import settings

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

app.include_router(user.router, prefix="/api/users", tags=["用户管理"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

### Router 模板

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter()

@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.get("/", response_model=list[UserOut])
def list_users(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return UserService.get_list(db, skip=skip, limit=limit)

@router.post("/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return UserService.create(db, user)

@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    return UserService.update(db, user_id, user)

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    UserService.delete(db, user_id)
    return {"message": "删除成功"}
```

---

## 数据库设计规范

1. 表名小写下划线：`user_info`、`order_detail`
2. 主键统一 `id BIGINT AUTO_INCREMENT`
3. 必备字段：`created_at`、`updated_at`、`deleted` (逻辑删除)
4. 字段注释必填：`COMMENT '用户名'`
5. 索引命名：`idx_表名_字段名`
6. 唯一索引：`uk_表名_字段名`

---

## 代码规范要点

### Java
- 遵循阿里 Java 开发手册
- Controller 不含业务逻辑，仅做参数校验和转发
- Service 接口 + Impl 实现分离
- 统一异常处理，不向客户端暴露堆栈信息
- 使用 SLF4J 记录日志，禁止 `System.out.println`

### Python
- 遵循 PEP 8
- 类型注解必填：`def get_user(user_id: int) -> UserOut:`
- Pydantic schema 校验输入输出
- 使用 `logging` 模块，禁止 `print`
- 异步路由用 `async def`，IO 密集型场景