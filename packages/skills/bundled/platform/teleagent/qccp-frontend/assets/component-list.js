// import xImg from '@/assets/gates/xImg.png'
// import yImg from '@/assets/gates/yImg.png'
// import zImg from '@/assets/gates/zImg.png'
// import rxImg from '@/assets/gates/rxImg.png'
// import ryImg from '@/assets/gates/ryImg.png'
// import rzImg from '@/assets/gates/rzImg.png'
// import sImg from '@/assets/gates/sImg.png'
// import sdImg from '@/assets/gates/sdImg.png'
// import tImg from '@/assets/gates/tImg.png'
// import tdImg from '@/assets/gates/tdImg.png'
// import x2pImg from '@/assets/gates/x2pImg.png'
// import x2mImg from '@/assets/gates/x2mImg.png'
// import y2pImg from '@/assets/gates/y2pImg.png'
// import y2mImg from '@/assets/gates/y2mImg.png'
// import hImg from '@/assets/gates/hImg.png'
// import czImg from '@/assets/gates/czImg.png'

export const commonStyle = {
  rotate: 0,
  // opacity: 1,
};

export const commonAttr = {
  // animations: [],
  // events: {},
  isLock: false, // 是否锁定组件
};



export const defaultStyle = {
  cursor: 'grab',
  fill: '#1664FF',
  textFill: 'white',
  width: '40px',
  height: '40px',
};

// 编辑器左侧组件列表
const list = [
  {
    component: 'DefaultGate',
    label: 'X',
    i: 0,
    j: 0,
    isEdit: false,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'Y',
    i: 0,
    j: 0,
    isEdit: false,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'Z',
    i: 0,
    j: 0,
    isEdit: false,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'RX',
    i: 0,
    j: 0,
    isEdit: true,
    style: defaultStyle,
    type: 'R',
    arguments:''
  },
  {
    component: 'DefaultGate',
    label: 'RY',
    i: 0,
    j: 0,
    isEdit: true,
    style: defaultStyle,
    type: 'R',
    arguments:''
  },
  {
    component: 'DefaultGate',
    label: 'RZ',
    i: 0,
    j: 0,
    isEdit: true,
    style: defaultStyle,
    type: 'R',
    arguments:''
  },
  {
    component: 'DefaultGate',
    label: 'S',
    i: 0,
    j: 0,
    isEdit: false,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'SD',
    extraLabel: {
      position: 'top',
      label: '+',
      style: {
        fill: '#ffffff',
      },
    },
    i: 0,
    j: 0,
    isEdit: false,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'T',
    i: 0,
    j: 0,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'TD',
    extraLabel: {
      position: 'top',
      label: '+',
      style: {
        fill: '#ffffff',
      },
    },
    i: 0,
    j: 0,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'X2P',
    i: 0,
    j: 0,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'X2M',
    i: 0,
    j: 0,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'Y2P',
    i: 0,
    j: 0,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'Y2M',
    i: 0,
    j: 0,
    style: defaultStyle,
    type: 'single',
  },
  {
    component: 'DefaultGate',
    label: 'XY2P',
    i: 0,
    j: 0,
    isEdit: true,
    style: defaultStyle,
    img: 'https://jiangsu-10.zos.ctyun.cn/qccp1/lab/gates/XY2P.png',
    type: 'R',
    arguments: ''
  },
  {
    component: 'DefaultGate',
    label: 'XY2M',
    i: 0,
    j: 0,
    isEdit: true,
    style: defaultStyle,
    img: 'https://jiangsu-10.zos.ctyun.cn/qccp1/lab/gates/XY2M.png',
    type: 'R',
    arguments: ''
  },
  {
    component: 'DefaultGate',
    label: 'H',
    i: 0,
    j: 0,
    style: defaultStyle,
    type: 'single',
  },
    {
    component: 'DefaultGate',
    label: 'I',
    i: 0,
    j: 0,
    isEdit: true,
    style: defaultStyle,
    img: '',
    type: 'I',
    t: ''
  },
  {
    component: 'CZGate',
    label: 'CZ',
    i: 0,
    j: 0,
    style: { ...defaultStyle, fill: '#FFB116' },
    type: 'CZ',
  },
   {
    component: 'CXGate',
    label: 'CX',
    i: 0,
    j: 0,
    style: { ...defaultStyle, fill: '#FFB116' },
    type: 'CX',
  },
  {
    component: 'FsimGate',
    label: 'FSIM',
    i: 0,
    j: 0,
    style: { ...defaultStyle, fill: '#FFB116' },
    type: 'CZ',
  },
  {
    component: 'BSuperGate',
    label: 'B',
    i: 0,
    j: 0,
    type: 'BSuper',
    style: defaultStyle,
    isCanEdit: false,
    checkedIds: [],
    sibilings: []
  },
  {
    component: 'MGate',
    label: 'M',
    i: 0,
    j: 0,
    style: { ...defaultStyle, fill: '#E9685D' },
    type: 'single',
  },
];

for (let i = 0, len = list.length; i < len; i++) {
  const item = list[i];
  item.style = { ...commonStyle, ...item.style };
  list[i] = { ...commonAttr, ...item };
}

export default list;
