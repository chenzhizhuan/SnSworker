/**
 * 坏 tool_call arguments 防复读（2026-09-16 生产事故修复）。
 *
 * 根因：模型生成 tool call 时 arguments 被 max_tokens 截断 → flushToolAccumulators
 * 的 JSON.parse 失败 → 坏字符串原样入库。历史回放时若原样写回
 * function.arguments，上游 tool-call-parser（vLLM qwen3_coder 等）对坏 JSON
 * 解析失败直接 400，会话从此每轮必挂（前端显示「模型服务暂时不可用」）。
 *
 * 修复：convertAssistantMessage 对字符串形态 input 回传前复验（safeToolCallArguments），
 * 解析失败替换为 '{}'（保留 id 配对结构，对话可继续）。
 */

import { describe, expect, it } from 'vitest';
import { convertAssistantMessage } from '../src/providers/proxy-provider.js';
import type { ContentBlock } from '../src/history/types.js';

const TRUNCATED_EDIT_FILE =
  '{"path": "artifacts/a.html", "old_string": "const data = %JSON%;", "new_string": "const data = {\\n  \\"';

function toolUseBlock(input: unknown): ContentBlock[] {
  return [{ type: 'tool_use', id: 'tu_1', name: 'edit_file', input } as unknown as ContentBlock];
}

describe('convertAssistantMessage — malformed tool arguments 防复读', () => {
  it('截断的字符串 input → arguments 修复为 {}', () => {
    const out = convertAssistantMessage(toolUseBlock(TRUNCATED_EDIT_FILE), 'drop');
    expect(out.tool_calls).toHaveLength(1);
    expect(out.tool_calls?.[0].function.name).toBe('edit_file');
    expect(out.tool_calls?.[0].function.arguments).toBe('{}');
  });

  it('合法字符串 input → arguments 原样透传', () => {
    const good = '{"query": "马云"}';
    const out = convertAssistantMessage(toolUseBlock(good), 'drop');
    expect(out.tool_calls?.[0].function.arguments).toBe(good);
  });

  it('对象 input → JSON.stringify（既有行为不变）', () => {
    const out = convertAssistantMessage(toolUseBlock({ a: 1 }), 'drop');
    expect(out.tool_calls?.[0].function.arguments).toBe('{"a":1}');
  });

  it('空字符串 input → 原样（协议常见形态）', () => {
    const out = convertAssistantMessage(toolUseBlock(''), 'drop');
    expect(out.tool_calls?.[0].function.arguments).toBe('');
  });

  it('混合消息：合法与截断 tool_use 并存时只修复坏的', () => {
    const blocks: ContentBlock[] = [
      { type: 'text', text: 'part' } as unknown as ContentBlock,
      { type: 'tool_use', id: 'tu_ok', name: 'web_search', input: { q: 'x' } } as unknown as ContentBlock,
      { type: 'tool_use', id: 'tu_bad', name: 'edit_file', input: '{"a": "unterminated' } as unknown as ContentBlock,
    ];
    const out = convertAssistantMessage(blocks, 'drop');
    expect(out.tool_calls).toHaveLength(2);
    expect(out.tool_calls?.[0].function.arguments).toBe('{"q":"x"}');
    expect(out.tool_calls?.[1].function.arguments).toBe('{}');
  });
});
