/** Bağımsız demo.html girişi: sayfaya gömülü demo.json verisini ProjectDemo ile gösterir. */
import { createRoot } from "react-dom/client";
import ProjectDemo, { type DemoData } from "./ProjectDemo";

const raw = document.getElementById("demo-data")?.textContent ?? "{}";
const demo = JSON.parse(raw) as DemoData;
createRoot(document.getElementById("root")!).render(<ProjectDemo demo={demo} />);
