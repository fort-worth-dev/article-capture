/** Emit static/config.js so the UI can call Render directly (avoids Netlify proxy timeouts). */
import { writeFileSync } from "node:fs";

const apiBase = (process.env.API_URL ?? "").replace(/\/$/, "");
const contents = `// Generated at build time from API_URL. Do not edit on Netlify deploys.
window.__API_BASE__ = ${JSON.stringify(apiBase)};
`;

writeFileSync("static/config.js", contents);
console.log(`Wrote static/config.js (API_BASE=${apiBase || "(same-origin)"})`);
