/** Proxy POST /capture to the Python API (Render). Netlify does not run Python functions. */
export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }
  if (req.method !== "POST") {
    return Response.json({ detail: "Method not allowed." }, { status: 405 });
  }

  const apiBase = Netlify.env.get("API_URL");
  if (!apiBase) {
    return Response.json(
      {
        detail:
          "API_URL is not set in Netlify. Deploy the FastAPI backend (see README) and add API_URL to site environment variables.",
      },
      { status: 503 },
    );
  }

  const target = `${apiBase.replace(/\/$/, "")}/capture`;
  let upstream;
  try {
    upstream = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await req.text(),
    });
  } catch {
    return Response.json(
      { detail: "Could not reach the API backend. Is Render running?" },
      { status: 502 },
    );
  }

  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") || "application/json",
    },
  });
};

export const config = {
  path: "/capture",
};
