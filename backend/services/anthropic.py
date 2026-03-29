import json
import logging
import re

import anthropic as anthropic_sdk

logger = logging.getLogger(__name__)

_SYSTEM = "You analyze podcast transcripts to identify advertisement segments. Return only valid JSON."

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


def classify_ads(transcript_text: str, model: str, api_key: str) -> list[dict]:
    """Call Anthropic Claude to classify ad segments in transcript text."""
    client = anthropic_sdk.Anthropic(api_key=api_key)
    prompt = _PROMPT_TEMPLATE.format(transcript=transcript_text)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text
    logger.info("Anthropic raw response: %s", raw)
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
