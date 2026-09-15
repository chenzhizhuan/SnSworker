# QCIS Circuit Display

Use this reference when a page requirement mentions QCIS, quantum circuit display, circuit visualization, or when API/local data includes a QCIS circuit string.

## Component contract

qccp-web already provides the circuit graph source. In generated `project-files`, import and use the existing component only:

```js
import QcisGraph from '@/views/solution/components/graph.vue';
```

Do not copy this skill's `assets/` source into `project-files`. The `assets/` folder is reference and preview support only. It mirrors the qccp-web circuit graph implementation and related gate components.

The circuit graph accepts a QCIS string:

```vue
<QcisGraph :qcis="qcisCircuit" />
```

Optional props are available only when the page explicitly needs them:

```vue
<QcisGraph
  :qcis="qcisCircuit"
  :max-qubit="maxQubit"
  :is-use-cus-lines="true"
  :is-use-sign="true"
  cus-font-size="12px"
/>
```

## Rendering rules

- Render the circuit section only when a non-empty QCIS string exists.
- Hide the whole circuit section when the QCIS value is missing, not a string, or blank.
- Do not show `<el-empty>` for a circuit-only section unless the user explicitly asks for an empty circuit panel.
- Keep the QCIS value as technical data. Do not translate, summarize, or rewrite the circuit source.
- Do not add fake QCIS to real API responses. If no real API field is provided, keep preview data in `data.js` and document it as mock data.

Use this pattern in the page:

```vue
<script setup>
import { computed, ref } from 'vue';
import QcisGraph from '@/views/solution/components/graph.vue';

const pageData = ref({});

const qcisCircuit = computed(() => {
  const value = pageData.value.qcis;
  return typeof value === 'string' ? value.trim() : '';
});

const hasQcisCircuit = computed(() => qcisCircuit.value.length > 0);
</script>

<template>
  <section v-if="hasQcisCircuit" class="page-key-circuit">
    <div class="wrapper">
      <h2>{{ $t('<pageKey>.circuit.title') }}</h2>
      <div class="page-key-circuit__graph">
        <QcisGraph :qcis="qcisCircuit" />
      </div>
    </div>
  </section>
</template>
```

If the API field is named `qcisCode`, `circuitQcis`, or another explicit contract name, use that exact field in the computed value.

## Styling pattern

```scss
.page-key-circuit {
  padding: 60px 0;
  background: #f4f7fc;

  &__graph {
    min-height: 360px;
    padding: 24px;
    overflow: hidden;
    background: #ffffff;
    border: 1px solid #dce0eb;
    border-radius: 8px;
  }
}
```

Adjust spacing to match the page, but keep the graph container stable and let the component handle internal scrolling.

## Preview HTML handling

When generating a standalone preview HTML or preview-only Vue sandbox, include the QCIS graph preview sources from this skill's `assets/` folder so the preview can render the circuit. This preview-only inclusion may use:

- `assets/graph.vue`
- `assets/component-list.js`
- `assets/graphic.js`
- `assets/gate/`

Do not place those preview assets under `<application_root>/frontend/qccp/project-files/`. They are not integration deliverables because qccp-web already contains the component source and gate registration.

## INTEGRATE.md notes

When the optional QCIS display is used, include:

- Component import path: `@/views/solution/components/graph.vue`
- QCIS source field name, for example `qcis`
- Rendering guard: section is hidden when the field is missing or blank
- Whether demo `data.js` contains mock QCIS preview data
- Confirmation that no circuit component source is copied into `project-files`
