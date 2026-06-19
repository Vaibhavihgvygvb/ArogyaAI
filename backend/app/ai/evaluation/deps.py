from app.ai.evaluation.runner import EvaluationRunner


_runner: EvaluationRunner | None = None


def get_evaluation_runner() -> EvaluationRunner:
    global _runner
    if _runner is None:
        _runner = EvaluationRunner()
    return _runner


def set_evaluation_runner(runner: EvaluationRunner) -> None:
    global _runner
    _runner = runner


def reset_evaluation_runner() -> None:
    global _runner
    _runner = None
