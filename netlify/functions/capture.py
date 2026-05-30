from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Make `src` importable when Netlify runs this file from netlify/functions/.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.pipeline import CaptureHttpError, run_capture  # noqa: E402

_JSON = {"Content-Type": "application/json"}


def handler(event: dict, _context: object) -> dict:
    method = event.get("httpMethod", "GET")
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _JSON, "body": ""}
    if method != "POST":
        return {
            "statusCode": 405,
            "headers": _JSON,
            "body": json.dumps({"detail": "Method not allowed."}),
        }

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": _JSON,
            "body": json.dumps({"detail": "Request body must be JSON."}),
        }

    url = body.get("url")
    if not isinstance(url, str):
        return {
            "statusCode": 422,
            "headers": _JSON,
            "body": json.dumps({"detail": "url → Input should be a valid string"}),
        }

    try:
        result = asyncio.run(run_capture(url))
    except CaptureHttpError as exc:
        return {
            "statusCode": exc.status_code,
            "headers": _JSON,
            "body": json.dumps({"detail": exc.detail}),
        }
    except Exception:
        return {
            "statusCode": 500,
            "headers": _JSON,
            "body": json.dumps({"detail": "Something went wrong."}),
        }

    return {
        "statusCode": 200,
        "headers": _JSON,
        "body": json.dumps(result.model_dump()),
    }
