/**
 * excel-data-utils.js — Excel 数据→PPT 工具函数库
 * v6.0 新增 | Layer 1 · 数据智能层
 * 
 * 供电信PPT大师在代码生成阶段引用，提供：
 * 1. 数字格式化（千分位、百分比、金额等）
 * 2. 表格自动生成（含条件格式、交替行色、汇总行）
 * 3. 自动数据点评生成
 * 4. KPI 卡片数据格式化
 */

// ============================================================
// §1 数字格式化
// ============================================================

/**
 * 千分位格式化
 * @param {number} val 数值
 * @returns {string} 如 "35,877"
 */
function fmtThousands(val) {
  if (val == null || isNaN(val)) return '-';
  return Number(val).toLocaleString('zh-CN');
}

/**
 * 百分比格式化
 * @param {number} val 小数形式（0.164 → "16.4%"）
 * @param {number} digits 小数位数，默认1
 * @returns {string}
 */
function fmtPercent(val, digits = 1) {
  if (val == null || isNaN(val)) return '-';
  return (Number(val) * 100).toFixed(digits) + '%';
}

/**
 * 同比/环比格式化（带正负号）
 * @param {number} val 变化值（百分点或百分比）
 * @param {boolean} isPercent true=百分点，false=绝对值
 * @returns {string} 如 "+3.2%" / "-1.5%"
 */
function fmtChange(val, isPercent = true) {
  if (val == null || isNaN(val)) return '-';
  const sign = val >= 0 ? '+' : '';
  return sign + (isPercent ? Number(val).toFixed(1) + '%' : sign + fmtThousands(val));
}

/**
 * 金额格式化
 * @param {number} val 金额（万元）
 * @returns {string} 如 "300.5万"
 */
function fmtMoney(val) {
  if (val == null || isNaN(val)) return '-';
  return Number(val).toFixed(1) + '万';
}

/**
 * 电信风格数字强调（红色加粗+黄底）
 * @param {string|number} text 数字文本
 * @param {boolean} withBg 是否添加黄底，默认 true
 * @returns {object} pptxgenjs text fragment
 */
function fmtNumber(text, withBg = true) {
  return {
    text: String(text),
    options: {
      color: 'C00000',
      bold: true,
      fontSize: 12,
      ...(withBg ? { highlight: 'FFFF00' } : {})
    }
  };
}

// ============================================================
// §2 表格自动生成
// ============================================================

/**
 * 生成带条件格式的表格行数据
 * @param {object} data { headers: [], rows: [[]], summaryRow: [] }
 * @param {object} contract Table Contract 配置
 * @param {object} theme 主题配色 { primary, iceLight, border, headerBg, ... }
 * @returns {array} pptxgenjs addTable 所需的行数组
 */
function buildTableRows(data, contract, theme) {
  const { ColSpec, RowSpec, ConditionFormat } = contract;
  const rows = [];

  // ---- 表头行 ----
  const headerRow = data.headers.map((h, i) => ({
    text: h,
    options: {
      bold: true,
      color: 'FFFFFF',
      fill: { color: theme.headerBg || 'C00000' },
      fontSize: 10,
      align: ColSpec[i]?.align || 'center',
      fontFace: 'Microsoft YaHei'
    }
  }));
  rows.push(headerRow);

  // ---- 数据行 ----
  data.rows.forEach((row, rowIdx) => {
    const isTop3 = ConditionFormat?.topN && rowIdx < ConditionFormat.topN;
    const isBottom = ConditionFormat?.bottomN && rowIdx >= data.rows.length - ConditionFormat.bottomN;
    
    const dataRow = row.map((cell, colIdx) => {
      const spec = ColSpec[colIdx] || {};
      let options = {
        fontSize: RowSpec?.data?.fontSize || 9,
        align: spec.align || 'center',
        fontFace: 'Microsoft YaHei'
      };

      // 条件格式：Top N 标红
      if (isTop3) {
        options.color = 'C00000';
        options.bold = true;
        options.fill = { color: theme.iceLight || 'FFF0F0' };
      }
      // 条件格式：末 N 标灰
      if (isBottom) {
        options.color = '999999';
      }
      // 条件格式：负值标红
      if (ConditionFormat?.negativeRed && typeof cell === 'number' && cell < 0) {
        options.color = 'C00000';
      }
      // 条件格式：阈值高亮
      if (ConditionFormat?.threshold && typeof cell === 'number') {
        if (cell >= ConditionFormat.threshold.high) {
          options.color = '00B050'; // 绿色
        } else if (cell <= ConditionFormat.threshold.low) {
          options.color = 'C00000'; // 红色
        }
      }

      // 交替行（非 Top3 行）
      if (!isTop3 && rowIdx % 2 === 1) {
        options.fill = { color: theme.altRow || 'FFF0F0' };
      }

      // 数字格式化
      let displayText = String(cell);
      if (typeof cell === 'number') {
        if (spec.format === '千分位') displayText = fmtThousands(cell);
        else if (spec.format === '百分比') displayText = fmtPercent(cell);
        else if (spec.format === '金额') displayText = fmtMoney(cell);
      }

      return { text: displayText, options };
    });
    rows.push(dataRow);
  });

  // ---- 汇总行 ----
  if (data.summaryRow) {
    const summaryRow = data.summaryRow.map((cell, colIdx) => {
      const spec = ColSpec[colIdx] || {};
      let displayText = String(cell);
      if (typeof cell === 'number') {
        if (spec.format === '千分位') displayText = fmtThousands(cell);
        else if (spec.format === '百分比') displayText = fmtPercent(cell);
      }
      return {
        text: displayText,
        options: {
          bold: true,
          fontSize: 10,
          fill: { color: 'F5F5F5' },
          align: spec.align || 'center',
          fontFace: 'Microsoft YaHei'
        }
      };
    });
    rows.push(summaryRow);
  }

  return rows;
}

/**
 * 计算 Table Contract 的列宽数组
 * @param {number} totalWidth 表格总宽度（英寸）
 * @param {array} colSpec ColSpec 数组
 * @returns {array} 列宽数组（英寸）
 */
function calcColWidths(totalWidth, colSpec) {
  const fixedWidth = colSpec.filter(c => c.w).reduce((sum, c) => sum + c.w, 0);
  const remaining = totalWidth - fixedWidth;
  const flexibleCount = colSpec.filter(c => !c.w).length;
  const flexibleWidth = flexibleCount > 0 ? remaining / flexibleCount : 0;
  return colSpec.map(c => c.w || flexibleWidth);
}

// ============================================================
// §3 自动数据点评
// ============================================================

/**
 * 生成极值点评
 * @param {array} data [{ name, value }, ...]
 * @param {string} unit 单位
 * @returns {string} 如 "合肥以35,877户领先，淮北1,256户垫底"
 */
function commentExtremes(data, unit = '户') {
  if (!data || data.length < 2) return '';
  const sorted = [...data].sort((a, b) => b.value - a.value);
  const max = sorted[0];
  const min = sorted[sorted.length - 1];
  return `${max.name}以${fmtThousands(max.value)}${unit}领先，${min.name}${fmtThousands(min.value)}${unit}垫底`;
}

/**
 * 生成排名点评（Top3）
 * @param {array} data [{ name, value }, ...]
 * @param {string} unit 单位
 * @returns {string}
 */
function commentTop3(data, unit = '户') {
  const sorted = [...data].sort((a, b) => b.value - a.value);
  const top3 = sorted.slice(0, 3);
  return `前三名：${top3.map(d => d.name + fmtThousands(d.value) + unit).join('、')}`;
}

/**
 * 生成结构点评（集中度）
 * @param {array} data [{ name, value }, ...]
 * @param {number} topN 前N名
 * @returns {string} 如 "前3名合计占比51.2%，集中度较高"
 */
function commentConcentration(data, topN = 3) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const sorted = [...data].sort((a, b) => b.value - a.value);
  const topSum = sorted.slice(0, topN).reduce((sum, d) => sum + d.value, 0);
  const pct = ((topSum / total) * 100).toFixed(1);
  return `前${topN}名合计占比${pct}%，${parseFloat(pct) > 50 ? '集中度较高' : '分布相对均衡'}`;
}

/**
 * 生成预警点评
 * @param {number} value 当前值
 * @param {number} threshold 阈值
 * @param {string} metric 指标名
 * @param {string} direction 'below' 或 'above'
 * @returns {string}
 */
function commentAlert(value, threshold, metric, direction = 'below') {
  if (direction === 'below' && value < threshold) {
    return `${metric}仅${fmtPercent(value / 100)}，低于${fmtPercent(threshold / 100)}警戒线`;
  }
  if (direction === 'above' && value > threshold) {
    return `${metric}达${fmtPercent(value / 100)}，超过${fmtPercent(threshold / 100)}预警线`;
  }
  return '';
}

// ============================================================
// §4 KPI 卡片数据格式化
// ============================================================

/**
 * 构建 KPI 卡片数据
 * @param {array} kpis [{ label, value, unit, change, changeUnit }]
 * @param {object} options { withBg, showChange, changeColor }
 * @returns {array} pptxgenjs text fragments
 */
function buildKPIData(kpis, options = {}) {
  return kpis.map(kpi => {
    const fragments = [];
    
    // 数值
    fragments.push({
      text: typeof kpi.value === 'number' ? fmtThousands(kpi.value) : String(kpi.value),
      options: {
        fontSize: 28,
        color: options.color || 'C00000',
        bold: true,
        fontFace: 'Arial'
      }
    });
    
    // 单位
    if (kpi.unit) {
      fragments.push({
        text: kpi.unit,
        options: { fontSize: 12, color: '666666' }
      });
    }
    
    // 变化趋势
    if (options.showChange && kpi.change != null) {
      const isUp = kpi.change >= 0;
      fragments.push({
        text: ` ${isUp ? '↑' : '↓'}${Math.abs(kpi.change)}${kpi.changeUnit || '%'}`,
        options: {
          fontSize: 10,
          color: isUp ? '00B050' : 'C00000',
          bold: true
        }
      });
    }
    
    return fragments;
  });
}

// ============================================================
// §5 导出
// ============================================================

// 当作为模块使用时导出所有函数
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    fmtThousands, fmtPercent, fmtChange, fmtMoney, fmtNumber,
    buildTableRows, calcColWidths,
    commentExtremes, commentTop3, commentConcentration, commentAlert,
    buildKPIData
  };
}
