/*
 * @Author: liu.yihu
 * @Date: 2024-04-20 14:46:44
 * @LastEditors: 刘威
 * @LastEditTime: 2025-09-16 15:00:27
 * @FilePath: \qccp-web\src\views\solution\components\gate\index.js
 * @Description: 操作门
 */
import DefaultGate from './DefaultGate.vue';
import CZGate from './CZGate.vue';
import CXGate from './CXGate.vue';
import MGate from './MGate.vue';
import BGate from './BGate.vue';
import FsimGate from './FsimGate.vue';
import BSuperGate from './BSuperGate.vue';

const components = {
  DefaultGate,
  CZGate,
  CXGate,
  BGate,
  MGate,
  FsimGate,
  BSuperGate

};

const GlobalComponents = app => {
  Object.keys(components).forEach(key => {
    app.component(`${key}`, components[key]);
  });
};

export default GlobalComponents;
