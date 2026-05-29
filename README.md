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
