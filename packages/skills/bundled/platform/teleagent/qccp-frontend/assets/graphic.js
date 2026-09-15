/*
 * @Author: liu.yihu
 * @Date: 2024-04-20 14:46:44
 * @LastEditors: Jie Zhuo
 * @LastEditTime: 2024-05-22 14:03:51
 * @FilePath: \qccp_lab\src\store\graphic.js
 * @Description: 图形化编程
 */
import { defineStore } from 'pinia';

// eslint-disable-next-line import/prefer-default-export
export const graphicStore = defineStore('graphic', {
  state: () => ({
    componentData: [],
    curComponent: null,
    scrollbarRef: null,
    pointLayout: [],
    gateLayout: [],
    menuShow: false,
    menuTop: 0, // 右击菜单数据
    menuLeft: 0,
    // 如果没点中组件，并且在画布空白处弹起鼠标，则取消当前组件的选中状态
    isClickComponent: false,
    copyData: null, // 复制粘贴剪切
    isCut: false,
    rxParams:0,//RX的参数,
    disabledQubitsQ:[],
    isqWhichLan:'QCIS',//语言切换
    maxQubit:66
  }),
  actions: {
    updatePointLayout(pointsArr) {
      this.pointLayout = pointsArr;
    },
    updateGateLayout(Arr) {
      this.gateLayout = Arr;
    },
    addComponent(component) {
      this.componentData.push(component);
    },
    updateComponent(components) {
      this.componentData = components;
    },
    setCurComponent(component) {
      this.curComponent = component;
      // this.curComponentIndex = index
    },
    setScrollbarRef(scrollbarRef) {
      // this.scrollbarRef = scrollbarRef;
      // this.curComponentIndex = index
    },
    showContextMenu(left,top) {
      this.menuShow = true
      this.menuTop = top
      this.menuLeft = left
    },
    hideContextMenu() {
      this.menuShow = false
    },
    setClickComponentStatus(status) {
      this.isClickComponent = status
    },
  },
});
