<!--
 * @Author: 刘威
 * @Date: 2025-08-05 10:05:24
 * @LastEditors: 刘威
 * @LastEditTime: 2025-11-13 10:23:41
 * @FilePath: \qccp-web\src\views\solution\components\gate\DefaultGate.vue
 * @Description:
-->
<template>
  <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 40 40" style="width: 36px; height: 36px">
    <rect class="q-gate" width="40" height="40" rx="4" :fill="element.style.fill"></rect>
    <!-- TD and SD -->
    <text x="20" v-if="element.label==='TD'||element.label==='SD'" :y="yCoordinates(element.label)" :fill="element.style.textFill" text-anchor="middle"
      dominant-baseline="middle" font-size="18">
      {{ element.label.slice(0,1) }}

    </text>

    <text x="20" v-else :y="yCoordinates(element.label)" :fill="element.style.textFill" text-anchor="middle"
      dominant-baseline="middle" :font-size="fontSize(element.label)">
      {{ element.label }}
    </text>

    <!-- rx -->
    <text v-if="element.label == 'RX' || element.label == 'RY' || element.label == 'RZ'||element.label == 'XY2M'||element.label == 'XY2P'"  x="20" y="31"
      :fill="element.style.textFill" class="RXYZ" text-anchor="middle" dominant-baseline="middle" font-size="10px">
      {{ element.isUseSign ? 'θ' : '' }} {{ Number(element.arguments).toFixed(3)}}
    </text>

    <!-- {{ rxParams }} -->



    <!-- 位置先写死，后期可通过position属性扩展四个方向的坐标 -->
    <text v-if="element.extraLabel" x="30" y="13" :fill="element.extraLabel.style.fill" text-anchor="middle"
      dominant-baseline="middle" :font-size="element.extraLabel.style.fontSize ?? 12">
      {{ element.extraLabel.label }}
    </text>
  </svg>
</template>
<script setup>
import { storeToRefs } from 'pinia';
import { graphicStore } from '@/store/graphic.js';
import { ref } from 'vue'
// Props
const props = defineProps({
  element: {
    type: Object,
    default: () => ({}),
  },
});

const store = graphicStore();
const { componentData, rxParams } = storeToRefs(store);
// console.log(props.element.label,'propsprops');
// if(props.element.label==='X/2'){
//   props.element.label = 'X/2'
// }else if(props.element.label==='-X/2'){
//   props.element.label = '-X/2'
// }else if(props.element.label==='-X/2'){
//   props.element.label = 'Y/2'
// }else if(props.element.label==='-Y/2'){
//   props.element.label = '-Y/2'
// }

const fontSize = (label)=>{
  let arr = ['XY2M','XY2P']
  if (arr.includes(label)) {
    return 14
  } else {
    return 18
  }
}

const yCoordinates = (label) => {
  let arr = ['RX', 'RY', 'RZ','XY2M','XY2P','RXY','U']
  if (arr.includes(label)) {
    return 14
  } else {
    return 22
  }
}
</script>
<style>
.gate{
  font-size: 16px;
}
/* .RXYZ{
  text-overflow: ellipsis;
    overflow: hidden;
    word-break: break-all;
    white-space: nowrap;
} */
</style>
