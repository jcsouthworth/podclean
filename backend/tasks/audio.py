import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def process_audio(
    original_path: str,
    episode_dir: str,
    ad_segments: list[dict],
    ad_handling: str,
) -> str:
    """
    Process audio file according to ad_handling mode.

    Returns path to processed.mp3.
    """
    output_path = os.path.join(episode_dir, "processed.mp3")

    if ad_handling == "chapters":
        _process_chapters(original_path, output_path, ad_segments)
    else:
        _process_splice(original_path, output_path, ad_segments)

    return output_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_duration_ms(audio_path: str) -> int:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True, check=True,
    )
    return int(float(result.stdout.strip()) * 1000)


def _get_bitrate_kbps(audio_path: str) -> int:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True, check=True,
    )
    try:
        bps = int(result.stdout.strip())
        return max(bps // 1000, 64)  # at least 64 kbps
    except (ValueError, ZeroDivisionError):
        return 128


# ---------------------------------------------------------------------------
# Chapters mode
# ---------------------------------------------------------------------------


def _process_chapters(original_path: str, output_path: str, ad_segments: list[dict]):
    """Mux chapter markers into MP3 without re-encoding."""
    duration_ms = _get_duration_ms(original_path)
    chapters = _build_chapters(ad_segments, duration_ms)

    ffmeta_fd, ffmeta_path = tempfile.mkstemp(suffix=".ffmeta")
    try:
        with os.fdopen(ffmeta_fd, "w") as f:
            f.write(";FFMETADATA1\n")
            for ch in chapters:
                f.write("[CHAPTER]\n")
                f.write("TIMEBASE=1/1000\n")
                f.write(f"START={ch['start_ms']}\n")
                f.write(f"END={ch['end_ms']}\n")
                f.write(f"title={ch['title']}\n")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", original_path,
                "-i", ffmeta_path,
                "-map_metadata", "1",
                "-codec", "copy",
                output_path,
            ],
            check=True, capture_output=True,
        )
    finally:
        if os.path.exists(ffmeta_path):
            os.unlink(ffmeta_path)


def _build_chapters(ad_segments: list[dict], duration_ms: int) -> list[dict]:
    if not ad_segments:
        return [{"start_ms": 0, "end_ms": duration_ms, "title": "Content"}]

    sorted_ads = sorted(ad_segments, key=lambda s: int(s.get("start_ms", 0)))
    chapters = []
    cursor = 0

    for ad in sorted_ads:
        start = int(ad.get("start_ms", 0))
        end = int(ad.get("end_ms", 0))
        if cursor < start:
            chapters.append({"start_ms": cursor, "end_ms": start - 1, "title": "Content"})
        chapters.append({"start_ms": start, "end_ms": end - 1, "title": "Ad Break"})
        cursor = max(cursor, end)

    if cursor < duration_ms:
        chapters.append({"start_ms": cursor, "end_ms": duration_ms, "title": "Content"})

    return chapters


# ---------------------------------------------------------------------------
# Splice mode
# ---------------------------------------------------------------------------


def _process_splice(original_path: str, output_path: str, ad_segments: list[dict]):
    """Remove ad segments and concatenate remaining audio, re-encoding as MP3."""
    duration_ms = _get_duration_ms(original_path)
    bitrate = _get_bitrate_kbps(original_path)
    keep_ranges = _build_keep_ranges(ad_segments, duration_ms)

    if not keep_ranges:
        # Everything is an ad — just copy as-is
        subprocess.run(
            ["ffmpeg", "-y", "-i", original_path, "-c", "copy", output_path],
            check=True, capture_output=True,
        )
        return

    if len(keep_ranges) == 1:
        start = keep_ranges[0][0] / 1000
        end = keep_ranges[0][1] / 1000
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", original_path,
                "-ss", str(start), "-to", str(end),
                "-c:a", "libmp3lame", "-b:a", f"{bitrate}k",
                output_path,
            ],
            check=True, capture_output=True,
        )
        return

    # Multiple ranges: build atrim+concat filter graph
    filter_parts = []
    for i, (start_ms, end_ms) in enumerate(keep_ranges):
        start = start_ms / 1000
        end = end_ms / 1000
        filter_parts.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[s{i}]"
        )

    n = len(keep_ranges)
    inputs = "".join(f"[s{i}]" for i in range(n))
    filter_parts.append(f"{inputs}concat=n={n}:v=0:a=1[out]")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", original_path,
            "-filter_complex", ";".join(filter_parts),
            "-map", "[out]",
            "-c:a", "libmp3lame", "-b:a", f"{bitrate}k",
            output_path,
        ],
        check=True, capture_output=True,
    )


# Each ad segment is expanded by this many ms on both sides before cutting.
_AD_PAD_MS = 200

# Adjacent ads separated by less than this ms of content are merged into one.
_AD_BRIDGE_MS = 30_000

# Content windows shorter than this at the very start or end of the podcast
# are absorbed into the adjacent ad rather than kept as a tiny isolated clip.
_EDGE_ABSORB_MS = 2000


def _build_keep_ranges(ad_segments: list[dict], duration_ms: int) -> list[tuple[int, int]]:
    if not ad_segments:
        return [(0, duration_ms)]

    # Step 1: sort and apply symmetric padding.
    padded = []
    for ad in sorted(ad_segments, key=lambda s: int(s.get("start_ms", 0))):
        start = max(0, int(ad.get("start_ms", 0)) - _AD_PAD_MS)
        end = min(duration_ms, int(ad.get("end_ms", 0)) + _AD_PAD_MS)
        padded.append([start, end])

    # Step 2: merge overlapping ads and bridge short gaps between adjacent ads.
    merged = [padded[0]]
    for start, end in padded[1:]:
        gap = start - merged[-1][1]
        if gap <= 0 or gap < _AD_BRIDGE_MS:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Step 3: build keep ranges from the merged ad list.
    keep = []
    cursor = 0
    for start, end in merged:
        if cursor < start:
            keep.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration_ms:
        keep.append((cursor, duration_ms))

    # Step 4: absorb short leading/trailing content windows.
    if keep and (keep[0][1] - keep[0][0]) <= _EDGE_ABSORB_MS:
        keep.pop(0)
    if keep and (keep[-1][1] - keep[-1][0]) <= _EDGE_ABSORB_MS:
        keep.pop()

    return keep
