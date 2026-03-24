"""Render Manim scenes for each solution step and concatenate into one video."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import List

from app.models.schemas import SolutionStep, StepTiming


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

def compute_timings(
    solution_steps: List[SolutionStep],
    aligned_narration: dict[int, str],
    words_per_second: float = 3.0,
    min_duration: float = 3.0,
) -> List[StepTiming]:
    """
    Compute per-step start/end times based on narration word count.
    Uses all step_indices present in aligned_narration (not just solution_steps),
    so extra narration steps from the LLM are also timed.
    """
    timings: List[StepTiming] = []
    cursor = 0.0

    # Use solution step order first, then any extra narration-only steps
    solution_indices = [s.step_index for s in solution_steps]
    extra_indices = sorted(idx for idx in aligned_narration if idx not in solution_indices)
    all_indices = solution_indices + extra_indices

    # Build a title map for description fallback
    desc_map = {s.step_index: (s.description or s.title) for s in solution_steps}

    for idx in all_indices:
        narration = aligned_narration.get(idx, desc_map.get(idx, ""))
        word_count = len(narration.split())
        duration = max(min_duration, word_count / words_per_second)

        timings.append(
            StepTiming(
                step_index=idx,
                start_sec=round(cursor, 3),
                end_sec=round(cursor + duration, 3),
                narration_text=narration,
            )
        )
        cursor += duration

    return timings


# ---------------------------------------------------------------------------
# Scene script template
# ---------------------------------------------------------------------------

SCENE_SCRIPT_TEMPLATE = textwrap.dedent("""\
    import sys, os
    sys.path.insert(0, {project_root!r})

    from app.manim_scenes.step_scene import MathStepScene

    class Step{scene_id}Scene(MathStepScene):
        step_data = {step_data!r}
""")


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _render_step_video(
    step: SolutionStep,
    duration: float,
    output_dir: Path,
    project_root: str,
) -> Path:
    """
    Write a temporary Manim script for one step and render it.
    Returns the path to the rendered .mp4 file.
    """
    scene_id = f"S{step.step_index:03d}"
    step_data = {
        "step_index": step.step_index,
        "title": step.title,
        "description": step.description,
        "formula_latex": step.formula_latex or "",
        "duration": duration,
    }

    script_content = SCENE_SCRIPT_TEMPLATE.format(
        project_root=project_root,
        scene_id=step.step_index,
        step_data=step_data,
    )

    script_path = output_dir / f"step_{scene_id}.py"
    script_path.write_text(script_content, encoding="utf-8")

    scene_class = f"Step{step.step_index}Scene"
    video_output_dir = output_dir / scene_id
    video_output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "manim",
        "render",
        "--quality", "m",           # 720p
        "--output_file", f"{scene_id}.mp4",
        "--media_dir", str(video_output_dir),
        str(script_path),
        scene_class,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Manim render failed for step {step.step_index}:\n"
            f"{result.stderr[-2000:]}"
        )

    # Manim writes to <media_dir>/videos/<script_stem>/<quality>/<scene_class>.mp4
    # Search recursively for the output file
    matches = list(video_output_dir.rglob(f"{scene_id}.mp4"))
    if not matches:
        # Fallback: find any .mp4
        matches = list(video_output_dir.rglob("*.mp4"))
    if not matches:
        raise FileNotFoundError(
            f"No output mp4 found in {video_output_dir} after rendering step {step.step_index}."
        )
    return matches[0]


def _ffmpeg_exe() -> str:
    """Locate ffmpeg executable, checking common Windows install paths."""
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]
    # winget installs to LocalAppData\Microsoft\WinGet\Packages
    import glob as _glob
    winget_hits = _glob.glob(
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan*\**\ffmpeg.exe"),
        recursive=True,
    )
    candidates = winget_hits + candidates
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError(
        "ffmpeg not found. Install it and add to PATH, or set FFMPEG_PATH env var."
    )


def _concat_videos(video_paths: List[Path], output_path: Path) -> None:
    """Concatenate mp4 files using ffmpeg."""
    list_file = output_path.parent / "concat_list.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for p in video_paths:
            f.write(f"file '{p.as_posix()}'\n")

    ffmpeg = os.environ.get("FFMPEG_PATH") or _ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr[-2000:]}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_solution_video(
    timestamp: str,
    solution_steps: List[SolutionStep],
    timings: List[StepTiming],
    output_dir_base: str = "problems",
) -> tuple[str, str]:
    """
    Render a Manim video for the full solution and save a timing JSON.

    Args:
        timestamp:       used for file naming
        solution_steps:  ordered solution steps
        timings:         per-step timing list (from compute_timings)
        output_dir_base: directory to save outputs (default "problems")

    Returns:
        (video_path, timing_json_path) as relative path strings
    """
    project_root = str(Path(__file__).resolve().parents[2])
    work_dir = Path(tempfile.mkdtemp(prefix=f"manim_{timestamp}_"))

    os.makedirs(output_dir_base, exist_ok=True)

    # Build step→duration map
    duration_map = {t.step_index: (t.end_sec - t.start_sec) for t in timings}

    # Render each step
    step_videos: List[Path] = []
    for step in solution_steps:
        duration = duration_map.get(step.step_index, 4.0)
        video_path = _render_step_video(step, duration, work_dir, project_root)
        step_videos.append(video_path)

    # Concatenate
    final_video = Path(output_dir_base) / f"problem_{timestamp}_solution.mp4"
    if len(step_videos) == 1:
        import shutil
        shutil.copy2(step_videos[0], final_video)
    else:
        _concat_videos(step_videos, final_video)

    # Save timing JSON
    timing_json = Path(output_dir_base) / f"problem_{timestamp}_timing.json"
    timing_data = [t.dict() for t in timings]
    timing_json.write_text(
        json.dumps(timing_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return str(final_video), str(timing_json)
