import json
import logging
import os

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: str,
    whisper_model: str,
    device_mode: str,
    episode_dir: str,
    progress_callback=None,
    total_duration_secs: float = 0,
) -> tuple[str, int, str]:
    """
    Transcribe audio using faster-whisper.

    Returns (transcript_path, word_count, device_used).
    Writes word-level transcript JSON to {episode_dir}/transcript.json.
    progress_callback(current_secs, total_secs) is called after each segment if provided.
    """
    model, device_used = _load_model(whisper_model, device_mode)
    logger.info("Transcribing %s with model=%s device=%s", audio_path, whisper_model, device_used)

    segments_iter, _ = model.transcribe(
        audio_path,
        word_timestamps=True,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
    )

    transcript_segments = []
    word_count = 0

    for segment in segments_iter:
        if progress_callback and total_duration_secs > 0:
            try:
                progress_callback(segment.end, total_duration_secs)
            except Exception:
                pass
        seg_data: dict = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        }
        if segment.words:
            seg_data["words"] = [
                {"word": w.word, "start": w.start, "end": w.end}
                for w in segment.words
            ]
            word_count += len(segment.words)
        transcript_segments.append(seg_data)

    transcript_path = os.path.join(episode_dir, "transcript.json")
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(transcript_segments, f)

    return transcript_path, word_count, device_used


def _load_model(model_size: str, device_mode: str) -> tuple[WhisperModel, str]:
    """Load WhisperModel for the given device_mode. Returns (model, device_str)."""
    if device_mode == "cpu_only":
        return WhisperModel(model_size, device="cpu", compute_type="int8"), "cpu"

    if device_mode == "gpu_required":
        # Will raise CTranslate2 error if CUDA is unavailable — correct behaviour
        return WhisperModel(model_size, device="cuda", compute_type="float16"), "cuda"

    # auto: try CUDA, fall back to CPU silently
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        return model, "cuda"
    except Exception:
        logger.info("CUDA unavailable, falling back to CPU for Whisper")
        return WhisperModel(model_size, device="cpu", compute_type="int8"), "cpu"
