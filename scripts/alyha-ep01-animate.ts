/**
 * Alyha · Episodio 01 — anima un fotograma IA con Seedance 2.5 (imagen → vídeo).
 *
 * Uso:  npm run alyha:animate -- 3             vista previa local (escena 2, 3, 4 o 6), 0 créditos
 *       npm run alyha:animate -- 3 --generar   genera el vídeo en Higgsfield (GASTA CRÉDITOS)
 *
 * - 5 s, 9:16, sin audio, prompts V2/V3/V4/V6 del guion.
 * - El fotograma (2:3) se recorta a 9:16 antes de subirlo; el modelo no tiene aspect_ratio
 *   y respeta la proporción de la imagen de entrada.
 * - El vídeo se guarda sin metadatos (ffmpeg -map_metadata -1).
 * - Credenciales solo en servidor: HF_CREDENTIALS o HF_API_KEY_ID + HF_API_KEY_SECRET
 *   (entorno o .env.local). Nunca se imprimen.
 */
import { config as loadEnv } from "dotenv";
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { HiggsfieldClient } from "@higgsfield/client";
import { config, higgsfield } from "@higgsfield/client/v2";

loadEnv({ path: ".env.local", quiet: true });

const MODEL = "bytedance/seedance-2.5/image-to-video";
const BASE = "campanas/alyha/episodio-01";
const OUT_DIR = join(BASE, "clips-ia");
const PREVIEW_DIR = join(BASE, "previews");

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
      "Handheld camera follows the dog as she pushes the cardboard box forward with her nose two times; tinsel moves naturally. Realistic paws and fur, playful energy, no cuts, no text.",
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

function credentials(): { id: string; secret: string } | null {
  const combined = process.env.HF_CREDENTIALS ?? process.env.HF_KEY;
  if (combined && /^[^:\s]+:[^:\s]+$/.test(combined)) {
    const [id, secret] = combined.split(":");
    return { id, secret };
  }
  const id = process.env.HF_API_KEY_ID;
  const secret = process.env.HF_API_KEY_SECRET;
  return id && secret ? { id, secret } : null;
}

function ffmpeg(args: string[]): void {
  execFileSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args], { stdio: "inherit" });
}

async function main(): Promise<number> {
  const args = process.argv.slice(2);
  const generate = args.includes("--generar");
  const sceneId = args.find((a) => !a.startsWith("--"));
  const scene = SCENES[sceneId ?? ""];
  if (!scene) {
    console.error(`Escena no válida. Usa una de: ${Object.keys(SCENES).join(", ")}`);
    return 1;
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
    console.log(`Modelo: ${MODEL} · 5 s · 720p · sin audio · mp4`);
    console.log(`Prompt: ${scene.prompt}`);
    console.log(`\nSi lo apruebas, genera (GASTA CRÉDITOS): npm run alyha:animate -- ${sceneId} --generar`);
    return 0;
  }

  const creds = credentials();
  if (!creds) {
    console.error("Faltan credenciales: define HF_CREDENTIALS (id:secret) o HF_API_KEY_ID + HF_API_KEY_SECRET.");
    return 1;
  }

  // 2) Subida al CDN de Higgsfield (necesario: el modelo pide image_url).
  const uploader = new HiggsfieldClient({ apiKey: creds.id, apiSecret: creds.secret });
  // El SDK (0.2.6) ignora `upload_headers` de la API y S3 rechaza la firma (falta x-amz-tagging),
  // así que se sube a mano con las cabeceras que devuelve la API.
  const api = (uploader as unknown as { client: { post: (p: string, b: object) => Promise<{ data: {
    upload_url: string; public_url: string; upload_headers?: Record<string, string>;
  } }> } }).client;
  const { data: link } = await api.post("/files/generate-upload-url", { content_type: "image/jpeg" });
  const put = await fetch(link.upload_url, {
    method: "PUT",
    body: readFileSync(cropped),
    headers: link.upload_headers ?? { "Content-Type": "image/jpeg" },
  });
  if (!put.ok) throw new Error(`Subida del fotograma fallida: HTTP ${put.status}`);
  const imageUrl = link.public_url;

  // 3) Generación.
  config({ credentials: `${creds.id}:${creds.secret}` });
  console.log(`Generando escena ${sceneId} con ${MODEL} (5 s, 720p, sin audio)…`);
  const result = await higgsfield.subscribe(MODEL, {
    input: {
      image_url: imageUrl,
      prompt: scene.prompt,
      duration: 5,
      resolution: "720p",
      generate_audio: false,
      output_format: "mp4",
    },
    withPolling: true,
  });

  const status = String(result.status);
  if (status !== "completed") {
    const why =
      status === "nsfw" ? "bloqueada por moderación" :
      status === "failed" ? "fallida" :
      status === "canceled" || status === "cancelled" ? "cancelada" : `estado inesperado "${status}"`;
    console.error(`Petición ${result.request_id} ${why}. No se ha generado vídeo.`);
    return status === "nsfw" ? 2 : 1;
  }
  const url = result.video?.url;
  if (!url) {
    console.error(`Petición ${result.request_id} completada pero sin URL de vídeo.`);
    return 1;
  }
  console.log(`Petición ${result.request_id} completada.`);
  console.log(`URL del vídeo: ${url}`);

  // 4) Descarga y limpieza de metadatos (sin re-codificar).
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

main()
  .then((code) => process.exit(code))
  .catch((err: unknown) => {
    const name = err instanceof Error ? err.constructor.name : "Error";
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Error: ${name}: ${message}`);
    process.exit(1);
  });
