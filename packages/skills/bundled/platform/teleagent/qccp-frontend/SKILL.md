---
name: qccp-frontend
description: "Guides self-contained Vue 3 page artifacts for the qccp-web TianYan Quantum Computing Cloud Platform frontend and quantum application showcases. Use for qccp pages, Element Plus SFCs, bilingual content, optional QCIS displays, routes, i18n, and frontend verification evidence. Trigger after qccp-ui. Do NOT use for backend/API implementation, quantum algorithm work, design-only review, or final readiness."
name_cn: 天衍前端助手
description_cn: 支持生成符合天衍量子云平台规范的Vue 3前端页面代码。包含路由配置、中英双语国际化及QCIS线路图展示等功能，辅助快速构建可交付的量子应用前端工程。
---

# qccp-web Frontend Page

Generate qccp-web Vue SFC artifacts for the `qccp_web_page` delivery profile. This skill does not own local FastAPI HTML demo layout or static mounting; use `qccp-service` for the `local_fastapi_demo` profile.

## When to Use

- User needs a qccp-web compatible Vue 3 SFC page for a quantum application or cloud showcase.
- User needs route snippets, i18n entries, page-local data/API boundary, optional QCIS circuit display, component structure, or build/integration evidence.
- A quantum application needs qccp-web frontend packaging evidence.

## When NOT to Use

- **Visual token/spec decisions only** -> use `qccp-ui` first.
- **Backend/API/service/deployment implementation** -> use `qccp-service`.
- **Quantum algorithm or report generation** -> use the selected `quantum-algorithm-*` skill and SDK reference.
- **Final staged verification or delivery approval** -> keep this skill out of scope.

## Priority rules

1. Read `qccp-ui` before generating or reviewing visual layout, tokens, spacing, radius, typography, or component styling.
2. Follow `agent.md` project facts over generic UI-generation rules when available.
3. Read `application_manifest.json` when it exists. API paths, qccp pageKey, route, and data schema must come from `qccp_web` or the backend contract.
4. Target stack is Vue 3 SFC, JavaScript, `<script setup>`, Element Plus, Vue I18n, scoped SCSS.
5. Do not generate React, TypeScript, JSX/TSX, Nuxt, Tailwind CSS, standalone HTML, CDN Vue/ECharts, or a new Vite project.
6. Do not create or replace app-level files such as `package.json`, `main.js`, `App.vue`, router file, language files, Header, or Footer.
7. Keep Chinese/English switching fully supported. Every visible string must use i18n keys and `INTEGRATE.md` must include complete zh/en entries.
8. Use a vertical top-to-bottom page structure by default: algorithm introduction box, banner/header section, content sections, data/process sections, action/footer section. Avoid left-right split hero layouts unless the request explicitly requires them.
9. qccp frontend artifacts must not invent endpoint prefixes such as `/api/<pageKey>/...`; consume the backend contract exactly, or state that a proxy/alias is required.

## Output location

For quantum application delivery, write generated qccp artifacts under `<application_root>/frontend/qccp/project-files/` and report application-root-relative paths. Mirror the target qccp-web paths inside that fixed subtree:

```text
frontend/qccp/project-files/
└─ src/
   ├─ views/<module>/<pageKey>/
   │  ├─ index.vue
   │  ├─ components/
   │  └─ data.js
   ├─ api/<pageKey>/index.js
   └─ assets/images/<pageKey>/
```

Only create `api/<pageKey>/index.js` when real endpoint details are provided. Otherwise use `data.js`.

## Module defaults

If the user does not specify a module, generate a solution page.

| Module | Page path | Route prefix |
| --- | --- | --- |
| solution | `src/views/solution/<pageKey>/` | `/solution/` |
| product | `src/views/product/<pageKey>/` | `/product/` |
| news | `src/views/news/<pageKey>/` | `/news/` |
| informationSpace | `src/views/informationSpace/<pageKey>/` | `/informationSpace/` |
| about | `src/views/about/<pageKey>/` | `/about/` |
| topLevel | `src/views/<pageKey>/` | `/<pageKey>` |

`pageKey` must be meaningful lowerCamelCase, for example `quantumSecurity`, never `newPage`, `page1`, or Chinese directory names.

## Page file rules

Use this shape and remove unused imports:

```vue
<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';

const route = useRoute();
const router = useRouter();
const { locale, t } = useI18n();
</script>

<template>
  <main class="page-key-page">
    <!-- complete page -->
  </main>
</template>

<style lang="scss" scoped>
.page-key-page {
  width: 100%;
  min-height: calc(100vh - 60px);
  background: #f4f7fc;
}
</style>
```

Allowed confirmed project-level imports:

```js
import Footer from '@/components/Footer.vue';
import { useMainStore } from '@/store/index.js';
import PagePanel from '@/views/solution/<pageKey>/components/PagePanel.vue';
import QcisGraph from '@/views/solution/components/graph.vue';
import { getPageData } from '@/api/<pageKey>/index.js';
```

Do not import unknown shared components. Header is already rendered globally and must not be imported.

Use `QcisGraph` only when the page requirement or API/local data includes a QCIS circuit string. Treat it as optional and render nothing when no QCIS value exists. Do not copy the component source from this skill's `assets/` folder into `project-files`; qccp-web already owns the component source. If `INTEGRATE.md` says the page uses `QcisGraph`, the SFC must actively import and render `<QcisGraph ...>`; comments or fallback `<pre>` blocks do not satisfy that claim.

## API and chart reliability

- Use only API paths declared in the backend contract or `application_manifest.json`.
- If the backend contract exposes `/api/solve`, do not call `/api/<pageKey>/solve` unless the backend also declares that alias or `INTEGRATE.md` documents an explicit proxy mapping.
- qccp SFC files must not assume global `echarts`; import it from the project dependency.
- Chart containers need an explicit height or stable aspect ratio.
- Render charts after `nextTick`, retry or guard when the container is absent, handle window resize, and dispose chart instances in `onBeforeUnmount`.

## References

Load these only when needed:

- `references/layout-and-style.md`: qccp layout, SCSS, vertical structure, responsive constraints.
- `references/i18n-rules.md`: Chinese/English switching and required i18n snippets.
- `references/api-rules.md`: axios instance and no-fake-interface rules.
- `references/qcis-circuit.md`: optional QCIS circuit graph import, rendering guard, preview-only asset handling.

## Required states

Implement states relevant to the page:

- loading
- normal data
- empty data using `<el-empty>`
- request failure with retry
- submit loading and duplicate-click prevention
- form validation with `el-form` and `rules`
- cleanup in `onBeforeUnmount` for timers, window listeners, sockets, charts, or 3D scenes

Do not leave TODOs, empty click handlers, fake uploads, fake submits, random network URLs, `console.log`, or visible placeholder text.

## INTEGRATE.md requirements

Include task-specific, copy-pastable content:

1. Page name, `pageKey`, module, final route.
2. Exact copy destinations for every generated file.
3. Route object to append, not the full router file.
4. Complete Chinese i18n object to append.
5. Complete English i18n object to append.
6. Existing npm dependencies used.
7. API URL/method/request/response/apiCode, or state clearly that mock `data.js` is used.
8. Whether the optional QCIS circuit display is used, the QCIS field name, and the hidden-when-empty behavior.
9. Whether `Footer` is used.
10. Whether login permission or nav entry is needed.
11. Verification command: `npm run build`.

Never claim the page has already been integrated into qccp-web.

## Application delivery handoff

For quantum application delivery, write the qccp handoff bundle under `<application_root>/frontend/qccp/project-files/`. Frontend work contributes app packaging and verification evidence. In `<application_root>/INTEGRATE.md`, include route path, i18n keys, API/mock boundary, request/response assumptions, and build command so backend and integration reviewers can check contract consistency.

Treat `application_manifest.json` as application source. Keep its `qccp_web` fields and frontend
implementation consistent; update them together when an implementation-time route, asset,
entrypoint, fixture, or browser selector changes.

Do not decide delivery readiness from this skill. Provide reviewable frontend evidence for the application packaging and verification stages.

## Completion checklist

- [ ] `frontend/qccp/project-files/src/views/.../index.vue` exists under the fixed application root.
- [ ] Vue 3 `<script setup>` uses JavaScript, not TypeScript.
- [ ] All visible text uses i18n keys.
- [ ] zh/en snippets are complete and preserve language switching.
- [ ] The first visible page content is the required 1440px algorithm introduction box with i18n text.
- [ ] No new dependencies.
- [ ] No unknown shared component imports.
- [ ] If a QCIS circuit is used, `QcisGraph` is imported from qccp-web and is guarded by a non-empty QCIS string.
- [ ] Styles are scoped SCSS.
- [ ] Layout is mainly top-to-bottom and works at 1366/1440/1920 desktop widths.
- [ ] No generated replacement for existing app-level files.
