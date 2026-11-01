import { config as loadEnv } from "dotenv";
import { config, higgsfield } from "@higgsfield/client/v2";

// Load server-side credentials at runtime. Values are never printed.
loadEnv({ path: ".env.local", quiet: true });

const MODEL = "bytedance/seedance-2.5/text-to-video";

async function main(): Promise<number> {
  const credentials = process.env.HF_CREDENTIALS;
  if (!credentials || !/^[^:\s]+:[^:\s]+$/.test(credentials)) {
    console.error(
      "HF_CREDENTIALS is missing or not in key-id:key-secret format. Set it in .env.local or the environment.",
    );
    return 1;
  }

  config({ credentials });

  const result = await higgsfield.subscribe(MODEL, {
    input: {
      prompt: "A cinematic scene at sunset",
      duration: 5,
      resolution: "720p",
      aspect_ratio: "16:9",
    },
    withPolling: true,
  });

  // Statuses other than "completed" are treated as failures (canceled is checked defensively).
  const status = String(result.status);
  switch (status) {
    case "completed": {
      const url = result.video?.url;
      if (!url) {
        console.error(`Request ${result.request_id} completed but returned no video URL.`);
        return 1;
      }
      console.log(`Request ${result.request_id} completed.`);
      console.log(`Video URL: ${url}`);
      return 0;
    }
    case "nsfw":
      console.error(`Request ${result.request_id} was blocked by moderation (nsfw). No video was produced.`);
      return 2;
    case "failed":
      console.error(`Request ${result.request_id} failed. No video was produced.`);
      return 1;
    case "canceled":
    case "cancelled":
      console.error(`Request ${result.request_id} was canceled. No video was produced.`);
      return 1;
    default:
      console.error(`Request ${result.request_id} ended with unexpected status "${status}".`);
      return 1;
  }
}

main()
  .then((code) => process.exit(code))
  .catch((err: unknown) => {
    // Print only the error type/message; never the request config (it contains the auth header).
    const name = err instanceof Error ? err.constructor.name : "Error";
    const message = err instanceof Error ? err.message : String(err);
    console.error(`Generation request failed: ${name}: ${message}`);
    process.exit(1);
  });
