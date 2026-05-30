# Knowledge Pipeline

Paste a URL → fetch it → summarize with Claude → file it in Notion.

A deliberately small, non-agentic tool: the warm-up before adding autonomy. The
three pipeline steps (`extract` → `summarize` → `store`) are independent typed
functions so they can later become tools an agent calls.

## Stack

| Piece            | Library                 | .NET analogue                     |
|------------------|-------------------------|-----------------------------------|
| Web API          | FastAPI + uvicorn       | ASP.NET Core minimal APIs         |
| Models / config  | Pydantic / pydantic-settings | records + validation / `IOptions<T>` |
| Article text     | trafilatura             | —                                 |
| YouTube captions | youtube-transcript-api  | —                                 |
| Summaries        | anthropic (Claude)      | —                                 |
| Storage          | notion-client           | —                                 |
| Packaging        | uv                      | NuGet + .csproj                   |

## Setup

### 1. Install dependencies

Uses [uv](https://docs.astral.sh/uv/). From the project root:

```bash
uv sync
```

### 2. Create a Notion integration + database

1. Create an internal integration at <https://www.notion.so/my-integrations>,
   then copy its secret (starts with `ntn_`).
2. Make a new Notion database (a full-page table) with these properties —
   **names and types must match exactly**:

   | Property | Type          |
   |----------|---------------|
   | `Name`   | Title         |
   | `URL`    | URL           |
   | `Source` | Select        |
   | `Tags`   | Multi-select  |

3. Open the database, click `•••` → **Connections** → add your integration.
   (The integration only sees databases you explicitly connect it to.)
4. Grab the database id from its URL: the 32-character string between the
   workspace slug and the `?` —
   `notion.so/<workspace>/<DATABASE_ID>?v=...`

### 3. Configure secrets

```bash
cp .env.example .env
```

Fill in `ANTHROPIC_API_KEY`, `NOTION_API_KEY`, and `NOTION_DATABASE_ID`.

### 4. Run

```bash
uv run uvicorn src.app:app --reload
```

Open <http://127.0.0.1:8000>, paste a link, hit Capture.

## Tests

```bash
uv run pytest
```

## Deploy (Netlify + Render)

**Netlify hosts the UI only.** It supports JavaScript/TypeScript/Go functions — not Python.
The capture pipeline runs on [Render](https://render.com) as FastAPI; a small Netlify
function proxies `POST /capture` to that API.

```
Browser → Netlify (static + capture.mjs proxy) → Render (FastAPI pipeline)
```

### 1. Deploy the API on Render

1. [Render dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
2. Connect `fort-worth-dev/article-capture` — Render reads `render.yaml`
3. Set secret env vars when prompted:
   - `ANTHROPIC_API_KEY`
   - `NOTION_API_KEY`
   - `NOTION_DATABASE_ID`
   - `ANTHROPIC_MODEL` (optional)
4. After deploy, copy the service URL (e.g. `https://article-capture-api.onrender.com`)

Free tier sleeps after inactivity; the first request may take ~30s to wake up.

### 2. Configure Netlify

Site settings → **Environment variables**:

| Variable | Value |
|----------|-------|
| `API_URL` | Your Render URL (no trailing slash), e.g. `https://article-capture-api.onrender.com` |

Secrets (`ANTHROPIC_*`, `NOTION_*`) live on **Render only** — not Netlify.

Redeploy the Netlify site after setting `API_URL`.

### 3. Verify

- Netlify **Functions** tab should list **capture** (JavaScript)
- `POST https://<your-site>.netlify.app/capture` should proxy to Render
- Local dev unchanged: `uv run uvicorn src.app:app --reload`

### Notes

- Captures often take 15–30 seconds (fetch + Claude + Notion).
- If you see **404 on /capture**, the JS function did not deploy — check the Functions tab.
- If you see **503 API_URL is not set**, add `API_URL` on Netlify and redeploy.

## Project layout

```
src/
  extractors/
    base.py        # ContentExtractor interface (the Strategy seam)
    article.py     # trafilatura
    youtube.py     # transcript + oEmbed metadata
    registry.py    # picks an extractor by URL; article is the fallback
  models.py        # Content (extractor output) + Summary (AI output)
  config.py        # typed settings from .env
  summarizer.py    # Claude call, structured output via forced tool-use
  notion_store.py  # Summary -> Notion page
  app.py           # FastAPI: serves the page + runs the pipeline
static/index.html  # single-page UI
tests/             # extractor routing tests
```

## Adding a source

Implement `ContentExtractor` (a `can_handle` and an async `extract`) and add an
instance to `_EXTRACTORS` in `registry.py`, above `ArticleExtractor`. Nothing
else changes — that's the point of the seam.

## Known limitations (v1, by design)

- **No captions, no YouTube summary.** Videos without a transcript raise a clean
  error rather than guessing. (Audio transcription via Whisper is a later add.)
- **Paywalled / JS-heavy articles** may not extract. A Playwright fallback is the
  natural next step.
- **Very long transcripts** are trimmed before summarizing. Swap in chunked
  map-reduce when you start losing detail on multi-hour videos.
- **`author` is captured but not written to Notion.** Add an `Author` text
  property and one line in `notion_store.py` if you want it.
