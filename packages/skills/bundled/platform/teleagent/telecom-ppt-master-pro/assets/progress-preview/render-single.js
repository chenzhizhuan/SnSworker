// =====================================================================
// 单页渲染子进程 · 接受页索引进行单页构建并导出 PNG
//
// 调用方式（由 runner.js fork）:
//   process.argv[2] = pagesModulePath   生成脚本模块路径
//   process.argv[3] = pageIdx           0-based 页索引
//   process.argv[4] = outPngPath        输出 PNG 绝对路径
//   process.argv[5] = themeName         主题名
//
// 流程:
//   1. require(pagesModule) → { deckMeta, setup, buildSlides }
//   2. 构造独立 pres + 主题
//   3. 执行 buildSlides[pageIdx](pres, ctx)
//   4. writeFile 临时 pptx
//   5. 调 render-worker.ps1 导出 PNG
//   6. process.send { ok, thumbnail, renderMs } 给父进程
// =====================================================================
"use strict";

const path = require("path");
const fs = require("fs");
const os = require("os");
const { spawn } = require("child_process");
const pptxgen = require("pptxgenjs");
const { setup } = require("./lib/themes");

async function main() {
  const [, , pagesModulePath, pageIdxStr, outPngPath, themeName] = process.argv;
  const pageIdx = parseInt(pageIdxStr, 10);
  if (!pagesModulePath || isNaN(pageIdx) || !outPngPath) {
    process.send && process.send({ ok: false, error: "参数缺失" });
    process.exit(2);
  }

  const t0 = Date.now();
  // 1. 加载 pages 模块
  let pages;
  try {
    delete require.cache[require.resolve(path.resolve(pagesModulePath))];
    pages = require(path.resolve(pagesModulePath));
  } catch (e) {
    process.send && process.send({ ok: false, error: "加载 pages 模块失败: " + e.message });
    process.exit(3);
  }
  if (!pages.buildSlides || !pages.buildSlides[pageIdx]) {
    process.send && process.send({ ok: false, error: `页索引 ${pageIdx} 不存在 buildSlides` });
    process.exit(4);
  }

  // 2. 构造 pres + 主题
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  if (pages.deckMeta) {
    pres.title = pages.deckMeta.title || "Preview";
    pres.author = pages.deckMeta.author || "";
  }
  const ctx = setup(pres, themeName || pages.deckMeta?.theme || "telecom-red");

  // 3. 执行该页构建
  try {
    pages.buildSlides[pageIdx](pres, ctx);
  } catch (e) {
    process.send && process.send({ ok: false, error: "构建第 " + (pageIdx + 1) + " 页失败: " + e.message });
    process.exit(5);
  }

  // 4. 输出临时 pptx
  const tmpDir = path.join(os.tmpdir(), "ppt-preview-cache");
  if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });
  const tmpPptx = path.join(tmpDir, `preview-${process.pid}-${pageIdx}.pptx`);
  try {
    await pres.writeFile({ fileName: tmpPptx });
  } catch (e) {
    process.send && process.send({ ok: false, error: "writeFile 失败: " + e.message });
    process.exit(6);
  }

  // 调用渲染脚本（仅操作 PowerPoint COM 导出 PNG，不涉及文件删除/进程终止）
  const ps1 = path.join(__dirname, "render-worker.ps1");
  const result = await new Promise((resolve) => {
    const args = [
      "-ExecutionPolicy", "RemoteSigned",
      "-NoProfile",
      "-File", ps1,
      "-PptxPath", tmpPptx,
      "-OutPath", outPngPath,
      "-PageIdx", "1",
    ];
    const child = spawn("powershell", args, { windowsHide: true });
    let stdout = "", stderr = "";
    child.stdout.on("data", (d) => { stdout += d.toString(); });
    child.stderr.on("data", (d) => { stderr += d.toString(); });
    child.on("error", (e) => resolve({ ok: false, error: "spawn 失败: " + e.message }));
    child.on("close", (code) => {
      if (code === 0 && fs.existsSync(outPngPath)) {
        resolve({ ok: true });
      } else {
        const m = (stderr || stdout || "").split("\n").filter(l => l.trim()).slice(-3).join(" | ");
        resolve({ ok: false, error: `PS退出码=${code} ${m}` });
      }
    });
  });

  // 清理临时 pptx
  try { fs.unlinkSync(tmpPptx); } catch (_) {}

  const renderMs = Date.now() - t0;
  if (result.ok) {
    process.send && process.send({ ok: true, thumbnail: outPngPath, renderMs });
    process.exit(0);
  } else {
    process.send && process.send({ ok: false, error: result.error, renderMs });
    process.exit(7);
  }
}

main().catch((e) => {
  process.send && process.send({ ok: false, error: "未捕获异常: " + e.message });
  process.exit(99);
});
