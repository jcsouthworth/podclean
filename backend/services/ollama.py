import json
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
You are analyzing a podcast transcript to identify advertisement segments.

Each transcript line is formatted as:
  [HH:MM:SS|start_ms-end_ms] spoken text

Example line: [00:03:05|185000ms-187500ms] And now a word from our sponsor.

The numbers after the pipe (|) are the exact millisecond values to use.
Copy them directly into your response — do NOT convert or calculate.

Identify all segments that are advertisements, sponsor reads, or promotional \
content. Return ONLY a JSON array:

[
  {{
    "start_ms": 185000,
    "end_ms": 312000,
    "confidence": 0.95,
    "reason": "Sponsor read for HelloFresh, contains promo code"
  }}
]

Rules:
- start_ms and end_ms must be copied directly from the transcript ms values
- confidence is 0.0–1.0
- If no ads are detected, return []
- Return ONLY the JSON array, no other text

Transcript:
{transcript}"""


def classify_ads(transcript_text: str, model: str, base_url: str) -> list[dict]:
    """Call Ollama to classify ad segments in transcript text."""
    prompt = _PROMPT_TEMPLATE.format(transcript=transcript_text)
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=1800.0,
    )
    response.raise_for_status()
    raw = response.json().get("response", "")
    logger.info("Ollama raw response: %s", raw)
    return _parse_segments(raw)


def _parse_segments(raw: str) -> list[dict]:
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            segments = json.loads(match.group())
            if isinstance(segments, list):
                return [s for s in segments if isinstance(s, dict)]
        except json.JSONDecodeError:
            pass
    return []
