#!/usr/bin/env python3
"""
TeleAgent 工作赋能分析 HTML报告生成器
输入: 分析结果JSON
输出: 可视化HTML单页
"""
import json
import sys
from datetime import datetime

def generate_html(analysis_data, output_path):
    """从分析结果JSON生成HTML报告"""

    user_name = analysis_data.get("user_name", "用户")
    department = analysis_data.get("department", "")
    analysis_date = analysis_data.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))
    material_summary = analysis_data.get("material_summary", "")
    work_items = analysis_data.get("work_items", [])
    work_direction = analysis_data.get("work_direction", {})
    overall_assessment = analysis_data.get("overall_assessment", {})

    # Stats
    total_items = len(work_items)
    s_count = sum(1 for w in work_items if w.get("fitness_grade") == "S")
    a_count = sum(1 for w in work_items if w.get("fitness_grade") == "A")
    b_count = sum(1 for w in work_items if w.get("fitness_grade") == "B")

    avg_fitness = sum(w.get("fitness_score", 0) for w in work_items) / max(total_items, 1)
    total_saving = sum(w.get("saving_hours_per_week", 0) for w in work_items)

    grade_colors = {"S": "#E74C3C", "A": "#F5A623", "B": "#0077BE", "C": "#8E44AD", "D": "#999"}
    star_colors = {5: "#E74C3C", 4: "#F5A623", 3: "#27AE60", 2: "#0077BE", 1: "#999"}

    def stars(n):
        return "★" * n + "☆" * (5 - n)

    def dim_bar(value, color):
        return f'''<div class="dim-bar-track"><div class="dim-bar-fill" style="width:{value}%;background:{color};"></div></div>'''

    def prompt_card(prompt_text, desc):
        escaped = prompt_text.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        return f'''<div class="prompt-card"><div class="prompt-text">{escaped}</div><div class="prompt-desc">{desc}</div></div>'''

    work_items_html = ""
    for i, w in enumerate(work_items):
        grade = w.get("fitness_grade", "C")
        score = w.get("fitness_score", 0)
        name = w.get("name", f"工作项{i+1}")
        description = w.get("description", "")
        current_status = w.get("current_status", "")
        optimized_approach = w.get("optimized_approach", "")
        saving = w.get("saving_hours_per_week", 0)
        optimization_stars = w.get("optimization_stars", 3)
        matched_skills = w.get("matched_skills", [])
        prompts = w.get("recommended_prompts", [])
        dimensions = w.get("dimensions", {})

        d1 = dimensions.get("automation_potential", 50)
        d2 = dimensions.get("skill_coverage", 50)
        d3 = dimensions.get("repetitiveness", 50)
        d4 = dimensions.get("time_weight", 50)
        d5 = dimensions.get("quality_sensitivity", 50)

        skill_tags = ""
        for s in matched_skills:
            sid = s.get("id", "")
            sname = s.get("name", "")
            match_level = s.get("match_level", "partial")
            badge_cls = "badge-match" if match_level == "exact" else "badge-partial"
            tag_cls = "tool-skill" if match_level == "exact" else "tool-feature"
            skill_tags += f'<span class="tool-tag {tag_cls}">@{sname} <span class="sm-badge {badge_cls}">{("精准" if match_level=="exact" else "近似")}</span></span> '

        prompt_cards = ""
        for p in prompts:
            prompt_cards += prompt_card(p.get("prompt", ""), p.get("scenario", ""))

        work_items_html += f'''
    <div class="work-card" data-grade="{grade}">
      <div class="work-header">
        <div class="work-title"><span class="idx" style="background:{grade_colors.get(grade,'#999')}">{i+1}</span>{name}</div>
        <div class="work-badges">
          <span class="grade-badge" style="background:{grade_colors.get(grade,'#999')}">{grade}级</span>
          <span class="fitness-score">适配度 {score}分</span>
          <span class="optimize-stars" style="color:{star_colors.get(optimization_stars,'#999')}">{stars(optimization_stars)}</span>
        </div>
      </div>
      <p class="work-desc">{description}</p>
      <div class="work-detail-grid">
        <div class="detail-col">
          <div class="detail-label detail-current">现状分析</div>
          <div class="detail-content">{current_status}</div>
          <div class="detail-label detail-optimize" style="margin-top:16px;">优化方案</div>
          <div class="detail-content">{optimized_approach}</div>
        </div>
        <div class="detail-col">
          <div class="detail-label">五维适配度</div>
          <div class="dim-row"><span class="dim-name">自动化潜力</span>{dim_bar(d1,"#0077BE")}<span class="dim-val">{d1}</span></div>
          <div class="dim-row"><span class="dim-name">技能覆盖度</span>{dim_bar(d2,"#27AE60")}<span class="dim-val">{d2}</span></div>
          <div class="dim-row"><span class="dim-name">重复性</span>{dim_bar(d3,"#F5A623")}<span class="dim-val">{d3}</span></div>
          <div class="dim-row"><span class="dim-name">耗时占比</span>{dim_bar(d4,"#8E44AD")}<span class="dim-val">{d4}</span></div>
          <div class="dim-row"><span class="dim-name">质量敏感度</span>{dim_bar(d5,"#E74C3C")}<span class="dim-val">{d5}</span></div>
          <div class="saving-badge">预计每周省时 <strong>{saving}h</strong></div>
        </div>
      </div>
      <div class="skill-match-area">
        <div class="detail-label">匹配技能</div>
        <div class="skill-tags">{skill_tags}</div>
      </div>
      <div class="prompt-area">
        <div class="detail-label">推荐提示词案例</div>
        <div class="prompt-grid">{prompt_cards}</div>
      </div>
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{user_name} · 工作赋能分析报告</title>
<style>
:root{{--ct-blue:#0077BE;--ct-dark:#003D7A;--ct-light:#E8F4FD;--ct-accent:#00A6ED;--ct-orange:#F5A623;--ct-green:#27AE60;--ct-red:#E74C3C;--ct-purple:#8E44AD;--gray-50:#FAFAFA;--gray-100:#F5F5F5;--gray-200:#E0E0E0;--gray-500:#999;--gray-600:#666;--gray-800:#333;--shadow:0 2px 12px rgba(0,119,190,0.08);--shadow-hover:0 6px 24px rgba(0,119,190,0.15)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:var(--gray-50);color:var(--gray-800);line-height:1.7}}
.hero{{background:linear-gradient(135deg,var(--ct-dark) 0%,var(--ct-blue) 50%,var(--ct-accent) 100%);color:#fff;padding:50px 40px 40px;text-align:center}}
.hero h1{{font-size:2.2em;margin-bottom:8px}}
.hero .sub{{opacity:0.9;font-size:1em}}
.hero .meta{{display:flex;justify-content:center;gap:20px;margin-top:20px;flex-wrap:wrap}}
.hero .mi{{background:rgba(255,255,255,0.15);backdrop-filter:blur(10px);border-radius:12px;padding:10px 22px;font-size:0.9em}}
.hero .mi span{{font-weight:700;font-size:1.3em;color:var(--ct-orange)}}
.nav{{background:#fff;border-bottom:1px solid var(--gray-200);position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.06);display:flex;gap:0;overflow-x:auto}}
.nav-tab{{padding:14px 26px;cursor:pointer;font-size:0.93em;font-weight:500;color:var(--gray-600);border-bottom:3px solid transparent;transition:all 0.3s;white-space:nowrap}}
.nav-tab:hover{{color:var(--ct-blue)}}
.nav-tab.active{{color:var(--ct-blue);border-bottom-color:var(--ct-blue);font-weight:600}}
.container{{max-width:1200px;margin:0 auto;padding:30px 24px}}
.section{{display:none;animation:fadeIn 0.4s ease}}
.section.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.stitle{{font-size:1.5em;font-weight:700;color:var(--ct-dark);margin-bottom:6px;display:flex;align-items:center;gap:10px}}
.sdesc{{color:var(--gray-600);margin-bottom:24px;font-size:0.92em}}
.ov-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:30px}}
.ov-card{{background:#fff;border-radius:14px;padding:20px;box-shadow:var(--shadow);border-left:4px solid var(--ct-blue)}}
.ov-card .num{{font-size:2em;font-weight:800;color:var(--ct-blue)}}
.ov-card .label{{font-size:0.85em;color:var(--gray-600)}}
.material-summary{{background:#fff;border-radius:14px;padding:20px;box-shadow:var(--shadow);margin-bottom:24px;font-size:0.92em;line-height:1.8}}
.work-card{{background:#fff;border-radius:16px;padding:24px;margin-bottom:28px;box-shadow:var(--shadow);transition:all 0.3s}}
.work-card:hover{{box-shadow:var(--shadow-hover)}}
.work-header{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px}}
.work-title{{font-size:1.15em;font-weight:700;color:var(--ct-dark);display:flex;align-items:center;gap:8px}}
.idx{{width:28px;height:28px;color:#fff;border-radius:7px;display:inline-flex;align-items:center;justify-content:center;font-size:0.85em;flex-shrink:0}}
.work-badges{{display:flex;align-items:center;gap:10px}}
.grade-badge{{padding:3px 12px;border-radius:12px;color:#fff;font-size:0.82em;font-weight:700}}
.fitness-score{{font-size:0.85em;font-weight:600;color:var(--ct-blue)}}
.optimize-stars{{font-size:0.9em;letter-spacing:2px}}
.work-desc{{color:var(--gray-600);font-size:0.9em;margin-bottom:16px}}
.detail-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:768px){{.detail-grid{{grid-template-columns:1fr}}}}
.detail-col{{}}
.detail-label{{font-size:0.78em;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;display:flex;align-items:center;gap:6px}}
.detail-current{{color:var(--ct-red)}}
.detail-optimize{{color:var(--ct-green)}}
.detail-content{{font-size:0.88em;line-height:1.8;color:var(--gray-800)}}
.dim-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.dim-name{{width:80px;font-size:0.78em;color:var(--gray-600);text-align:right;flex-shrink:0}}
.dim-bar-track{{flex:1;height:8px;background:var(--gray-100);border-radius:4px;overflow:hidden}}
.dim-bar-fill{{height:100%;border-radius:4px;transition:width 1s ease}}
.dim-val{{width:28px;font-size:0.78em;font-weight:600;text-align:right;flex-shrink:0}}
.saving-badge{{margin-top:12px;background:var(--ct-light);border-radius:10px;padding:10px 16px;font-size:0.88em;color:var(--ct-dark)}}
.saving-badge strong{{color:var(--ct-green);font-size:1.2em}}
.skill-match-area{{margin-top:16px}}
.detail-label{{font-size:0.78em;font-weight:700;letter-spacing:1.5px;margin-bottom:8px;color:var(--gray-600)}}
.skill-tags{{display:flex;flex-wrap:wrap;gap:6px}}
.tool-tag{{display:inline-block;padding:3px 10px;border-radius:6px;font-size:0.8em;font-weight:600}}
.tool-skill{{background:var(--ct-light);color:var(--ct-blue)}}
.tool-feature{{background:#F3E5F5;color:var(--ct-purple)}}
.sm-badge{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:0.7em;font-weight:700;margin-left:4px}}
.badge-match{{background:#E8F5E9;color:var(--ct-green)}}
.badge-partial{{background:#FFF3E0;color:var(--ct-orange)}}
.prompt-area{{margin-top:16px}}
.prompt-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}}
.prompt-card{{background:var(--gray-100);border-radius:10px;padding:14px 16px;border:1px solid var(--gray-200)}}
.prompt-text{{font-size:0.88em;font-weight:600;color:var(--ct-dark);margin-bottom:4px;font-family:'SF Mono','Fira Code',monospace;word-break:break-all}}
.prompt-desc{{font-size:0.78em;color:var(--gray-600)}}
.direction-box{{background:#fff;border-radius:14px;padding:22px;box-shadow:var(--shadow);margin-bottom:20px}}
.direction-box h3{{font-size:1.1em;color:var(--ct-dark);margin-bottom:10px}}
.direction-box p{{font-size:0.9em;color:var(--gray-600);line-height:1.8}}
.assess-box{{background:linear-gradient(135deg,var(--ct-light),#fff);border:2px solid var(--ct-blue);border-radius:14px;padding:24px;margin:20px 0}}
.assess-box h3{{color:var(--ct-blue);font-size:1.15em;margin-bottom:12px}}
.assess-box ul{{padding-left:20px}}
.assess-box li{{margin-bottom:6px;font-size:0.9em}}
.radar-chart{{text-align:center;padding:20px}}
.radar-placeholder{{width:300px;height:300px;margin:0 auto;background:var(--gray-100);border-radius:50%;display:flex;align-items:center;justify-content:center;color:var(--gray-600);font-size:0.9em}}
.footer{{background:var(--ct-dark);color:rgba(255,255,255,0.7);text-align:center;padding:24px;font-size:0.82em;margin-top:50px}}
.footer strong{{color:#fff}}
.gap-card{{background:#fff;border-radius:14px;padding:20px;box-shadow:var(--shadow);margin-bottom:16px;border-left:4px solid var(--ct-orange)}}
.gap-card h4{{color:var(--ct-orange);margin-bottom:6px}}
.gap-card p{{font-size:0.88em;color:var(--gray-600)}}
</style>
</head>
<body>
<div class="hero">
  <h1>{user_name} · 工作赋能分析</h1>
  <div class="sub">基于工作材料的TeleAgent能力全量匹配 · {"电信" if department else "行业"}场景深度适配</div>
  <div class="meta">
    <div class="mi">分析项目 <span>{total_items}</span></div>
    <div class="mi">平均适配度 <span>{avg_fitness:.0f}</span></div>
    <div class="mi">周省时 <span>{total_saving:.1f}h</span></div>
    <div class="mi">S/A级 <span>{s_count+a_count}</span></div>
  </div>
</div>
<div class="nav">
  <div class="nav-tab active" onclick="showTab('overview')">总览</div>
  <div class="nav-tab" onclick="showTab('detail')">逐项分析</div>
  <div class="nav-tab" onclick="showTab('direction')">工作方向分析</div>
</div>
<div class="container">

<!-- OVERVIEW -->
<div class="section active" id="overview">
  <div class="stitle">总览</div>
  <div class="sdesc">从工作材料中提取的核心指标</div>
  <div class="ov-grid">
    <div class="ov-card" style="border-color:var(--ct-red)"><div class="num" style="color:var(--ct-red)">{s_count}</div><div class="label">S级（深度适配）</div></div>
    <div class="ov-card" style="border-color:var(--ct-orange)"><div class="num" style="color:var(--ct-orange)">{a_count}</div><div class="label">A级（高度适配）</div></div>
    <div class="ov-card" style="border-color:var(--ct-blue)"><div class="num" style="color:var(--ct-blue)">{b_count}</div><div class="label">B级（中度适配）</div></div>
    <div class="ov-card" style="border-color:var(--ct-green)"><div class="num" style="color:var(--ct-green)">{total_saving:.1f}h</div><div class="label">每周可省时间</div></div>
  </div>
  <div class="material-summary">
    <strong>材料摘要：</strong>{material_summary}
  </div>
  <div class="assess-box">
    <h3>综合评估</h3>
    <ul>
      <li><strong>整体适配度：{avg_fitness:.0f}分</strong>（{"S级-深度适配" if avg_fitness>=85 else "A级-高度适配" if avg_fitness>=70 else "B级-中度适配" if avg_fitness>=55 else "C级-低度适配"}）</li>
      <li><strong>最高提效场景：</strong>{work_items[0]["name"] if work_items else "N/A"}（适配度{work_items[0]["fitness_score"] if work_items else 0}分）</li>
      <li><strong>技能覆盖率：</strong>{len(set(s["id"] for w in work_items for s in w.get("matched_skills",[])))/(len(work_items)*3)*100:.0f}%（匹配技能数/理论需求技能数×3）</li>
    </ul>
  </div>
</div>

<!-- DETAIL -->
<div class="section" id="detail">
  <div class="stitle">逐项分析</div>
  <div class="sdesc">每项工作内容 → 现状 → 五维适配度 → 匹配技能 → 优化方案 → 推荐提示词</div>
  {work_items_html}
</div>

<!-- DIRECTION -->
<div class="section" id="direction">
  <div class="stitle">工作方向与能力分析</div>
  <div class="sdesc">基于工作材料的整体能力画像与发展建议</div>
  <div class="direction-box">
    <h3>工作方向分析</h3>
    <p>{work_direction.get("direction_analysis","")}</p>
  </div>
  <div class="direction-box">
    <h3>核心能力画像</h3>
    <p>{work_direction.get("capability_profile","")}</p>
  </div>
  <div class="direction-box">
    <h3>TeleAgent赋能策略</h3>
    <p>{work_direction.get("empowerment_strategy","")}</p>
  </div>
  <div class="direction-box">
    <h3>优先实施路径</h3>
    <p>{work_direction.get("implementation_path","")}</p>
  </div>
  <div class="stitle" style="margin-top:28px;">能力缺口与建议</div>
  {"".join(f'<div class="gap-card"><h4>{g.get("title","")}</h4><p>{g.get("description","")}</p></div>' for g in work_direction.get("gaps",[]))}
</div>
</div>
<div class="footer"><strong>{user_name} · 工作赋能分析报告</strong> | {department} | TeleAgent星辰超级智能体 | {analysis_date}</div>
<script>
function showTab(id){{document.querySelectorAll('.section').forEach(function(s){{s.classList.remove('active')}});document.querySelectorAll('.nav-tab').forEach(function(t){{t.classList.remove('active')}});document.getElementById(id).classList.add('active');var map={{overview:0,detail:1,direction:2}};document.querySelectorAll('.nav-tab')[map[id]].classList.add('active');window.scrollTo({{top:document.querySelector('.nav').offsetTop,behavior:'smooth'}});}}
</script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML report generated: {output_path}")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_html.py <analysis.json> <output.html>")
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        data = json.load(f)
    generate_html(data, sys.argv[2])
