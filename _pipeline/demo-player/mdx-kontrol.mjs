// MDX derleme kontrolü: node mdx-kontrol.mjs <dosya.mdx>
import { compile } from "@mdx-js/mdx";
import remarkGfm from "remark-gfm";
import { readFileSync } from "node:fs";
const raw = readFileSync(process.argv[2], "utf8").replace(/^---[\s\S]*?---\n/, "");
try {
  await compile(raw, { remarkPlugins: [remarkGfm] });
  console.log("MDX derlemesi tamam");
} catch (e) {
  console.error("MDX hatası:", e.message);
  process.exit(1);
}
