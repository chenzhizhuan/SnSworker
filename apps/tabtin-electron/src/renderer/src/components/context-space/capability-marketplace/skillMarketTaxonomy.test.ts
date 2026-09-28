import { describe, expect, it } from 'vitest'

import {
  isRecommendedMarketPackSkill,
  resolveSkillMarketCategory,
  SKILL_MARKET_CATEGORY_ORDER,
} from './skillMarketTaxonomy'

describe('resolveSkillMarketCategory', () => {
  it.each([
    ['writing', 'writing'],
    ['collab', 'collab'],
    ['data', 'data'],
    ['research', 'research'],
    ['creative', 'creative'],
    ['engineering', 'engineering'],
    ['business', 'business'],
  ] as const)('分类 %s 原生值直接命中', (input, expected) => {
    expect(resolveSkillMarketCategory(input)).toBe(expected)
  })

  it('推荐分类顺序：六类压缩包 + business（商务办公）', () => {
    expect([...SKILL_MARKET_CATEGORY_ORDER]).toEqual([
      'writing',
      'collab',
      'data',
      'research',
      'creative',
      'engineering',
      'business',
    ])
  })

  it('27 类体系归一到推荐七类（预装技能 category 能被 tabs 捡到）', () => {
    expect(resolveSkillMarketCategory('doc')).toBe('writing')
    expect(resolveSkillMarketCategory('analysis')).toBe('research')
    expect(resolveSkillMarketCategory('developer')).toBe('engineering')
    expect(resolveSkillMarketCategory('collaboration')).toBe('collab')
    expect(resolveSkillMarketCategory('finance')).toBe('data')
    expect(resolveSkillMarketCategory('design')).toBe('creative')
    expect(resolveSkillMarketCategory('sales_crm')).toBe('business')
    // 预装技能里出现过的超纲值也一并归一
    expect(resolveSkillMarketCategory('storage')).toBe('engineering')
    expect(resolveSkillMarketCategory('integration')).toBe('collab')
  })

  it('未分类与未映射杂类仍不进推荐 chip', () => {
    expect(resolveSkillMarketCategory(null)).toBeNull()
    expect(resolveSkillMarketCategory('')).toBeNull()
    expect(resolveSkillMarketCategory('other')).toBeNull()
    expect(resolveSkillMarketCategory('lifestyle')).toBeNull()
    expect(resolveSkillMarketCategory('unknown_category')).toBeNull()
  })
})

describe('isRecommendedMarketPackSkill', () => {
  it('只认压缩包 6 个 pack', () => {
    expect(isRecommendedMarketPackSkill({
      app_id: 'tabtin-writing-tools-pack',
      distribution: 'marketplace',
    })).toBe(true)
    expect(isRecommendedMarketPackSkill({
      app_id: 'tabtin-office-skills-pack',
      distribution: 'marketplace',
    })).toBe(false)
    expect(isRecommendedMarketPackSkill({
      app_id: 'tabdata',
      distribution: 'builtin',
    })).toBe(false)
  })
})
