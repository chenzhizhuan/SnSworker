/**
 * 能力市场「推荐」分类。
 *
 * 七类 = 原六个压缩包文件夹 key + business（商务办公：销售/营销/财务/法务/HR/客户支持等）。
 * 推荐货架的成员已扩到 platform 预装技能（见 skillSourceGroups.isRecommendedMarketCatalogSkill），
 * 其 category 用 skillCategory.ts 的 27 类体系——resolveSkillMarketCategory 负责 27 类 →
 * 七类归一；未映射值返回 null（不进任何 tab，仅「全部」可见）。
 */
export const SKILL_MARKET_CATEGORY_ORDER = [
  'writing',
  'collab',
  'data',
  'research',
  'creative',
  'engineering',
  'business',
] as const

export type SkillMarketCategory = (typeof SKILL_MARKET_CATEGORY_ORDER)[number]

/** 推荐货架只展示这批压缩包导入的 pack（不含内置 Operator / 其它 marketplace pack）。 */
export const RECOMMENDED_MARKET_PACK_IDS = new Set([
  'tabtin-writing-tools-pack',
  'tabtin-collab-efficiency-pack',
  'tabtin-data-toolkit-pack',
  'tabtin-business-analysis-pack',
  'tabtin-creative-toolkit-pack',
  'tabtin-dev-toolkit-pack',
])

const CATEGORY_KEYS = new Set<string>(SKILL_MARKET_CATEGORY_ORDER)

/**
 * 27 类体系（skillCategory.ts 的 SKILL_MARKET_CATEGORIES）→ 推荐货架七类的归一映射。
 * 预装技能中出现过的超纲值（storage / integration）一并映射；
 * lifestyle / other 等消费向杂类不映射，保持仅「全部」可见。
 */
const CATEGORY_FALLBACK_MAP: Partial<Record<string, SkillMarketCategory>> = {
  // → 文档写作
  doc: 'writing',
  // → 协作效率
  collaboration: 'collab',
  communication: 'collab',
  productivity: 'collab',
  project_management: 'collab',
  workflow: 'collab',
  integration: 'collab',
  // → 数据处理
  finance: 'data',
  // → 研究分析
  analysis: 'research',
  knowledge: 'research',
  education: 'research',
  // → 创意设计
  design: 'creative',
  media: 'creative',
  ai_media: 'creative',
  // → 工程开发
  developer: 'engineering',
  automation: 'engineering',
  utility: 'engineering',
  storage: 'engineering',
  device: 'engineering',
  web: 'engineering',
  // → 商务办公
  sales_crm: 'business',
  marketing: 'business',
  legal: 'business',
  hr: 'business',
  customer_support: 'business',
}

export function resolveSkillMarketCategory(category: string | null | undefined): SkillMarketCategory | null {
  const normalized = category?.trim().toLowerCase()
  if (!normalized) return null
  if (CATEGORY_KEYS.has(normalized)) return normalized as SkillMarketCategory
  return CATEGORY_FALLBACK_MAP[normalized] ?? null
}

export function isRecommendedMarketPackSkill(skill: {
  app_id?: string | null
  source?: string | null
  distribution?: string | null
}): boolean {
  const appId = typeof skill.app_id === 'string' ? skill.app_id.trim() : ''
  if (!appId || !RECOMMENDED_MARKET_PACK_IDS.has(appId)) return false
  return skill.distribution === 'marketplace'
}
