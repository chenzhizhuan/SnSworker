import { describe, expect, it } from 'vitest'
import { isPathInside } from '@components/shared/file-utils/path-ops'
import { relativePath } from './path'

describe('tabcode path utils', () => {
  it('resolves Windows file paths relative to a slash-normalized root', () => {
    expect(relativePath(
      'C:/workspace/SnSworker-feature/SnSworker',
      'C:\\workspace\\SnSworker-feature\\SnSworker\\.cursor\\skills\\linux-commit-discipline\\SKILL.md',
    )).toBe('.cursor/skills/linux-commit-discipline/SKILL.md')
  })

  it('matches Windows drive paths case-insensitively', () => {
    expect(relativePath(
      'c:/workspace/SnSworker-feature/SnSworker',
      'C:\\workspace\\SnSworker-feature\\SnSworker\\apps\\tabtin-electron\\package.json',
    )).toBe('apps/tabtin-electron/package.json')
  })

  it('never exposes an absolute path when the target is outside the root', () => {
    expect(relativePath(
      'C:/workspace/project',
      'C:\\Users\\me\\outside.ts',
    )).toBe('outside.ts')
  })

  it('matches Windows path containment case-insensitively for index exclusions', () => {
    expect(isPathInside(
      'C:/Repo',
      'c:/repo/node_modules/package/index.js',
    )).toBe(true)
  })

})
