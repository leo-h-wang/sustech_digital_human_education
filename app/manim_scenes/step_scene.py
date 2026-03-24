"""Manim scenes for rendering math solution steps."""
from __future__ import annotations

import re
from typing import Optional, List

from manim import (
    Scene,
    VGroup,
    Text,
    MathTex,
    Write,
    FadeIn,
    FadeOut,
    UP,
    DOWN,
    WHITE,
    YELLOW,
    LIGHT_GRAY,
)

_MAX_WIDTH = 12.0


def _extract_latex_blocks(text: str) -> List[str]:
    """Return unique LaTeX expressions found inside $$...$$ or $...$."""
    blocks = re.findall(r'\$\$([^$]+)\$\$', text)
    blocks += re.findall(r'(?<!\$)\$([^$\n]+)\$(?!\$)', text)
    seen: set = set()
    result = []
    for b in blocks:
        b = b.strip()
        if b and b not in seen:
            seen.add(b)
            result.append(b)
    return result


def _strip_all_latex(text: str) -> str:
    """Remove $$ and $ markers, keeping the inner text."""
    text = re.sub(r'\$\$([^$]+)\$\$', r' \1 ', text)
    text = re.sub(r'(?<!\$)\$([^$\n]+)\$(?!\$)', r' \1 ', text)
    text = re.sub(r'\\displaystyle\{([^}]*)\}', r'\1', text)
    text = re.sub(r'  +', ' ', text).strip()
    return text


def _make_text(content: str, font_size: int = 28, color=WHITE) -> Text:
    mob = Text(content, font_size=font_size, color=color, line_spacing=1.3)
    if mob.width > _MAX_WIDTH:
        mob.scale_to_fit_width(_MAX_WIDTH)
    return mob


def _make_formula(latex: str, font_size: int = 44) -> Optional[MathTex]:
    try:
        mob = MathTex(latex, font_size=font_size, color=WHITE)
        if mob.width > _MAX_WIDTH:
            mob.scale_to_fit_width(_MAX_WIDTH)
        return mob
    except Exception:
        return None


class MathStepScene(Scene):
    """
    Renders one solution step.

    step_data keys:
        step_index   : int
        title        : str
        description  : str  -- primary content; $...$ LaTeX is extracted and rendered
        formula_latex: str  -- ignored
        duration     : float
    """

    def construct(self):
        data        = getattr(self, "step_data", {})
        title_text  = data.get("title", "")
        description = data.get("description", "")
        duration    = float(data.get("duration", 4.0))
        step_index  = data.get("step_index", 1)

        # ── 1. Title ───────────────────────────────────────────────────────────
        title_str = f"Step {step_index}: {title_text}"
        if len(title_str) > 55:
            title_str = title_str[:52] + "..."
        title_mob = _make_text(title_str, font_size=34, color=YELLOW)
        title_mob.to_edge(UP, buff=0.35)

        # ── 2. Plain description (LaTeX stripped) ──────────────────────────────
        desc_plain = _strip_all_latex(description)
        if len(desc_plain) > 200:
            desc_plain = desc_plain[:197] + "..."
        desc_mob = _make_text(desc_plain, font_size=26, color=LIGHT_GRAY)
        desc_mob.next_to(title_mob, DOWN, buff=0.45)

        # ── 3. Extract and render LaTeX from description ───────────────────────
        latex_blocks = _extract_latex_blocks(description)
        formula_mob: Optional[MathTex] = None
        if latex_blocks:
            combined = r" \quad ".join(latex_blocks[:2])
            formula_mob = _make_formula(combined, font_size=40)
        if formula_mob is not None:
            formula_mob.next_to(desc_mob, DOWN, buff=0.5)

        # ── 4. Sequential animation ────────────────────────────────────────────
        step_time = max(0.4, duration * 0.06)
        hold_time = max(1.0, duration - step_time * 3)

        self.play(Write(title_mob), run_time=step_time)
        self.play(FadeIn(desc_mob), run_time=step_time)
        if formula_mob is not None:
            self.play(Write(formula_mob), run_time=step_time)
        self.wait(hold_time)

        all_mobs = VGroup(title_mob, desc_mob)
        if formula_mob is not None:
            all_mobs.add(formula_mob)
        self.play(FadeOut(all_mobs), run_time=0.3)
