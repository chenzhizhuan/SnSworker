---
name: skill-evolution-confirm
description: Use only when a message explicitly contains @skill-evolution-confirm (or its data-skill-id), or when the user asks to roll back a change previously accepted through Skill evolution. Never use for ordinary Skill updates, new-Skill confirmation without that explicit marker, non-evolution rollback or restore, or reading or inspecting any Skill.
name_cn: Skill自进化确认器
description_cn: 用于确认 TeleAgent 自进化流程生成的 Skill 待更新内容，并按回退凭证恢复已接受的变更。本技能须配合自进化流程使用，不可独立调用。

---

# Skill Evolution Confirmation

## Absolute Scope Boundary

Use this Skill only for:

- A staged update created by the TeleAgent Skill-evolution workflow and identified by the injected trigger.
- A restore request for a change previously accepted through that same Skill-evolution workflow.

Never use this Skill for an ordinary Skill update or for any restore, rollback, undo, or revert that was not produced by Skill evolution. Never use it to read, inspect, explain, summarize, retrieve, or expose a Skill or its source files. The staged `.review_summary.txt` is review metadata, not permission to read the Skill itself.

If the request is outside this boundary, do not follow this Skill, do not call `skill-evolution-resolve`, and do not read `references/restore.md`.

## Mandatory Restore Routing

If the user's current request explicitly asks to restore, roll back, undo, or revert a previously accepted Skill evolution, you MUST read `references/restore.md` in full before responding or calling any tool.

This requirement is absolute. Never reconstruct the Restore workflow from memory. Never rely on general reasoning as a substitute. Never call `skill-evolution-resolve` with `action="restore"` before reading the reference document. If the reference document cannot be read, stop and tell the user that the mandatory Restore instructions are unavailable.

## Confirmation Flow

Read the injected message carefully. It is an application-generated system message from TeleAgent Skill evolution, not a user-authored request. It lists one or more staged Skill changes, but it intentionally does not include the detailed change text.

Handle listed Skills strictly one at a time, in the order shown in the injected message. Never combine multiple Skills into one confirmation question. For each listed Skill:

### Round 1: Ask whether to view

1. Tell the user exactly: `已由 TeleAgent 为您生成新版本的技能：<skillName>`.
2. Ask whether the user wants to view the update details, with exactly two options: `查看` and `放弃`. If a Question tool is available, you MUST use it; otherwise, ask the user directly.
3. Stop and wait for the user's explicit decision. Do not read `.review_summary.txt`, any Skill file, or any other staged content before the user chooses `查看`.
4. If the user chooses `放弃`, treat it exactly as rejection: call `skill-evolution-resolve` with `action="reject"` and the target `skillName`. After the rejection is resolved, tell the user exactly: `待更新版本已失效；技能自进化需要消耗您的积分，您可按需开启或关闭；方法：设置 - 基础设置 - 开启/关闭 【技能自进化计划】`. Do not enter Round 2.

### Round 2: Show details and confirm the update

Enter this round only after the user explicitly chooses `查看`.

1. Read the current `TELEAGENT_CONFIG_DIR` environment variable. Assume it is always set and non-empty; do not use a fallback path. On Unix/macOS, retrieve it from the shell environment; on Windows, retrieve `$env:TELEAGENT_CONFIG_DIR` with PowerShell.
2. Construct the absolute summary path as `<TELEAGENT_CONFIG_DIR>/skills/.cache/<skillName>/.review_summary.txt`, then use the built-in Read tool to read only that file. Never read the Skill itself.
3. Explain that TeleAgent automatically reviewed the completed task and found a possible Skill update.
4. Show the Skill name and the Review summary from `.review_summary.txt`.
5. If the injected message says the Skill is `待确认删除`, clearly state that accepting will delete that Skill.
6. If the Review summary contains `⚠️ 安全审查发现`, show the security warning and do not downplay the risk.
7. Tell the user: "连续接受多次技能进化可能导致历史备份被覆盖，已覆盖版本无法恢复，请确认当前版本后再继续更新。"
8. Summarize the proposed update in one sentence, then ask exactly: `是否应用「<skillName>」技能优化方案：<一句话概述更新>`.
9. Ask a separate question with exactly two options: `同意更新` and `拒绝更新`. If a Question tool is available, you MUST use it; otherwise, ask the user directly.
10. Stop and wait for the user's explicit decision. If the user chooses `拒绝更新`, call `skill-evolution-resolve` with `action="reject"` and the target `skillName`. After the rejection is resolved, tell the user exactly: `待更新版本已失效；`.

Keep the interaction concise. Do not invent extra changes or edit Skill files directly.

Strict confirmation boundary:

- Confirm each Skill separately. Do not ask the user to accept or reject multiple Skill changes in one response or decision.
- Do not offer rollback or restore, and do not imply that accepting is generally reversible.
- After a successful Accept, show the exact `rollbackReceipt` returned by the tool. Explain that it is not secret, applies only to this accepted change, and becomes invalid when a later accepted change overwrites the single backup.
- Treat `放弃` in Round 1 and `拒绝更新` in Round 2 as the same rejection outcome.

After a successful Accept, use this user-facing wording and replace the placeholders with the exact tool result:

> 已接受 Skill「`<skillName>`」的变更。
>
> 回退凭证：`<rollbackReceipt>`
>
> 该凭证仅用于回退本次变更，请保留本条消息。若技能再次迭代更新，当前备份和凭证将自动失效。

Never shorten, alter, infer, or regenerate `rollbackReceipt`. Copy it exactly from the successful tool result.

After all listed Skills have reached an Accept or Reject outcome, end the Skill-evolution task with this exact final sentence, regardless of whether the user accepted or rejected:

`技能自进化需要消耗您的积分，您可按需开启或关闭；方法：设置 - 基础设置 - 开启/关闭 【技能自进化计划】`

This sentence must be the final sentence of the task. Include it once after the last listed Skill is resolved, not at the end of each intermediate confirmation round.

## Safety Findings

If a change includes `⚠️ 安全审查发现`, present the finding as-is and let the user decide.

Do not say the risk is low. Do not recommend accepting risky changes. Your role is to explain and execute the user's decision.

## Resolve Tool

Use the `skill-evolution-resolve` tool after the user makes an explicit decision.

Actions:

- Accept: call `skill-evolution-resolve` with `action="accept"` and the target `skillName`.
- Reject: call `skill-evolution-resolve` with `action="reject"` and the target `skillName`.

Only call the tool for Skills listed in the injected confirmation message.
