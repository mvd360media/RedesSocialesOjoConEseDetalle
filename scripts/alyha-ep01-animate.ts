/**
 * Alyha · Episodio 01 — anima un fotograma IA con Seedance 2.5 (imagen → vídeo).
 *
 * Uso:  npm run alyha:animate -- 3                        vista previa local (escena 2, 3, 4 o 6), 0 créditos
 *       npm run alyha:animate -- 3 --generar              genera el vídeo en Higgsfield (GASTA CRÉDITOS)
 *       npm run alyha:animate -- 3 --recuperar=<id>       solo consulta/descarga una petición ya enviada (0 créditos)
 *
 * - 4 s (mínimo del modelo y lo que pide el guion; ~0,46 $/s a 720p ≈ 1,85 $/clip), 9:16, sin audio,
 *   prompts V2/V3/V4/V6 del guion.
 * - El fotograma (2:3) se recorta a 9:16 antes de subirlo; el modelo no tiene aspect_ratio
 *   y respeta la proporción de la imagen de entrada.
 * - El envío se hace UNA sola vez (sin reintentos automáticos que dupliquen el gasto). El request_id
 *   se imprime y se guarda en clips-ia/V<escena>-peticion.json en cuanto la API lo devuelve, de modo
 *   que si la espera se agota se puede recuperar con --recuperar sin pagar otra generación.
 * - Espera hasta 20 min (antes 5 min, límite por defecto del SDK, insuficiente para Seedance 2.5).
 * - El vídeo se guarda sin metadatos (ffmpeg -map_metadata -1).
 * - Credenciales solo en servidor: HF_CREDENTIALS ("key_id:secret", o "id:key_id:secret" tal como
 *   lo muestra el panel) o HF_API_KEY_ID + HF_API_KEY_SECRET (entorno o .env.local). Nunca se imprimen.
 */
import { config as loadEnv } from "dotenv";
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

loadEnv({ path: ".env.local", quiet: true });

const API = "https://api.higgsfield.ai";
const MODEL = "bytedance/seedance-2.5/image-to-video";
const BASE = "campanas/alyha/episodio-01";
const OUT_DIR = join(BASE, "clips-ia");
const PREVIEW_DIR = join(BASE, "previews");
const POLL_INTERVAL_MS = 5_000;
const MAX_WAIT_MS = 20 * 60_000;
const DURATION_S = 4;
const USD_PER_S_720P = 0.4622; // tarifa publicada antes de descuentos

// cropX: desplazamiento horizontal del recorte 9:16 (864×1536) sobre el fotograma 1024×1536,
// elegido para no cortar a Alyha ni el elemento de la acción.
const SCENES: Record<string, { frame: string; cropX: number; prompt: string }> = {
  "2": {
    frame: "F2-rincon.jpg",
    cropX: 80,
    prompt:
      "Subtle handheld smartphone camera. The dog slowly turns her head from the empty corner toward the camera and lowers her ears with a sad, theatrical look, then sighs. Natural motion, realistic fur, no camera cuts, no text.",
  },
  "3": {
    frame: "F3-caja.jpg",
    cropX: 100,
    prompt:
      "Handheld camera follows the dog as she nudges the box forward once with her nose; tinsel moves naturally. Realistic paws and fur, playful energy, no cuts, no text.",
  },
  "4": {
    frame: "F4-arbol.jpg",
    cropX: 80,
    prompt:
      "Slow push-in toward the dog sitting next to the lit Christmas tree; fairy lights twinkle softly; the dog looks up at the empty branch, then back to the camera and tilts her head. Natural, realistic motion, no cuts, no text.",
  },
  "6": {
    frame: "F6-cierre.jpg",
    cropX: 80,
    prompt:
      "Static camera, fairy lights twinkle, the dog sighs contentedly and closes her eyes. Very subtle motion, realistic fur, no text.",
  },
};

type Creds = { id: string; secret: string };

function credentials(): Creds | null {
  const combined = process.env.HF_CREDENTIALS ?? process.env.HF_KEY;
  if (combined && !/\s/.test(combined)) {
    const parts = combined.split(":");
    // "key_id:secret" o "id:key_id:secret" (se usan siempre las dos últimas partes).
    if ((parts.length === 2 || parts.length === 3) && parts.every(Boolean)) {
      return { id: parts[parts.length - 2], secret: parts[parts.length - 1] };
    }
  }
  const id = process.env.HF_API_KEY_ID;
  const secret = process.env.HF_API_KEY_SECRET;
  return id && secret ? { id, secret } : null;
}

/** Llamada a la API sin reintentos. Los errores nunca incluyen credenciales. */
async function hf<T>(creds: Creds, method: "GET" | "POST", path: string, body?: object): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method,
    // Mismas cabeceras que usa el SDK 0.2.6: Authorization (cliente v2: generación y estado) y
    // hf-api-key/hf-secret (cliente v1: subida de ficheros, probada con éxito).
    headers: {
      Authorization: `Key ${creds.id}:${creds.secret}`,
      "hf-api-key": creds.id,
      "hf-secret": creds.secret,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(120_000),
  });
  const text = await res.text();
  if (!res.ok) {
    const hint = res.status === 401 ? " (credenciales no válidas)" : res.status === 403 ? " (sin créditos o sin permiso)" : "";
    throw new Error(`${method} ${path} → HTTP ${res.status}${hint}: ${text.slice(0, 300)}`);
  }
  return JSON.parse(text) as T;
}

type HfRequest = { request_id?: string; status?: string; error?: string; video?: { url?: string } };

function ffmpeg(args: string[]): void {
  execFileSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args], { stdio: "inherit" });
}

async function waitAndDownload(creds: Creds, requestId: string, sceneId: string): Promise<number> {
  const start = Date.now();
  let last = "";
  let result: HfRequest;
  while (true) {
    try {
      result = await hf<HfRequest>(creds, "GET", `/requests/${requestId}/status`);
    } catch (err) {
      // Errores transitorios de red/servidor al consultar: se sigue esperando (consultar no gasta créditos).
      const msg = err instanceof Error ? err.message : String(err);
      if (!/HTTP 5\d\d|fetch failed|timeout|aborted/i.test(msg)) throw err;
      result = { status: last || "desconocido" };
    }
    const status = String(result.status ?? "");
    if (status !== last) {
      console.log(`[${Math.round((Date.now() - start) / 1000)} s] estado: ${status}`);
      last = status;
    }
    if (["completed", "nsfw", "failed", "canceled", "cancelled"].includes(status)) break;
    if (Date.now() - start > MAX_WAIT_MS) {
      console.error(`Sin resultado tras ${MAX_WAIT_MS / 60_000} min (último estado: ${status}). La petición puede seguir en curso.`);
      console.error(`Recupérala sin gastar créditos: npm run alyha:animate -- ${sceneId} --recuperar=${requestId}`);
      return 3;
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }

  const status = String(result.status);
  if (status !== "completed") {
    const why =
      status === "nsfw" ? "bloqueada por moderación" :
      status === "failed" ? "fallida" : "cancelada";
    console.error(`Petición ${requestId} ${why}. No se ha generado vídeo.${result.error ? ` Motivo: ${result.error}` : ""}`);
    return status === "nsfw" ? 2 : 1;
  }
  const url = result.video?.url;
  if (!url) {
    console.error(`Petición ${requestId} completada pero sin URL de vídeo.`);
    return 1;
  }
  console.log(`Petición ${requestId} completada.`);
  console.log(`URL del vídeo: ${url}`);

  // Descarga y limpieza de metadatos (sin re-codificar).
  const work = join(tmpdir(), `alyha-ep01-dl-${process.pid}`);
  mkdirSync(work, { recursive: true });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Descarga fallida: HTTP ${res.status}`);
  const raw = join(work, "raw.mp4");
  writeFileSync(raw, Buffer.from(await res.arrayBuffer()));
  mkdirSync(OUT_DIR, { recursive: true });
  const out = join(OUT_DIR, `V${sceneId}-prueba.mp4`);
  ffmpeg([
    "-i", raw, "-map", "0:v", "-c", "copy",
    "-map_metadata", "-1", "-map_chapters", "-1",
    "-metadata:s:v", "handler_name=", "-fflags", "+bitexact", out,
  ]);
  rmSync(work, { recursive: true, force: true });
  console.log(`Guardado: ${out}`);
  return 0;
}

async function main(): Promise<number> {
  const args = process.argv.slice(2);
  const generate = args.includes("--generar");
  const recoverArg = args.find((a) => a.startsWith("--recuperar="));
  const recoverId = recoverArg?.slice("--recuperar=".length);
  const sceneId = args.find((a) => !a.startsWith("--"));
  const scene = SCENES[sceneId ?? ""];
  if (!scene || !sceneId) {
    console.error(`Escena no válida. Usa una de: ${Object.keys(SCENES).join(", ")}`);
    return 1;
  }
  if (generate && recoverArg) {
    console.error("Usa --generar o --recuperar, no ambos.");
    return 1;
  }

  // Recuperar una petición ya enviada: solo consulta estado y descarga, 0 créditos.
  if (recoverArg) {
    if (!recoverId) {
      console.error("Falta el request_id: --recuperar=<request_id>");
      return 1;
    }
    const creds = credentials();
    if (!creds) {
      console.error("Faltan credenciales: define HF_CREDENTIALS o HF_API_KEY_ID + HF_API_KEY_SECRET.");
      return 1;
    }
    console.log(`Recuperando petición ${recoverId} (no se envía nada nuevo, 0 créditos)…`);
    return waitAndDownload(creds, recoverId, sceneId);
  }

  // 1) Recorte a 9:16 sin metadatos.
  const work = join(tmpdir(), `alyha-ep01-${process.pid}`);
  mkdirSync(work, { recursive: true });
  const cropped = join(work, `escena-${sceneId}-9x16.jpg`);
  ffmpeg([
    "-i", join(BASE, "fotogramas-ia", scene.frame),
    "-vf", `crop=864:1536:${scene.cropX}:0`,
    "-map_metadata", "-1", "-q:v", "2", cropped,
  ]);

  // Por defecto: solo vista previa local, sin llamar a la API ni gastar créditos.
  if (!generate) {
    mkdirSync(PREVIEW_DIR, { recursive: true });
    const preview = join(PREVIEW_DIR, `escena-${sceneId}-9x16.jpg`);
    copyFileSync(cropped, preview);
    rmSync(work, { recursive: true, force: true });
    console.log(`VISTA PREVIA (no se ha llamado a Higgsfield, 0 créditos)`);
    console.log(`Fotograma de entrada 9:16: ${preview}`);
    console.log(`Modelo: ${MODEL} · ${DURATION_S} s · 720p · sin audio · mp4 · ≈ ${(DURATION_S * USD_PER_S_720P).toFixed(2)} $`);
    console.log(`Prompt: ${scene.prompt}`);
    console.log(`\nSi lo apruebas, genera (GASTA CRÉDITOS): npm run alyha:animate -- ${sceneId} --generar`);
    return 0;
  }

  const creds = credentials();
  if (!creds) {
    console.error("Faltan credenciales: define HF_CREDENTIALS o HF_API_KEY_ID + HF_API_KEY_SECRET.");
    return 1;
  }

  // 2) Subida al CDN de Higgsfield (el modelo pide image_url). Se usan las upload_headers
  //    que devuelve la API; sin ellas S3 rechaza la firma (falta x-amz-tagging).
  const link = await hf<{ upload_url: string; public_url: string; upload_headers?: Record<string, string> }>(
    creds, "POST", "/files/generate-upload-url", { content_type: "image/jpeg" },
  );
  const put = await fetch(link.upload_url, {
    method: "PUT",
    body: readFileSync(cropped),
    headers: link.upload_headers ?? { "Content-Type": "image/jpeg" },
  });
  if (!put.ok) throw new Error(`Subida del fotograma fallida: HTTP ${put.status}`);
  rmSync(work, { recursive: true, force: true });

  // 3) Envío ÚNICO de la generación (sin reintentos: un reintento podría cobrarse dos veces).
  console.log(`Enviando escena ${sceneId} a ${MODEL} (${DURATION_S} s, 720p, sin audio)…`);
  const submitted = await hf<HfRequest>(creds, "POST", `/${MODEL}`, {
    image_url: link.public_url,
    prompt: scene.prompt,
    duration: DURATION_S,
    resolution: "720p",
    generate_audio: false,
    // Sin output_format: el esquema de image-to-video no lo define y rechaza campos extra
    // (additionalProperties: false). Por defecto devuelve mp4.
  });
  const requestId = submitted.request_id;
  if (!requestId) {
    console.error(`La API no devolvió request_id. Respuesta: ${JSON.stringify(submitted).slice(0, 300)}`);
    return 1;
  }
  mkdirSync(OUT_DIR, { recursive: true });
  const ticket = join(OUT_DIR, `V${sceneId}-peticion.json`);
  writeFileSync(ticket, JSON.stringify({
    request_id: requestId, escena: sceneId, modelo: MODEL, prompt: scene.prompt,
    enviado: new Date().toISOString(),
  }, null, 2) + "\n");
  console.log(`request_id: ${requestId} (guardado en ${ticket})`);

  // 4) Espera y descarga.
  return waitAndDownload(creds, requestId, sceneId);
}

main()
  .then((code) => process.exit(code))
  .catch((err: unknown) => {
    const name = err instanceof Error ? err.constructor.name : "Error";
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Error: ${name}: ${message}`);
    process.exit(1);
  });
