# -*- coding: utf-8 -*-
"""
生成交互式HTML关系图
用法: python generate_graph_html.py <input.json> <output.html>
input.json 格式:
{
  "nodes": [
    {"id": "entity1", "label": "张三", "type": "person", "detail": "某公司CEO"},
    {"id": "entity2", "label": "某公司", "type": "company", "detail": "科技行业"}
  ],
  "edges": [
    {"source": "entity1", "target": "entity2", "label": "任职"}
  ],
  "title": "张三 - 关系图谱"
}
"""

import json
import sys
import os
import html as html_mod
from datetime import datetime


def escape_js(s):
    """Escape string for safe JS embedding."""
    return html_mod.escape(str(s))


def generate_html(data, output_path):
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    title = data.get("title", "关系图谱")

    # Node type color mapping
    type_colors = {
        "person": "#e74c3c",
        "company": "#3498db",
        "organization": "#2ecc71",
        "event": "#f39c12",
        "project": "#9b59b6",
        "location": "#1abc9c",
        "default": "#95a5a6"
    }

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)

    # Build node type legend
    present_types = list(set(n.get("type", "default") for n in nodes))
    legend_items = []
    for t in present_types:
        color = type_colors.get(t, type_colors["default"])
        label_cn = {
            "person": "人物", "company": "公司", "organization": "组织/机构",
            "event": "事件", "project": "项目", "location": "地点"
        }.get(t, t)
        legend_items.append(f'<span style="display:inline-flex;align-items:center;margin-right:12px;"><span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:{color};margin-right:5px;"></span>{escape_js(label_cn)}</span>')

    legend_html = "\n".join(legend_items)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_js(title)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #0a0a1a; color: #e0e0e0; overflow: hidden; }}
#header {{ position: fixed; top: 0; left: 0; right: 0; z-index: 100; background: rgba(10,10,26,0.92); border-bottom: 1px solid rgba(255,255,255,0.08); padding: 12px 24px; backdrop-filter: blur(10px); }}
#header h1 {{ font-size: 18px; font-weight: 600; color: #fff; }}
#legend {{ margin-top: 6px; font-size: 13px; color: #aaa; }}
#stats {{ position: fixed; top: 60px; right: 16px; z-index: 100; background: rgba(10,10,26,0.85); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #aaa; backdrop-filter: blur(10px); }}
#search {{ position: fixed; top: 60px; left: 16px; z-index: 100; }}
#search input {{ background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 13px; width: 180px; outline: none; }}
#search input:focus {{ border-color: #3498db; }}
#tooltip {{ position: fixed; z-index: 200; background: rgba(20,20,40,0.95); border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 12px 16px; font-size: 13px; max-width: 320px; pointer-events: none; display: none; backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.5); }}
#tooltip .tt-label {{ font-weight: 600; color: #fff; font-size: 15px; margin-bottom: 4px; }}
#tooltip .tt-type {{ color: #aaa; font-size: 12px; margin-bottom: 6px; }}
#tooltip .tt-detail {{ color: #ccc; line-height: 1.5; }}
svg {{ width: 100vw; height: 100vh; }}
.node {{ cursor: pointer; }}
.node circle {{ stroke-width: 2.5; transition: r 0.2s; }}
.node:hover circle {{ stroke-width: 4; }}
.node text {{ fill: #e0e0e0; font-size: 12px; pointer-events: none; text-anchor: middle; }}
.link {{ fill: none; stroke: rgba(255,255,255,0.2); stroke-width: 1.5; }}
.link-label {{ fill: #aaa; font-size: 10px; pointer-events: none; }}
.node.highlighted circle {{ stroke: #fff; stroke-width: 4; }}
.node.dimmed {{ opacity: 0.15; }}
.link.dimmed {{ opacity: 0.05; }}
.link.highlighted {{ stroke: rgba(255,255,255,0.7); stroke-width: 2.5; }}
</style>
</head>
<body>
<div id="header">
  <h1>{escape_js(title)}</h1>
  <div id="legend">{legend_html}</div>
</div>
<div id="stats"></div>
<div id="search"><input type="text" placeholder="搜索节点..." id="searchInput"></div>
<div id="tooltip"><div class="tt-label"></div><div class="tt-type"></div><div class="tt-detail"></div></div>
<svg id="graph"></svg>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const nodes = {nodes_json};
const edges = {edges_json};
const typeColors = {json.dumps(type_colors, ensure_ascii=False)};

const g = d3.select("#graph").append("g");
const zoom = d3.zoom().scaleExtent([0.1, 8]).on("zoom", (e) => g.attr("transform", e.transform));
d3.select("#graph").call(zoom);

const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(edges).id(d => d.id).distance(160))
  .force("charge", d3.forceManyBody().strength(-500))
  .force("center", d3.forceCenter(window.innerWidth/2, window.innerHeight/2))
  .force("collision", d3.forceCollide().radius(40));

const link = g.append("g").selectAll("line").data(edges).join("line").attr("class","link");
const linkLabel = g.append("g").selectAll("text").data(edges).join("text").attr("class","link-label").text(d => d.label || "");
const node = g.append("g").selectAll("g").data(nodes).join("g").attr("class","node")
  .call(d3.drag().on("start",dragStart).on("drag",dragging).on("end",dragEnd));

node.append("circle").attr("r", d => d.type==='person'?18:d.type==='company'?20:16)
  .attr("fill", d => typeColors[d.type]||typeColors.default)
  .attr("stroke", d => d3.color(typeColors[d.type]||typeColors.default).brighter(0.5));

node.append("text").attr("dy", d => (d.type==='person'?18:d.type==='company'?20:16)+14).text(d => d.label);

sim.on("tick", () => {{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  linkLabel.attr("x",d=>(d.source.x+d.target.x)/2).attr("y",d=>(d.source.y+d.target.y)/2-5);
  node.attr("transform",d=>`translate(${{d.x}},${{d.y}})`);
}});

function dragStart(e,d) {{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }}
function dragging(e,d) {{ d.fx=e.x; d.fy=e.y; }}
function dragEnd(e,d) {{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}

// Tooltip
const tooltip = document.getElementById("tooltip");
node.on("mouseover", (e, d) => {{
  tooltip.querySelector(".tt-label").textContent = d.label;
  const typeMap = {{person:"人物",company:"公司",organization:"组织/机构",event:"事件",project:"项目",location:"地点"}};
  tooltip.querySelector(".tt-type").textContent = typeMap[d.type]||d.type;
  tooltip.querySelector(".tt-detail").textContent = d.detail||"";
  tooltip.style.display = "block";
}}).on("mousemove", e => {{
  tooltip.style.left = (e.pageX+15)+"px"; tooltip.style.top = (e.pageY+15)+"px";
}}).on("mouseout", () => {{ tooltip.style.display = "none"; }});

// Highlight connected
node.on("click", (e, d) => {{
  const connected = new Set();
  edges.forEach(l => {{ if(l.source.id===d.id) connected.add(l.target.id); if(l.target.id===d.id) connected.add(l.source.id); }});
  connected.add(d.id);
  node.classed("dimmed", n => !connected.has(n.id)).classed("highlighted", n => n.id===d.id);
  link.classed("dimmed", l => l.source.id!==d.id && l.target.id!==d.id).classed("highlighted", l => l.source.id===d.id || l.target.id===d.id);
}});

d3.select("#graph").on("click", e => {{
  if(e.target.tagName==="svg") {{
    node.classed("dimmed",false).classed("highlighted",false);
    link.classed("dimmed",false).classed("highlighted",false);
  }}
}});

// Search
document.getElementById("searchInput").addEventListener("input", e => {{
  const q = e.target.value.toLowerCase();
  if(!q) {{ node.classed("dimmed",false); link.classed("dimmed",false); return; }}
  const matched = new Set(nodes.filter(n=>n.label.toLowerCase().includes(q)||(n.detail||"").toLowerCase().includes(q)).map(n=>n.id));
  node.classed("dimmed", n=>!matched.has(n.id));
  link.classed("dimmed", l=>!matched.has(l.source.id)&&!matched.has(l.target.id));
}});

// Stats
document.getElementById("stats").innerHTML = `节点: ${{nodes.length}} | 关系: ${{edges.length}}`;
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML关系图已生成: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python generate_graph_html.py <input.json> <output.html>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    generate_html(data, sys.argv[2])
