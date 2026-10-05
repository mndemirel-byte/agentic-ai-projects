/**
 * ProjectDemo — proje sayfasına gömülen terminal demo kartı.
 *
 * Tek kaynak: aynı bileşen platformda MDX component map'e eklenir ve
 * _pipeline/demo-player/build.mjs ile repodaki bağımsız demo.html'e derlenir.
 *
 * Veri: demo.json (schema 2). "scenes" sahneleri, "parameters" parametre
 * başvurusunu taşır. Eski oynatıcılar için "steps" (command/output) dizisi de
 * dosyada bulunur; bu bileşen onu kullanmaz.
 *
 * Kart tek ekrana sığacak şekilde tasarlanmıştır: yüksekliği görüntü alanıyla
 * sınırlıdır, uzun içerik (terminal çıktısı, parametre listesi) kartın kendi
 * içinde kayar.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "./ProjectDemo.module.css";

export type DemoParam = {
  name: string;
  kind: "konumsal" | "seçenek" | "bayrak";
  value: string;
  default: string;
  short: string;
  detail: string;
  example: string;
  positional: boolean;
};

export type DemoParamGroup = {
  command: string;
  title: string;
  summary: string;
  example?: string;
  params: DemoParam[];
};

export type DemoScene = {
  title: string;
  caption: string;
  command: string;
  output: string;
};

export type DemoData = {
  schema: number;
  demo_kind: "terminal";
  title: string;
  representative?: boolean;
  scenes: DemoScene[];
  parameters: DemoParamGroup[];
};

type UsedParam = { text: string; id: string; why: string };

const TYPE_DELAY = 16;
const LINE_DELAY = 45;
const SCENE_PAUSE = 3800;

function paramId(command: string, name: string) {
  return `pd-${command}-${name.replace(/^-+/, "")}`;
}

/** Komut satırını alt komut, konumsal argüman ve seçeneklere ayırır. */
export function parseCommand(command: string, groups: DemoParamGroup[]): UsedParam[] {
  const tokens = command.trim().split(/\s+/);
  const start = tokens.findIndex((t) => t.endsWith(".py"));
  const rest = tokens.slice(start + 1);
  const out: UsedParam[] = [];
  let sub: string | null = null;
  let positional = 0;

  const find = (cmd: string, name: string) => {
    for (const g of groups) {
      if (g.command !== cmd && g.command !== "genel") continue;
      const p = g.params.find((x) => x.name === name);
      if (p) return { group: g.command, param: p };
    }
    return null;
  };

  for (let i = 0; i < rest.length; i++) {
    const tok = rest[i];
    if (!sub && !tok.startsWith("--")) {
      sub = tok;
      const g = groups.find((x) => x.command === sub);
      const first = g ? g.summary.split(". ")[0].replace(/\.$/, "") + "." : "";
      out.push({ text: sub, id: `pd-g-${sub}`, why: first });
      continue;
    }
    if (tok.startsWith("--")) {
      const hit = find(sub ?? "genel", tok);
      if (!hit) continue;
      let text = tok;
      if (hit.param.kind === "seçenek" && i + 1 < rest.length) text += " " + rest[++i];
      out.push({ text, id: paramId(hit.group, hit.param.name), why: hit.param.short });
      continue;
    }
    const g = groups.find((x) => x.command === sub);
    const p = g?.params.filter((x) => x.positional)[positional++];
    if (p) out.push({ text: tok, id: paramId(g!.command, p.name), why: `${p.name}: ${p.short}` });
  }
  return out;
}

/** Terminal çıktısındaki etiketleri ve çubukları renklendirir. */
function OutputLine({ line }: { line: string }) {
  if (/^(Not|Uyarı|Fiyat kaynağı|Bu oran)/.test(line)) return <span className={styles.muted}>{line}</span>;
  if (/^(Ortalama|Girdi farkı)/.test(line)) return <span className={styles.amber}>{line}</span>;
  const parts = line.split(/(█+|░+|\bYÜKSEK\b|\bDİKKAT\b|\bTAŞMA\b|erişilemedi \([^)]*\)| OK$)/);
  return (
    <>
      {parts.map((p, i) => {
        if (!p) return null;
        if (p.startsWith("█")) return <span key={i} className={styles.barFull}>{p}</span>;
        if (p.startsWith("░")) return <span key={i} className={styles.barEmpty}>{p}</span>;
        if (p === "YÜKSEK" || p === "DİKKAT") return <span key={i} className={styles.amber}>{p}</span>;
        if (p === "TAŞMA" || p.startsWith("erişilemedi")) return <span key={i} className={styles.red}>{p}</span>;
        if (p === " OK") return <span key={i}> <span className={styles.green}>OK</span></span>;
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

function usePrefersReducedMotion() {
  const [reduce, setReduce] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduce(mq.matches);
    const on = () => setReduce(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduce;
}

export default function ProjectDemo({ demo }: { demo: DemoData }) {
  const scenes = demo.scenes;
  const reduce = usePrefersReducedMotion();
  const [tab, setTab] = useState<"demo" | "params">("demo");
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [typed, setTyped] = useState(0);
  const [lines, setLines] = useState(0);
  const [flash, setFlash] = useState<string | null>(null);
  const screenRef = useRef<HTMLDivElement>(null);
  const refBox = useRef<HTMLDivElement>(null);

  const scene = scenes[index];
  const outputLines = useMemo(() => scene.output.split("\n"), [scene]);
  const used = useMemo(() => parseCommand(scene.command, demo.parameters), [scene, demo.parameters]);
  const done = typed >= scene.command.length && lines >= outputLines.length;

  const show = useCallback(
    (i: number, animate: boolean) => {
      setIndex(i);
      if (animate && !reduce) {
        setTyped(0);
        setLines(0);
      } else {
        setTyped(scenes[i].command.length);
        setLines(scenes[i].output.split("\n").length);
      }
    },
    [reduce, scenes],
  );

  // İlk yüklemede ilk sahne tam gösterilir; oynatma kullanıcı başlatınca başlar.
  useEffect(() => {
    show(0, false);
  }, [show]);

  // Yazma ve çıktı animasyonu
  useEffect(() => {
    if (!playing) return;
    let t: ReturnType<typeof setTimeout>;
    if (typed < scene.command.length) t = setTimeout(() => setTyped((n) => n + 1), typed === 0 ? 250 : TYPE_DELAY);
    else if (lines < outputLines.length) t = setTimeout(() => setLines((n) => n + 1), lines === 0 ? 400 : LINE_DELAY);
    else if (index < scenes.length - 1) t = setTimeout(() => show(index + 1, true), SCENE_PAUSE);
    else setPlaying(false);
    return () => clearTimeout(t);
  }, [playing, typed, lines, index, scene, outputLines.length, scenes.length, show]);

  useEffect(() => {
    const el = screenRef.current;
    if (el && playing) el.scrollTop = el.scrollHeight;
  }, [lines, playing]);

  const togglePlay = () => {
    if (playing) {
      setPlaying(false);
      show(index, false);
      return;
    }
    if (reduce) return;
    const restart = done ? (index === scenes.length - 1 ? 0 : index) : index;
    show(restart, true);
    setPlaying(true);
  };

  const go = (i: number) => {
    const next = (i + scenes.length) % scenes.length;
    show(next, playing);
  };

  const openParam = (id: string) => {
    setTab("params");
    setFlash(id);
    requestAnimationFrame(() => {
      const box = refBox.current;
      const el = box?.querySelector<HTMLElement>(`#${CSS.escape(id)}`);
      if (box && el) box.scrollTo({ top: el.offsetTop - 12, behavior: reduce ? "auto" : "smooth" });
    });
    setTimeout(() => setFlash(null), 1600);
  };

  return (
    <section className={styles.root} aria-label={demo.title}>
      <header className={styles.head}>
        <div className={styles.headTitle}>
          <span className={styles.kicker}>Demo</span>
          <h2 className={styles.title}>{demo.title.replace(/^Demo:\s*/, "")}</h2>
        </div>
        <div className={styles.tabs} role="tablist" aria-label="Demo görünümü">
          <button role="tab" aria-selected={tab === "demo"} className={styles.tab} onClick={() => setTab("demo")}>
            Komutlar
          </button>
          <button role="tab" aria-selected={tab === "params"} className={styles.tab} onClick={() => setTab("params")}>
            Parametreler
          </button>
        </div>
      </header>

      {demo.representative && (
        <p className={styles.banner} role="note">
          Önizleme: bu demodaki sayılar temsilidir. Gerçek ölçüm çıktısıyla yeniden üretilecek.
        </p>
      )}

      {tab === "demo" ? (
        <div className={styles.body}>
          <div className={styles.main}>
            <div className={styles.caption}>
              <span className={styles.num}>
                {index + 1} / {scenes.length}
              </span>
              <div>
                <h3 className={styles.sceneTitle}>{scene.title}</h3>
                <p className={styles.sceneCaption}>{scene.caption}</p>
              </div>
            </div>

            <div className={styles.term}>
              <div className={styles.termBar}>
                <span>terminal</span>
                <span>{playing ? "çalışıyor" : done ? "tamamlandı" : "duraklatıldı"}</span>
              </div>
              <div className={styles.screen} ref={screenRef} aria-live="polite">
                <span className={styles.prompt}>$ </span>
                <span className={styles.cmd}>{scene.command.slice(0, typed)}</span>
                {typed < scene.command.length && <span className={styles.cursor} />}
                {outputLines.slice(0, lines).map((l, i) => (
                  <div key={i}>
                    <OutputLine line={l} />
                    {l === "" ? "\u00a0" : null}
                  </div>
                ))}
              </div>
            </div>

            <div className={styles.controls}>
              <button className={styles.btn} onClick={() => go(index - 1)}>
                Önceki
              </button>
              <button className={`${styles.btn} ${styles.primary}`} onClick={togglePlay} disabled={reduce}>
                {playing ? "Duraklat" : "Oynat"}
              </button>
              <button className={styles.btn} onClick={() => go(index + 1)}>
                Sonraki
              </button>
            </div>
          </div>

          <aside className={styles.side}>
            <h4 className={styles.sideTitle}>Sahneler</h4>
            <ol className={styles.scenes}>
              {scenes.map((s, i) => (
                <li key={i}>
                  <button
                    className={styles.sceneBtn}
                    aria-current={i === index ? "step" : undefined}
                    onClick={() => show(i, playing)}
                  >
                    <span className={styles.sceneNum}>{String(i + 1).padStart(2, "0")}</span>
                    {s.title}
                  </button>
                </li>
              ))}
            </ol>
            <h4 className={styles.sideTitle}>Bu komuttaki parametreler</h4>
            <ul className={styles.used}>
              {used.map((u) => (
                <li key={u.id + u.text}>
                  <button className={styles.tok} onClick={() => openParam(u.id)} title="Parametre ayrıntısına git">
                    {u.text}
                  </button>
                  <span className={styles.why}>{u.why}</span>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      ) : (
        <div className={styles.refBox} ref={refBox}>
          <p className={styles.refIntro}>
            Konumsal argümanlar sırayla ve adı yazılmadan verilir; seçenekler iki tireyle başlar ve bir değer alır;
            bayraklar değer almaz, yazılmaları yeterlidir.
          </p>
          {demo.parameters.map((g) => (
            <div key={g.command} className={styles.group} id={`pd-g-${g.command}`}>
              <div className={styles.groupHead}>
                <h3>{g.title}</h3>
                <p>{g.summary}</p>
                {g.example && <code>{g.example}</code>}
              </div>
              {g.params.map((p) => {
                const id = paramId(g.command, p.name);
                return (
                  <div key={id} id={id} className={`${styles.param} ${flash === id ? styles.flash : ""}`}>
                    <div>
                      <div className={styles.paramName}>{p.name}</div>
                      <div className={styles.pills}>
                        {[p.kind, p.value, p.default ? `varsayılan: ${p.default}` : ""]
                          .filter(Boolean)
                          .map((x) => (
                            <span key={x} className={styles.pill}>
                              {x}
                            </span>
                          ))}
                      </div>
                    </div>
                    <div>
                      <p className={styles.detail}>{p.detail}</p>
                      <div className={styles.example}>
                        <span>Örnek</span>
                        <code>{p.example}</code>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
