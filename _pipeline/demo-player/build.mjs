// demo.json dosyasından tek parça, bağımsız demo.html üretir.
// Kullanım: node build.mjs <demo.json> <çıktı.html>
import { build } from "esbuild";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const [demoPath, outPath] = process.argv.slice(2);
if (!demoPath || !outPath) {
  console.error("Kullanım: node build.mjs <demo.json> <çıktı.html>");
  process.exit(2);
}
const demo = JSON.parse(readFileSync(demoPath, "utf8"));

const result = await build({
  entryPoints: [join(here, "standalone.tsx")],
  bundle: true,
  minifyWhitespace: true,
  minifySyntax: true,
  minifyIdentifiers: false,
  write: false,
  outdir: "out",
  format: "iife",
  jsx: "automatic",
  loader: { ".module.css": "local-css" },
  define: { "process.env.NODE_ENV": '"production"' },
  logLevel: "error",
});
const js = result.outputFiles.find((f) => f.path.endsWith(".js")).text;
const css = result.outputFiles.find((f) => f.path.endsWith(".css")).text;
const esc = (s) => s.replace(/</g, "\\u003c");
const title = demo.title || "Demo";

const html = `<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title.replace(/</g, "&lt;")}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html,body{margin:0}
body{background:#f2f4f7;font-family:"IBM Plex Sans",-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
@media (prefers-color-scheme:dark){body{background:#0b0e13}}
#root{max-width:1180px;margin:0 auto;padding:16px}
${css}
</style>
</head>
<body>
<div id="root"></div>
<script id="demo-data" type="application/json">${esc(JSON.stringify(demo))}</script>
<script>${js}</script>
</body>
</html>
`;
writeFileSync(outPath, html);
console.log(`Yazıldı: ${outPath} (${Math.round(html.length / 1024)} KB)`);
