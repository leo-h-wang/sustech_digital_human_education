from app.models.schemas import SolutionStep, StepTiming
from app.manim_scenes.renderer import render_solution_video, compute_timings

steps = [
      SolutionStep(step_index=1, title="设定极限", description="令 x 趋近于 0", formula_latex=r"\lim_{x \to 0} \frac{\sin x}{x}"),
      SolutionStep(step_index=2, title="应用洛必达", description="分子分母同时求导", formula_latex=r"\frac{\cos x}{1} = 1"),
    ]
aligned = {1: "令 x 趋近于零", 2: "分子分母同时求导，得到结果为一"}
timings = compute_timings(steps, aligned, words_per_second=3.0)
video, timing_json = render_solution_video(steps, aligned, timings, timestamp="test001")
print("video:", video)
print("timing:", timing_json)