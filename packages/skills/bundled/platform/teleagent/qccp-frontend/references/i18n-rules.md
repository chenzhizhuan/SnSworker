# I18n Rules

qccp-web must keep Chinese/English switching for every generated page.

## Required behavior

- Every user-visible string must be represented by a Vue I18n key.
- Provide complete Chinese and English entries in `INTEGRATE.md`.
- Template text uses `$t('<pageKey>.path.to.key')`.
- Script text uses `t('<pageKey>.path.to.key')`.
- Do not maintain two large local text objects inside the page.
- Do not hardcode one language in button labels, charts, empty states, form rules, messages, table columns, tabs, tags, or alt text.
- The route guard already manages `?lang=zh` and `?lang=en`; do not rewrite language query parameters in the page.
- QCIS circuit source text is technical data and must not be translated. Only surrounding titles, tabs, labels, helper text, and error or empty messages need i18n keys.

## Page usage

```vue
<script setup>
import { useI18n } from 'vue-i18n';

const { locale, t } = useI18n();
</script>

<template>
  <h1>{{ $t('<pageKey>.hero.title') }}</h1>
  <el-button>{{ $t('<pageKey>.actions.submit') }}</el-button>
</template>
```

`locale` may be used only for language-specific formatting or when a backend field is actually returned as `{ CN, EN }`.

## INTEGRATE.md snippets

Chinese object to append to `src/utils/lang/zh.js`:

```js
<pageKey>: {
  hero: {
    title: '中文标题',
  },
  actions: {
    submit: '提交',
  },
  message: {
    loadFailed: '数据加载失败',
    networkError: '网络异常，请稍后重试',
  },
},
```

English object to append to `src/utils/lang/en.js`:

```js
<pageKey>: {
  hero: {
    title: 'English title',
  },
  actions: {
    submit: 'Submit',
  },
  message: {
    loadFailed: 'Failed to load data',
    networkError: 'Network error. Please try again later.',
  },
},
```

## Self-check

- [ ] Chinese and English objects have identical key structure.
- [ ] No visible Chinese or English text remains hardcoded in the Vue template.
- [ ] Element Plus form rules and message text use `t(...)`.
- [ ] Chart labels, legends, tooltips, and empty states are translated.
- [ ] QCIS section labels are translated, while QCIS source strings remain unchanged.
- [ ] Button widths and layouts tolerate longer English text.
