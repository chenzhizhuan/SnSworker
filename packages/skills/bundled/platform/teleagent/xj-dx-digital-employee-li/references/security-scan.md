---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '25300d55-0cb5-4f4e-8222-9518f07d30cc'
  PropagateID: '25300d55-0cb5-4f4e-8222-9518f07d30cc'
  ReservedCode1: '5d338a8b-844c-49b9-b779-b097f0a3b0aa'
  ReservedCode2: '5d338a8b-844c-49b9-b779-b097f0a3b0aa'
---

# 安全漏洞扫描指南

## 目录

1. [扫描脚本使用](#扫描脚本使用)
2. [漏洞检测规则](#漏洞检测规则)
3. [报告格式](#报告格式)
4. [修复方案速查](#修复方案速查)
5. [服务器安全检查清单](#服务器安全检查清单)

---

## 扫描脚本使用

```bash
# 扫描指定项目目录
python scripts/security_scan.py /path/to/project

# 仅扫描 Java 项目
python scripts/security_scan.py /path/to/project --lang java

# 仅扫描 Python 项目
python scripts/security_scan.py /path/to/project --lang python

# 输出 JSON 格式报告
python scripts/security_scan.py /path/to/project --format json -o report.json
```

---

## 漏洞检测规则

### SQL 注入

| 模式 | 语言 | 检测正则 |
|------|------|---------|
| 字符串拼接SQL | Java | `"(SELECT\|INSERT\|UPDATE\|DELETE).*"\s*\+` |
| 字符串拼接SQL | Python | `f"(SELECT\|INSERT\|UPDATE\|DELETE).*\{` |
| MyBatis ${} 占位符 | XML | `\$\{.*\}` in mapper XML |

### XSS 跨站脚本

| 模式 | 检测方式 |
|------|---------|
| 未转义输出 | 搜索 `innerHTML`、`document.write`、`v-html` |
| 反射型XSS | Controller 直接返回未过滤的用户输入 |

### 命令注入

| 模式 | 语言 | 检测方式 |
|------|------|---------|
| exec/os.system | Python | 正则 `os\.system\(`、`subprocess\.call\(.*shell=True` |
| Runtime.exec | Java | 正则 `Runtime\.getRuntime\(\)\.exec\(` |

### 硬编码敏感信息

| 模式 | 检测正则 |
|------|---------|
| 密码 | `password\s*=\s*["'][^"'+]+["']` |
| 密钥 | `(secret\|api_key\|access_key)\s*=\s*["'][^"'+]+["']` |
| 数据库连接串含密码 | `jdbc:.*password=.*` |

### 反序列化漏洞

| 模式 | 语言 | 检测方式 |
|------|------|---------|
| Java原生反序列化 | Java | `ObjectInputStream`、`readObject` |
| pickle反序列化 | Python | `pickle\.loads\(`、`yaml\.load\(` (无Loader) |

### 路径遍历

| 模式 | 检测方式 |
|------|---------|
| 文件路径拼接用户输入 | 搜索 `new File(` + `request.getParameter` |
| Python open拼接 | 搜索 `open(` + `request` |

---

## 报告格式

### 文本格式

```
========== 安全扫描报告 ==========

扫描目标: /path/to/project
扫描时间: 2024-01-01 12:00:00
项目语言: Java, Python
扫描文件数: 45

--- 发现 3 个安全问题 ---

[高危] SQL注入
  文件: src/main/java/com/example/UserController.java:42
  描述: 检测到字符串拼接SQL语句
  代码: String sql = "SELECT * FROM user WHERE name = '" + name + "'"
  修复: 使用参数化查询或 MyBatis #{} 占位符

[中危] 硬编码密码
  文件: src/main/resources/application.yml:15
  描述: 配置文件中检测到明文密码
  代码: password: admin123
  修复: 使用环境变量或密钥管理服务

[低危] 信息泄露
  文件: src/main/java/com/example/GlobalExceptionHandler.java:28
  描述: 异常信息直接返回客户端，可能泄露技术栈信息
  代码: return Result.error(500, e.getMessage())
  修复: 记录完整异常到日志，返回通用错误提示

========== 扫描完成 ==========
```

---

## 修复方案速查

### SQL 注入修复

```java
// 错误
String sql = "SELECT * FROM user WHERE name = '" + name + "'";
jdbcTemplate.queryForObject(sql, User.class);

// 正确 - 参数化查询
String sql = "SELECT * FROM user WHERE name = ?";
jdbcTemplate.queryForObject(sql, User.class, name);

// 正确 - MyBatis
// XML: SELECT * FROM user WHERE name = #{name}  // 用#不用$
```

### XSS 修复

```java
// 对输出进行HTML转义
import org.apache.commons.text.StringEscapeUtils;
String safe = StringEscapeUtils.escapeHtml4(userInput);
```

### 命令注入修复

```python
# 错误
import os
os.system(f"ping {user_input}")

# 正确 - 使用参数列表
import subprocess
subprocess.run(["ping", user_input], check=True)
```

### 硬编码密钥修复

```yaml
# 错误
password: admin123

# 正确 - 环境变量
password: ${DB_PASSWORD}

# 正确 - Spring Boot 配置
password: ${DB_PASSWORD:default-fallback}
```

### 反序列化修复

```python
# 错误
import yaml
data = yaml.load(user_content)  # 不安全

# 正确
data = yaml.safe_load(user_content)
```

---

## 服务器安全检查清单

| 检查项 | 命令 | 安全标准 |
|--------|------|---------|
| SSH端口 | `ss -tlnp \| grep ssh` | 非默认22端口 |
| SSH密码登录 | `grep PasswordAuth /etc/ssh/sshd_config` | `PasswordAuthentication no` |
| 防火墙状态 | `firewall-cmd --state` / `ufw status` | 已启用 |
| 开放端口 | `ss -tlnp` | 仅80/443/22，无多余端口 |
| Docker Socket权限 | `ls -l /var/run/docker.sock` | 仅root/docker组可读写 |
| MySQL远程访问 | `grep bind-address MySQL配置` | `bind-address = 127.0.0.1` |
| Redis认证 | `redis-cli CONFIG GET requirepass` | 已设置密码 |
| Nginx版本隐藏 | `curl -I localhost \| grep Server` | 不暴露版本号 |
| 系统用户检查 | `cat /etc/passwd \| grep /bin/bash` | 无多余可登录用户 |
| 定时任务检查 | `crontab -l` / `ls /etc/cron.d/` | 无可疑定时任务 |
| 磁盘空间 | `df -h` | 使用率 < 80% |
| 系统日志异常 | `journalctl -p err --since "24 hours ago"` | 无异常报错 |