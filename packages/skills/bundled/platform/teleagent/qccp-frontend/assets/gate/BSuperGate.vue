<template>
  <g @click.stop>
    <BGate v-if="element.sibilings.length === 0" />
    <g v-else>
      <g v-for="(item, i) in element.sibilings" :key="i">
        <g
          v-if="item.checked"
          :transform="`translate(0 ${getRectChecked(i)})`"
          @click.stop="handleChange(item, i)"
        >
          <BGate />
        </g>
        <rect
          v-if="element.isCanEdit && !item.checked"
          r="0"
          rx="0"
          ry="0"
          width="10"
          height="10"
          :stroke="element.style.fill"
          stroke-width="2"
          fill-opacity="0.7"
          fill="#ffffff"
          :transform="`translate(14 ${getRectTransform(i)})`"
          @click.stop="handleChange(item)"
        ></rect>
      </g>
    </g>
  </g>
</template>
<script setup>
import BGate from './BGate.vue'
import { GRAPH } from '@/hooks/graph'

const emit = defineEmits(['BSuperChecked'])

const props = defineProps({
  element: {
    type: Object,
    default: () => ({})
  }
})

/**
 * 计算 选中 状态矩形的位置
 * */
const getRectChecked = (i) => {
  let posY = 0
  if (i > props.element.i) {
    posY = (i - props.element.i) * GRAPH.ROW_SPACING
  } else {
    posY = (props.element.i - i) * -GRAPH.ROW_SPACING
  }
  return posY
}

/**
 * 计算 未选中 状态矩形的位置
 * */
const getRectTransform = (i) => {
  let posY = 0
  if (i > props.element.i) {
    posY = (i - props.element.i) * GRAPH.ROW_SPACING + 15
  } else {
    posY = (props.element.i - i) * -GRAPH.ROW_SPACING + 15
  }
  return posY
}
/**
 * 编辑选项
 *  1. 如果不可编辑，直接阻止后续流程
 *  2. 否则 取当前 相反的状态
 */
const handleChange = (item, i) => {
  if (!props.element.isCanEdit) return
  if (props.element.i === i) return
  item.checked = !item.checked
  props.element.checkedIds = props.element.sibilings
    .map((item, index) => (item.checked ? index : -1))
    .filter((index) => index !== -1)
  props.element.minI = props.element.i - props.element.checkedIds[0]
  props.element.maxI =
    props.element.i +
    GRAPH.ROW_NUMBER -
    1 -
    props.element.checkedIds[props.element.checkedIds.length - 1]
  emit('BSuperChecked')
}
</script>
