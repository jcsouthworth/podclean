import json
import logging

logger = logging.getLogger(__name__)


def classify_ads(
    transcript_path: str,
    llm_backend: str,
    llm_model: str,
    confidence_threshold: float,
    ollama_base_url: str,
    anthropic_api_key: str | None,
) -> list[dict]:
    """
    Run LLM ad classification on a transcript file.

    Returns list of {start_ms, end_ms, confidence, reason} filtered by confidence_threshold.
    """
    with open(transcript_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    transcript_text = _format_transcript(segments)

    if llm_backend == "cloud":
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for cloud LLM backend")
        from services.anthropic import classify_ads as _classify
        raw = _classify(transcript_text, llm_model, anthropic_api_key)
    else:
        from services.ollama import classify_ads as _classify  # type: ignore[assignment]
        raw = _classify(transcript_text, llm_model, ollama_base_url)

    logger.info("LLM returned %d raw ad segments (threshold=%.2f)", len(raw), confidence_threshold)

    filtered = [
        seg for seg in raw
        if isinstance(seg.get("confidence"), (int, float))
        and seg["confidence"] >= confidence_threshold
        and isinstance(seg.get("start_ms"), (int, float))
        and isinstance(seg.get("end_ms"), (int, float))
    ]

    logger.info("%d segments kept after threshold filter", len(filtered))
    return filtered


def _format_transcript(segments: list[dict]) -> str:
    """Format transcript segments as timestamped text for LLM input.
    Each line includes both human-readable time and the raw ms value so the
    LLM can use the ms value directly without any conversion arithmetic.
    """
    lines = []
    for seg in segments:
        start_ms = int(seg.get("start", 0) * 1000)
        end_ms = int(seg.get("end", 0) * 1000)
        h = start_ms // 3_600_000
        m = (start_ms % 3_600_000) // 60_000
        s = (start_ms % 60_000) // 1_000
        lines.append(f"[{h:02d}:{m:02d}:{s:02d}|{start_ms}ms-{end_ms}ms] {seg.get('text', '').strip()}")
    return "\n".join(lines)
