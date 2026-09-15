<template>
  <div class="svgImg">
    <el-scrollbar>
    <svg
      :height="height"
      :width="width "
      version="1.0"
      :viewBox="'0 0 ' + width + ' ' + height"
    >
      <g id="svgLine">
        <g v-for="index in GRAPH.ROW_NUMBER" :key="index"  :transform="getTransform(index)">
          <line
            x1="32"
            y1="20"
            :x2="width"
            y2="20"
            stroke="#dfe1e6"
            style="stroke-width: 1"
          ></line>
        </g>
      </g>
      <g id="Qbit" transform="translate(0 40)" style="opacity: 1">
        <rect
          width="59"
          transform="translate(0 0)"
          height="240"
          style="fill: white;"
        ></rect>
        <g>
          <g  v-for="index in GRAPH.ROW_NUMBER" :key="index" :transform="getTransform1(index)">
            <rect
              width="59"
              height="60"
              transform="translate(0 0)"
              style="fill: rgba(0, 0, 0, 0); pointer-events: bounding-box"
            ></rect>
            <circle cx="40" cy="30" r="20" fill="#E6F0FF"></circle>
            <text
              font-size="16px"
              text-anchor="end"
              font-weight="700"
              fill="#252b3a"
              x="52"
              y="36"
            >
              Q{{ qubitMap[index - 1] }}
            </text>
          </g>
        </g>
      </g>
      <g transform="translate(80 10)">
        <g v-for="(item, index) in GRAPH.COL_NUMBER" :key="index" :transform="computedColumn(index)">
          <rect
            width="36"
            height="10"
            style="fill: rgba(0, 0, 0, 0); pointer-events: bounding-box"
          ></rect>
          <text x="18" y="10" style="text-anchor: middle">{{item}}</text>
        </g>
      </g>
      <svg x="85" y="40" style="position: relative">
        <g :transform="item.style.transform" v-for="item  in componentData" :key="item.id" :element="item" style="display: inline">
        <component :is="item.component" :element="item"></component>
        </g>


      </svg>
    </svg>
  </el-scrollbar>
  </div>
</template>

<script setup>
import { graphicStore } from '@/store/graphic.js';
// import { GRAPH } from '@/hooks/graph';
import { computed ,watch,ref,reactive } from 'vue';
import componentList from './component-list';
import { deepCopy, generateID } from '@/utils/utils.js'
const store = graphicStore();

const props = defineProps({
  maxQubit: {
    type: Number,
  },
  qcis: {
    type: String
  },
  isUseCusLines: {
    type: Boolean,
    default: false
  },
  isUseSign: {
    type: Boolean,
    default: true
  },
  cusFontSize: {
    type: String,
    default: '12px'
  }
});

const GRAPH = reactive({
  ROW_NUMBER: props.isUseCusLines ? props.maxQubit : 5, // 行数
  COL_NUMBER: 20, // 列数
  ROW_SPACING: 60, // 行间距
  COL_SPACING: 60, // 列间距
  COL_START_X: 20, // 列起始位置
  ROW_START_Y: 20, // 行起始位置
});

const width = computed(() => 85 + GRAPH.COL_NUMBER * GRAPH.COL_SPACING);
const height = computed(() => 60 + GRAPH.ROW_NUMBER * GRAPH.ROW_SPACING);
const componentData = ref([])
// 存储唯一量子比特索引（例如 [0, 6, 12]）
const qubitMap = ref([]);


const getTransform = computed(() => {
  return index => `translate(32,${index * GRAPH.ROW_SPACING})`;
});

const getTransform1 = computed(() => {
  return index => `translate(0,${(index-1 )* GRAPH.ROW_SPACING + 10})`;
});

const computedColumn = i => {
  const X = 25 + i * GRAPH.COL_SPACING;

  return `translate(${X},0)`;
};


const addBits = () => {
  console.log(11111,GRAPH.ROW_NUMBER);

  if (GRAPH.ROW_NUMBER == store.maxQubit) return;
  GRAPH.ROW_NUMBER++;
};

const extractBits = (code) => {
  const regex = /Q(\d+)/g;
  let result = [];
  let match;

  // 循环匹配所有的 Q 数字
  while ((match = regex.exec(code)) !== null) {
    result.push(parseInt(match[1], 10)); // 将匹配到的数字转换成整数
  }

  // 去重并按升序排序
  return [...new Set(result)].sort((a, b) => a - b);
}

// watch(() => props.maxQubit, (newValue, oldValue) => {
//   const a = GRAPH.ROW_NUMBER-1
//   if (newValue) {
//     for (let i = 0; i < newValue - a; i++) {
//       addBits()
//     }
//   }
// }, { immediate: true, deep: true })

watch(() => props.qcis, (newValue, oldValue) => {
  if (newValue) {
    updateGraphDataByCode(props.qcis)
  }
}, { immediate: true, deep: true })


function getIlistByIndex(i, checkedI) {
  // 获取操作门占据的列索引集合，通过i和checkedI获取，以两个值最小的作为起始列索引，最大值作为结束列索引
  const startColIndex = Math.min(i, checkedI)
  const endColIndex = Math.max(i, checkedI)
  const iList = Array.from(
    { length: endColIndex - startColIndex + 1 },
    (_, index) => startColIndex + index
  )
  return iList
}




function updateGraphDataByCode(code) {
  qubitMap.value = extractBits(code);
  GRAPH.ROW_NUMBER = qubitMap.value.length;
  // 此处调用规则校验方法，通过则改变左侧数据
  code = code.replace(/(\s\n|\n|\r|\r\n|↵)/g, '\n')

  const fsimColors = [
    '#53B4AA',
    '#0E29A6',
    '#9BCE48',
    '#E9685D',
    '#9BCE48',
    '#E9685D',
    '#53B4AA',
    '#0E29A6',
  ];
  let fsimCounter = 0;

  const list = code?.split('\n')
  // 正则返回两个值 一个是Q之前的字符串，去除空格，一个是Q之后的字符串，不包括Q,去除空格
  const result = list
    ?.map((item) => {
      // Rx
      const parts = item.trim().split(/\s+/);
      const gate = parts[0];
      const args = parts.slice(1);

      const qubits = args.filter(p => p.startsWith('Q'));

      let gateR = ['RX', 'RY', 'RZ','XY2M','XY2P']
      let str = ''
      if (item.slice(0, 4) === 'XY2P' || item.slice(0, 4) === 'XY2M') {
        str = item.slice(0, 4)
      } else {
        str = item.slice(0, 2)
      }

      if (item.slice(0, 3) === 'RXY') {
        const rxGate = item.split(' ')
        let argument = rxGate[2]
        let argument1 = rxGate[3]
        // let after = rxGate[1].slice(1)
        let after = parseInt(rxGate[1].slice(1));
        let rowIndex = qubitMap.value.indexOf(after);
        if (rowIndex === -1) return;
        return {
          before: rxGate[0],
          after: rowIndex,
          argument: argument,
          argument1: argument1
        }
      }
       // B门
     if (item.startsWith('B')) {
        let checkeds = item.match(/\d+/g) || []
        checkeds = checkeds.map(Number).sort((a, b) => a - b)
        let mappedCheckeds = checkeds.map(c => qubitMap.value.indexOf(c)).filter(c => c !== -1);
        if (mappedCheckeds.length === 0) return;
        return {
          type: 'BSuper',
          checkeds:mappedCheckeds,
          before: 'B',
          after: mappedCheckeds[0],
          preCheckedId: mappedCheckeds[0],
          lastCheckedId: mappedCheckeds[mappedCheckeds.length - 1]
        }
      }
      if (gateR.includes(str)) {
        const rxGate = item.split(' ')
        let argument = rxGate[2]
        // if (argument.length > 4) {
        //   argument = argument.slice(0, 3) + '..';
        // }
        let after = parseInt(rxGate[1].slice(1));
        let rowIndex = qubitMap.value.indexOf(after);
        if (rowIndex === -1) return;
        return {
          before: rxGate[0],
          after: rowIndex,
          argument: argument
        }
      }
        // I门
      if (gate === 'I') {
        const IGate = item.split(' ')
        let t = IGate[2]

        // let after = IGate[1].slice(1)
        // if (after > GRAPH.ROW_NUMBER - 1) return

        let after = parseInt(IGate[1].slice(1));
        // 将原始量子比特索引映射到新行索引
        let rowIndex = qubitMap.value.indexOf(after);
        if (rowIndex === -1) return; // 如果量子比特不在 qubitMap 中，跳过
        return {
          before: IGate[0],
          after: rowIndex,
          t: t
        }
      }

         // ---- 解析 FSIM 新写法 ----
      if (gate === 'FSIM') {
         // e.g. FSIM Q46 Q53 0
        const [q1Str, q2Str] = args; // ["Q46", "Q53"]
        const q1 = Number(q1Str.slice(1)); // 去掉前缀 Q -> 46
        const q2 = Number(q2Str.slice(1)); // -> 53

        let rowIndex1 = qubitMap.value.indexOf(q1);
        let rowIndex2 = qubitMap.value.indexOf(q2);
        if (rowIndex1 === -1 || rowIndex2 === -1 || rowIndex1 === rowIndex2) return;

        return { before: 'FSIM', after: rowIndex2, checkedI: rowIndex1  };
      }

      const regex = /^(.*?)Q(\d+)$/
      const match = item.match(regex)

      if (match) {
        // 如果是CZ
        if (match[0].indexOf('CZ') != '-1' || match[0].indexOf('CX') != '-1') {
          const matchCZ = match.input.split(' ')
          let after = parseInt(matchCZ[2].slice(1));
          let checkedI = parseInt(matchCZ[1].slice(1));
          let rowIndex = qubitMap.value.indexOf(after);
          let checkedRowIndex = qubitMap.value.indexOf(checkedI);
          if (rowIndex === -1 || checkedRowIndex === -1) return;
          if (rowIndex === checkedRowIndex) return;
          return {
            before: matchCZ[0],
            after: rowIndex,
            checkedI: checkedRowIndex
          };
        }
        let after = parseInt(match[2].trim());
        let rowIndex = qubitMap.value.indexOf(after);
        if (rowIndex === -1) return;
        return {
          before: match[1].trim(),
          after: rowIndex
        };
      }
      return null;
    })
    .filter((item) => item)



  // 使用Map来存储组件，以便快速查找
  const componentMap = new Map(componentList.map((comp) => [comp.label, comp]))

  // 创建一个对象来跟踪每行的最大j值
  const maxJPerRow = {}
  // 将解析逻辑封装为一个函数
  function parseItem(item) {
    let fsimCounter = 0;
    const { before, after, checkedI, argument,t,
      argument1,
      preCheckedId,
      lastCheckedId,
      checkeds} = item
    const component = componentMap.get(before)

    if (component) {
      const rowIndex = after
      let colIndex = 0 // 假设列的索引从0开始

    // 处理 FSIM 门，独占一整列并分配颜色
    if (before === 'FSIM') {
      // 获取当前所有行的最大列索引
      const maxCol = Math.max(...Object.values(maxJPerRow).filter(val => val >= 0), -1) + 1;
      colIndex = maxCol; // 为 FSIM 分配新的列索引
      // 更新所有行的 maxJPerRow，确保整列独占
      for (let i = 0; i < GRAPH.ROW_NUMBER; i++) {
        maxJPerRow[i] = colIndex;
      }
      fsimCounter++; // 增加 FSIM 计数器
    }else if (before === 'CZ' ||before === 'CX' || before === 'B') {
        // CZ 获取每行的最大j值并加1
        const iList =
            before === 'B'
            ? getIlistByIndex(preCheckedId, lastCheckedId)
            : getIlistByIndex(rowIndex, checkedI)

        iList.forEach((item) => {

          if (maxJPerRow[item] >= 0) {
            if (colIndex <=maxJPerRow[item]) {

              colIndex = maxJPerRow[item] + 1
            }
          }
          // maxJPerRow[item] = colIndex
        })
        iList.forEach((item) => {
          maxJPerRow[item] = colIndex
        })

        // maxJPerRow[rowIndex] = colIndex
      } else {
        // 如果当前行已有数据，则获取该行的最大j值并加1
        if (maxJPerRow[rowIndex] >= 0) {
          colIndex = maxJPerRow[rowIndex] + 1
        }
        // 更新当前行的最大j值
        maxJPerRow[rowIndex] = colIndex
      }
      const node = deepCopy(component)
      node.id = generateID()
      node.i = +rowIndex
      node.dragY = rowIndex * GRAPH.ROW_SPACING + 20
      node.y = node.dragY
      node.dragX = colIndex * GRAPH.COL_SPACING + 20
      node.x = node.dragX
      node.style.transform = `translate(${node.x},${node.y})`

      // 为 FSIM 门设置循环颜色
      if (before === 'FSIM') {
        const colorIndex = (fsimCounter - 1) % fsimColors.length; // 计算当前 FSIM 门的颜色索引
        node.style = { ...node.style, fill: fsimColors[colorIndex] }; // 设置颜色
        node.component = 'FsimGate';
        node.label = 'FSIM';
        node.type = 'CZ';
      }

      let gateR = ['RX', 'RY', 'RZ','XY2M','XY2P']
      if (gateR.includes(node.label)) {
        node.arguments = argument
      }

      if (node.label === 'I') {
        node.t = t;
      }

      // 判断是不是CZ操作门
      if (node.label === 'CZ' || node.label === 'CX' || node.label === 'FSIM') {
        node.checkedI = checkedI
        node.checkedIdot = after

        node.isGhost = false
        node.style.cZGate = []
        // 设置CZ操作门中rect的样式
        for (let i = 1; i < GRAPH.ROW_NUMBER; i++) {
          node.style.cZGate.push({ fill: '#fff', checked: false })
        }
        if (checkedI < after) {
          if (node.checkedI > GRAPH.ROW_NUMBER) return
          node.style.cZGate[node.checkedI].checked = true
        } else {
          if (node.checkedI - 1 >= GRAPH.ROW_NUMBER) return
          node.style.cZGate[node.checkedI - 1].checked = true
        }
      }

       if (node.label === 'B') {
        console.log(qubitMap.value);

        // qubitMap.value.forEach((item, index) => {
        //   node.sibilings[item] = { checked: false };
        // })
        for (let i = 0; i < GRAPH.ROW_NUMBER; i++) {
          node.sibilings[i] = { checked: false };
        }
        node.checkedIds = checkeds;
        node.preCheckedId = preCheckedId;
        node.lastCheckedId = lastCheckedId;
        node.minI = 0;
        node.maxI = GRAPH.ROW_NUMBER - checkeds[checkeds.length - 1];
        console.log(checkeds);
        checkeds.forEach((i,index)=> {
          node.sibilings[index].checked = true;
        });
      }

      return node
    }

    return null // 如果没有找到组件，返回null
  }
  const parseData = result.map(parseItem).filter(Boolean) // 使用map进行转换，filter过滤掉null值
  GRAPH.COL_NUMBER = Math.max(...Object.values(maxJPerRow))+1
  if (GRAPH.COL_NUMBER <15) {
    GRAPH.COL_NUMBER = 15
  }
  componentData.value = deepCopy(parseData)
  componentData.value.forEach(item => {
    item.cusFontSize = props.cusFontSize
    item.isUseSign = props.isUseSign
  })
}


</script>


<style lang="scss" scoped>
.svgImg{
    width: 98%;
    height: 86%;
    margin: 0 auto;
    overflow: auto;
    user-select: none;

}
</style>
