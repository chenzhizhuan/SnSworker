<!--
 * @Author: liu.yihu
 * @Date: 2024-04-29 17:18:01
 * @LastEditors: 刘威
 * @LastEditTime: 2025-09-28 09:27:25
 * @FilePath: \qccp-web\src\views\solution\components\gate\FsimGate.vue
 * @Description: Fsim操作门
-->
<template>
  <g @click.stop>
    <g v-if="!element.isGhost" transform="translate(0 0.4)">
      <line x1="18" x2="18" :y1="getRectLine()" y2="18" d1="0" d2="1" d3="1" :stroke="element.style.fill"
        stroke-width="3" class="hiq-gate"></line>
      <svg id="1" xmlns="http://www.w3.org/2000/svg" :x="0" :y="getRectLine2()" width="36" height="36" viewBox="0 0 1024 1024"
        class="hiq-gate">
        <circle cx="512" cy="512" r="512" :fill="element.style.fill" />
       <text x="512" y="630" text-anchor="middle" font-size="380" fill="#FFFFFF">FSIM</text>
      </svg>
    </g>
    <!-- <rect x="-105" y="-62" width="1905" height="322" style="padding: 5px; fill: transparent"></rect> -->
    <g transform="translate(0 -5)">
      <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" viewBox="-10 0 100 100">
        <circle cx="30" cy="52" r="40" :fill="element.style.fill" />
        <text x="30" y="65" text-anchor="middle" font-size="30" fill="#FFFFFF">FSIM</text>
      </svg>
    </g>
    <g v-if="element.isGhost">
      <g :transform="`translate(0 ${props.element.i * -GRAPH.ROW_SPACING})`">
        <rect width="42" :height="GRAPH.ROW_NUMBER * GRAPH.ROW_SPACING - 20" rx="2" class="yffControl"
          transform="translate(-3,-3)" :stroke="element.style.fill"
          style="stroke-width: 1; padding: 5px; fill: transparent"></rect>
      </g>
      <rect v-for="rect in GRAPH.ROW_NUMBER - 1" :key="rect" r="0" rx="0" ry="0" width="10" height="10"
        :stroke="element.style.fill" stroke-width="2" fill-opacity="0.7" :fill="element.style.cZGate[rect - 1].fill"
        :transform="`translate(14 ${getRectTransform(rect)})`" @click.stop="handleChangeChecked(rect - 1)"></rect>
    </g>
  </g>
</template>
<script setup>
import { GRAPH } from '@/hooks/graph';

const defaultRectStyle = { fill: '#ffffff' };

const props = defineProps({
  element: {
    type: Object,
    default: () => ({}),
  },
});

const getRectTransform = i => {
  // 判断当前的rect节点是不是在当前拖拽行下方
  let posY = 0;
  if (i > props.element.i) {
    posY = (i - props.element.i) * GRAPH.ROW_SPACING + 15;
  } else {
    posY = (props.element.i + 1 - i) * -GRAPH.ROW_SPACING + 15;
  }
  return posY;
};

const getRectTransform2 = (i) => {
  // 判断当前的rect节点是不是在当前拖拽行下方
  let posY = 0
  if (i > props.element.i) {
    posY = (i - props.element.i) * GRAPH.ROW_SPACING
  } else {
    posY = (props.element.i + 1 - i) * -GRAPH.ROW_SPACING
  }
  return posY
}


/**
 * @Author: liu.yihu
 * @des: 获取连线Y轴的偏移量
 * @return {*}
 */
function getRectLine() {
  const curI =
    props.element.checkedI > props.element.i
      ? props.element.checkedI
      : props.element.checkedI + 1;
  return getRectTransform(curI);
}

function getRectLine2() {
  const curI =
    props.element.checkedI > props.element.i ? props.element.checkedI : props.element.checkedI + 1
  return getRectTransform2(curI)
}
/**
 * @Author: liu.yihu
 * @des: 改变CZ操作门中的选中状态
 * @param {number} i 当前索引
 */
function handleChangeChecked(i) {
  const { cZGate } = props.element.style;
  if (cZGate[i].checked) {
    cZGate[i].checked = false;
    cZGate[i] = { ...cZGate[i], ...defaultRectStyle };
  } else {
    for (let j = 0; j < cZGate.length; j++) {
      cZGate[j].checked = false;
      cZGate[j] = { ...cZGate[j], ...defaultRectStyle };
    }
    cZGate[i].checked = true;
    // 当前的rect节点是不是勾选节点下方，
    // 如果是下方，则勾选节点索引+1，否则勾选节点索引不变，因为索引是从0开始计算
    props.element.checkedI = i >= props.element.i ? i + 1 : i;
    cZGate[i] = { ...cZGate[i], fill: props.element.style.fill };
  }
}
</script>
