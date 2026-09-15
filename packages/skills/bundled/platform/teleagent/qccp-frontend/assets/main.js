/*
 * @Author: liyu
 * @Date: 2024-05-27 09:10:01
 * @LastEditors: Do not edit
 * @LastEditTime: 2024-06-04 17:54:43
 */
/* eslint-disable global-require */
import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import zhLocale from 'element-plus/dist/locale/zh-cn.mjs';
import App from './App.vue';
import router from './router';
// import store from './store/index.js';
import 'element-plus/theme-chalk/index.css';
import '@/assets/style/global.css';
import axios from './utils/axios';
import { createPinia } from 'pinia';
import 'vant/lib/index.css';
import { NoticeBar, Swipe, SwipeItem } from 'vant';
import GlobalComponents from './views/solution/components/gate/index' // 注

import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import i18n from '@/utils/lang/index.js'
import '@/assets/fonts/fonts.css'
window.name = 'tianYan';
// import Moment from 'moment'
//定义一个全局过滤器实现日期格式化
// Vue.filter('comverTime',function(data,format){
//   return Moment.unix(data).format(format);
// });

// import '@/mock';
const pinia = createPinia();
const app = createApp(App);

const baseOrigin = import.meta.env.VITE_APP_PAGE_BASE_URL;
app.config.globalProperties.$baseOrigin = baseOrigin;

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
app.use(ElementPlus, {
  locale: zhLocale,
});
app.use(i18n)
app
  .use(pinia)
  .use(router)
  .use(GlobalComponents)
  .use(NoticeBar)
  .use(Swipe)
  .use(SwipeItem)
  .mount('#app');
app.config.globalProperties.$axios = axios;
