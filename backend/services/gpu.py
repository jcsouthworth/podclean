"""nvidia-smi wrapper for GPU status reporting."""
import subprocess


def get_gpu_status(device_mode: str) -> dict:
    base: dict = {
        "available": False,
        "device_mode": device_mode,
        "gpu_name": None,
        "vram_used_mb": None,
        "vram_total_mb": None,
        "utilization_pct": None,
        "actively_used": False,
    }
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return base
        parts = [p.strip() for p in result.stdout.strip().split(",")]
        if len(parts) < 4:
            return base
        utilization = int(parts[3])
        return {
            "available": True,
            "device_mode": device_mode,
            "gpu_name": parts[0],
            "vram_used_mb": int(parts[1]),
            "vram_total_mb": int(parts[2]),
            "utilization_pct": utilization,
            "actively_used": utilization > 5,
        }
    except Exception:
        return base
