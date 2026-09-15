# 企查查 MCP API Key 配置

仅在 `SKILL.md` 指定的连接、API Key 或 JSON 配置场景中读取本文件。执行时保留用户原始任务上下文。

## 配置方式

默认按 Server 分别提供以下五份占位符配置，不主动要求用户把 API Key 发送到聊天框。每次只复制并导入一份 JSON；导入并确认当前 Server 连接成功后，再继续导入下一份。不得把多个 Server 合并到同一份 JSON 中批量导入。

### 1. qcc-company

```json
{
  "mcpServers": {
    "qcc-company": {
      "url": "https://agent.qcc.com/mcp/company/stream",
      "headers": {
        "Authorization": "Bearer <请替换为你的企查查 API Key>"
      }
    }
  }
}
```

### 2. qcc-risk

```json
{
  "mcpServers": {
    "qcc-risk": {
      "url": "https://agent.qcc.com/mcp/risk/stream",
      "headers": {
        "Authorization": "Bearer <请替换为你的企查查 API Key>"
      }
    }
  }
}
```

### 3. qcc-ipr

```json
{
  "mcpServers": {
    "qcc-ipr": {
      "url": "https://agent.qcc.com/mcp/ipr/stream",
      "headers": {
        "Authorization": "Bearer <请替换为你的企查查 API Key>"
      }
    }
  }
}
```

### 4. qcc-operation

```json
{
  "mcpServers": {
    "qcc-operation": {
      "url": "https://agent.qcc.com/mcp/operation/stream",
      "headers": {
        "Authorization": "Bearer <请替换为你的企查查 API Key>"
      }
    }
  }
}
```

### 5. qcc-executive

```json
{
  "mcpServers": {
    "qcc-executive": {
      "url": "https://agent.qcc.com/mcp/executive/stream",
      "headers": {
        "Authorization": "Bearer <请替换为你的企查查 API Key>"
      }
    }
  }
}
```

同时告知用户：

1. 请先访问[企查查智能体数据平台](https://agent.qcc.com/)完成注册或登录。
2. 登录后，点击平台右上角头像，选择“[获取 API KEY](https://agent.qcc.com/profile/api-key)”，进入“获取 API KEY”页面。
3. 已有可用 Key 时直接复制；如果尚未创建，请新建一个 API Key，建议命名为 `TeleAgent`。
4. 页面复制的是包含 `Bearer ` 前缀的完整授权内容。请在第一份 JSON 中将 `Authorization` 的完整值 `Bearer <请替换为你的企查查 API Key>` 替换为复制的内容，确保最终只有一个 `Bearer`。
5. 将该份配置粘贴到【设置】→【工具设置】→【从 JSON 导入/添加】，确认 Server 连接成功。
6. 对其余 Server 重复替换、导入和连接检查，直至所需 Server 均已连接。
7. 全部导入完成后返回当前对话，以便继续原始任务。

## 凭证失效与安全规则

- API Key 缺失、错误或失效时，引导用户获取最新 API Key，并更新全部企查查服务的 `Authorization: Bearer ...`。
- 只有用户明确选择“把 API Key 发到聊天框，由 Agent 生成配置”时，才可接收并生成一次包含该 Key 的 JSON。
- 用户在聊天框提供 Key 时，只将 Key 放入用户要求的配置，不在解释、摘要或后续消息中再次复述，不写入文件、终端命令或调试日志，并提醒用户聊天记录可能保存敏感信息，优先改用占位符方案。
- 用户完成配置后仅重试原失败工具一次；仍失败时停止凭证配置循环并报告实际错误。
