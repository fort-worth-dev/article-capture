/** Emit static/config.js so the UI can call Render directly (avoids Netlify proxy timeouts). */
import { writeFileSync } from "node:fs";

const apiBase = (process.env.API_URL ?? "").trim().replace(/\/$/, "");

if (process.env.NETLIFY && !apiBase) {
  console.error(
    "FATAL: API_URL is not set. Add your Render service URL to Netlify env vars and redeploy.",
  );
  process.exit(1);
}

const contents = `// Generated at build time from API_URL. Do not edit on Netlify deploys.
window.__API_BASE__ = ${JSON.stringify(apiBase)};
`;

writeFileSync("static/config.js", contents);
console.log(`Wrote static/config.js (API_BASE=${apiBase || "(same-origin, local dev)"})`);
