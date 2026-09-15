---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2bb7130e-fe10-4508-9e99-6d190075110c'
  PropagateID: '2bb7130e-fe10-4508-9e99-6d190075110c'
  ReservedCode1: 'b4896682-4d25-4ff2-86c9-1c961dab3053'
  ReservedCode2: 'b4896682-4d25-4ff2-86c9-1c961dab3053'
---

# 并行 SDD 派发模式（Parallel SDD Dispatch）

## 适用场景

当用户要求跳过 SDD 的逐任务顺序执行流程，改为多 subagent 并行开发时使用此模式。典型触发语：
- "多 subagents 并行开发"
- "并行执行"
- "不要一个一个来，同时做"

## 核心方法：按文件域分组

将计划中的所有 Task 按**文件域所有权**分组，确保没有两个并行 agent 同时写同一个文件。

### 分组步骤

1. **列出所有 Task 及其涉及的文件**（从计划中提取）
2. **识别共享文件**——被多个 Task 修改的文件（如 pom.xml、application.yml、实体类、Service 类）
3. **按文件域合并冲突 Task**——将共享同一文件的 Task 合并到同一个 agent
4. **独立 Task 保持独立**——不共享文件的 Task 可以安全并行

### 冲突矩阵示例

| Task 对 | 共享文件 | 处理方式 |
|---|---|---|
| Task 1 ↔ Task 4 | User.java（不同行） | 合并到同一 agent |
| Task 2 ↔ Task 9 | application.yml | 合并到同一 agent |
| Task 5 ↔ Task 10 | api/client.ts | 合并到同一 agent |
| Task 3 ↔ Task 6/7/8 | Controller ↔ Screen（不同层） | 可并行，无文件冲突 |

### 常见共享文件清单

**后端项目**需特别关注：
- `pom.xml` / `build.gradle` — 多个 Task 可能添加依赖
- `application.yml` / `application.properties` — 配置类 Task 和功能类 Task 都可能修改
- 实体类（Entity）— Bug 修复和功能扩展可能同时修改同一实体
- Service 类 — 权限修复和测试覆盖可能同时修改同一 Service
- Repository 接口 — 表名修复和查询优化可能同时修改

**前端项目**需特别关注：
- `package.json` — 依赖添加
- `components/index.ts` / 导出 barrel 文件 — 多个新组件需要导出
- `api/client.ts` — 配置化和新 API 文件都可能涉及
- Store 文件 — 多个功能可能修改同一 store

## 派发流程

1. **预检扫描**：检查计划中所有 Task 的文件列表，识别冲突
2. **分组**：按文件域将冲突 Task 合并，独立 Task 保持独立
3. **同时派发**：所有 agent 分组同时派发（使用 task 工具并行调用）
4. **等待全部完成**：所有 agent 返回后进入冲突检查
5. **冲突检查**：逐个检查共享文件，确认两个 agent 的修改是否都保留
6. **最终验证**：运行编译（后端 `mvn clean compile` / 前端 `tsc --noEmit`）和测试（`mvn test`）

## 冲突检查技巧

当两个 agent 修改了同一文件时，后返回的 agent 可能覆盖先返回的修改。检查方法：

1. **读取共享文件**，确认两个 agent 的修改是否都存在
2. **特别关注**：import 语句、依赖声明、配置项——这些容易被整体替换而非增量修改
3. **如果冲突**：手动合并两个 agent 的修改，保留两者的有效变更
4. **优先选择更优方案**：如果两个 agent 对同一问题用了不同方案（如 Agent A 在实体类加反向关联 `@ManyToMany(mappedBy=...)`，Agent B 用 Repository 查询 `existsByRoles_Id()`），选择避免循环引用/副作用更小的方案

## Git 提交策略

- 默认 SDD 要求每 Task 提交 git，但用户可能要求"不提交 git，代码留在本地"
- 并行模式下跳过 git 提交是合理的——并行 agent 无法安全地交替提交
- 如果用户后续需要提交，可以在所有 agent 完成后做一次整体提交

## 验证清单

并行模式完成后必须验证：
- [ ] 后端编译通过（`mvn clean compile`）
- [ ] 前端编译通过（`tsc --noEmit`）
- [ ] 所有测试通过（`mvn test`）
- [ ] 共享文件无冲突（逐个检查被多个 agent 涉及的文件）
- [ ] 无 import 缺失或类型错误