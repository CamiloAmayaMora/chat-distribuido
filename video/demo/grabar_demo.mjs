// Graba la DEMO REAL (caída y recuperación) sin tocar la pantalla del usuario.
// Abre un Chrome invisible con el escenario (los dos chats y los logs), escribe
// los mensajes de verdad, apaga y prende contenedores con docker y toma
// capturas continuas. Al final arma video/render/demo.mp4 con ffmpeg y deja
// en demo/eventos.json en qué segundo pasó cada cosa (para ubicar la voz).
//
//   docker compose -f docker-compose.lab.yml down -v
//   docker compose -f docker-compose.lab.yml up -d
//   node video/demo/grabar_demo.mjs
import { createRequire } from "node:module";
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const VIDEO = path.resolve(HERE, "..");
const ROOT = path.resolve(VIDEO, "..");
const { chromium } = require(path.join(VIDEO, "tools", "node_modules", "playwright-core"));
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const LAB = path.join(ROOT, "docker-compose.lab.yml");
const FRAMES = path.join(HERE, "frames");
const OUT = path.join(VIDEO, "render", "demo.mp4");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const compose = (...args) => execFileSync("docker", ["compose", "-f", LAB, ...args], { stdio: "ignore" });

fs.rmSync(FRAMES, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });
fs.mkdirSync(path.dirname(OUT), { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(pathToFileURL(path.join(HERE, "escenario.html")).href);
await sleep(2500);
const fa = page.frame({ url: /localhost:8001/ });
const fb = page.frame({ url: /localhost:8002/ });

// ---------------------------------------------------------------- logs reales
const INTEREST = /\b(SENT|RECEIVED|DUPLICATE|RETRY|REJECTED|HISTORY_REQUEST|HISTORY_DONE|RECOVERED|CENTRAL_DOWN|CENTRAL_UP|CENTRAL_BLIP|HEARTBEAT_FAIL|OUTBOX_FLUSH|REGISTERED|LOCAL_MESSAGE|STARTUP)\b/;
const seen = new Set();
let following = true;
function follow(container, srv) {
  const since = new Date().toISOString();
  const run = () => {
    if (!following) return;
    const p = spawn("docker", ["logs", "-f", "--since", since, container]);
    let buf = "";
    const onData = (d) => {
      buf += d.toString();
      const lines = buf.split(/\r?\n/);
      buf = lines.pop();
      for (const line of lines) {
        if (seen.has(line) || !INTEREST.test(line)) continue;
        seen.add(line);
        const m = line.match(/^\S+\s+(\S+)\s+(\S+)\s+(.*)$/);
        if (!m) continue;
        const rest = m[3].replace(/\s+/g, " ").replace(/central=http:\/\/central:9000 public_url=http:\/\/\w+:8000 /, "");
        page.evaluate(([s, k, r]) => window.addLog(s, k, r), [srv, m[2], rest]).catch(() => {});
      }
    };
    p.stdout.on("data", onData);
    p.stderr.on("data", onData);
    p.on("exit", () => setTimeout(run, 700)); // el contenedor se apagó: reintentar
  };
  run();
}
follow("chat-distribuido-ga-1", "ga");
follow("chat-distribuido-gb-1", "gb");

// ---------------------------------------------------------- grabación continua
const t0 = Date.now();
const times = [];
let recording = true;
const recorder = (async () => {
  let i = 0;
  while (recording) {
    const t = (Date.now() - t0) / 1000;
    const file = path.join(FRAMES, `f${String(i).padStart(5, "0")}.jpg`);
    try {
      await page.screenshot({ path: file, type: "jpeg", quality: 92 });
      times.push([file, t]);
      i++;
    } catch { await sleep(50); }
  }
})();
const events = {};
const mark = (name) => { events[name] = +((Date.now() - t0) / 1000).toFixed(2); console.log(name, events[name]); };
const step = (html, cmd = "") => page.evaluate(([h, c]) => window.setStep(h, c), [html, cmd]);
async function typeIn(frame, text) {
  await frame.focus("#text");
  await frame.type("#text", text, { delay: 55 });
  await sleep(250);
  await frame.press("#text", "Enter");
}
async function login(frame, name) {
  await frame.fill("#user", "");
  await frame.type("#user", name, { delay: 80 });
  await frame.press("#user", "Enter");
}

// ------------------------------------------------------------------ guion
mark("inicio");
await step("Dos grupos conectados al <b>servidor central</b>");
await sleep(1500);
await login(fa, "ana");
await sleep(600);
await login(fb, "beto");
await sleep(6500);

mark("conversacion");
await step("1 · Conversación entre <b>ga</b> y <b>gb</b>");
await typeIn(fa, "hola, soy ana desde ga");
await sleep(1800);
await typeIn(fb, "hola ana, aquí beto desde gb");
await sleep(3500);

mark("kill_ga");
await step("2 · Apagamos <b>ga</b> de golpe", "docker compose -f docker-compose.lab.yml kill ga");
await sleep(900);
compose("kill", "ga");
await page.evaluate(() => window.setDown("colA", true));
await sleep(3200);

mark("gb_escribe");
await step("3 · <b>gb</b> sigue escribiendo mientras ga está caído");
for (const m of ["¿alguien me lee?", "ga no está, pero el central guarda todo", "tercer mensaje durante la caída"]) {
  await typeIn(fb, m);
  await sleep(900);
}
await sleep(1500);

mark("start_ga");
await step("4 · Prendemos <b>ga</b>: pide lo que se perdió", "docker compose -f docker-compose.lab.yml start ga");
await sleep(900);
compose("start", "ga");
await page.evaluate(() => window.setDown("colA", false));
await sleep(8000);

mark("ga_al_dia");
await step("5 · <b>ga</b> al día: todo, una sola vez, mismo orden");
await sleep(6500);

mark("stop_central");
await step("6 · Ahora se cae el <b>servidor central</b>", "docker compose -f docker-compose.lab.yml stop central");
await sleep(900);
compose("stop", "central");
await sleep(7500);
await typeIn(fa, "¿se cayó el central?");
await sleep(800);
await typeIn(fa, "esto queda pendiente en disco");
await sleep(3000);

mark("start_central");
await step("7 · Vuelve el central: <b>ga</b> envía lo pendiente", "docker compose -f docker-compose.lab.yml start central");
await sleep(900);
compose("start", "central");
await sleep(9000);
await step("Ningún mensaje perdido · ninguno repetido");
await sleep(3500);
mark("fin");

recording = false;
await recorder;
following = false;
await browser.close();
fs.writeFileSync(path.join(HERE, "eventos.json"), JSON.stringify(events, null, 2));

// ------------------------------------------------- frames -> mp4 (30 fps)
const total = (Date.now() - t0) / 1000;
let list = "";
for (let i = 0; i < times.length; i++) {
  const dur = (i + 1 < times.length ? times[i + 1][1] : total) - times[i][1];
  list += `file '${times[i][0].replace(/\\/g, "/")}'\nduration ${Math.max(dur, 0.01).toFixed(3)}\n`;
}
list += `file '${times[times.length - 1][0].replace(/\\/g, "/")}'\n`;
const listFile = path.join(HERE, "frames.txt");
fs.writeFileSync(listFile, list);
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listFile,
  "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "16", "-preset", "slow", OUT], { stdio: "inherit" });
console.log(`frames=${times.length} (~${(times.length / total).toFixed(1)} fps de captura), duración=${total.toFixed(1)} s -> ${OUT}`);
process.exit(0);
