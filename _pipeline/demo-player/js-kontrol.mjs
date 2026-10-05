// HTML içindeki satır içi <script> bloklarının sözdizimini denetler: node js-kontrol.mjs <dosya.html>...
import { readFileSync } from "node:fs";
let hata = 0;
for (const yol of process.argv.slice(2)) {
  const html = readFileSync(yol, "utf8");
  const bloklar = [...html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  for (const kod of bloklar) {
    try { new Function(kod); } catch (e) { console.error(`${yol}: ${e.message}`); hata++; }
  }
}
if (hata) process.exit(1);
console.log("JS sözdizimi tamam");
