from datetime import datetime
from typing import Any
from uuid import uuid4

from app.ai.evaluation.schemas import EvaluationMetric, EvaluationRun


class EvaluationRunner:
    def __init__(self) -> None:
        self._runs: dict[str, EvaluationRun] = {}

    def create_run(
        self,
        pipeline_name: str,
        metrics: list[EvaluationMetric],
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationRun:
        run_id = str(uuid4())
        run = EvaluationRun(
            id=run_id,
            timestamp=datetime.utcnow(),
            pipeline_name=pipeline_name,
            metrics=metrics,
            metadata=metadata or {},
        )
        run.summary_score = self.compute_summary(run)
        run.passed = run.summary_score >= 0.5
        self._runs[run_id] = run
        return run

    def get_run(self, run_id: str) -> EvaluationRun | None:
        return self._runs.get(run_id)

    def list_runs(self, pipeline_name: str | None = None) -> list[EvaluationRun]:
        if pipeline_name is None:
            return list(self._runs.values())
        return [
            run for run in self._runs.values() if run.pipeline_name == pipeline_name
        ]

    def compute_summary(self, run: EvaluationRun) -> float:
        if not run.metrics:
            return 0.0
        total_weight = sum(m.weight for m in run.metrics)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(m.value * m.weight for m in run.metrics)
        return weighted_sum / total_weight

    def compare_runs(self, run_ids: list[str]) -> dict[str, Any]:
        runs = [self._runs[rid] for rid in run_ids if rid in self._runs]
        if not runs:
            return {}

        result: dict[str, Any] = {
            "run_count": len(runs),
            "runs": [{"id": r.id, "pipeline_name": r.pipeline_name, "summary_score": r.summary_score, "passed": r.passed} for r in runs],
        }

        scores = [r.summary_score for r in runs]
        result["min_score"] = min(scores)
        result["max_score"] = max(scores)
        result["avg_score"] = sum(scores) / len(scores)

        if len(runs) >= 2:
            result["best_run_id"] = max(runs, key=lambda r: r.summary_score).id
            result["worst_run_id"] = min(runs, key=lambda r: r.summary_score).id
            result["score_delta"] = result["max_score"] - result["min_score"]

        metric_names = {m.name for r in runs for m in r.metrics}
        deltas = {}
        for name in metric_names:
            values = [m.value for r in runs for m in r.metrics if m.name == name]
            if len(values) >= 2:
                deltas[name] = max(values) - min(values)
        if deltas:
            result["metric_deltas"] = deltas

        return result

    def generate_report(self, run: EvaluationRun) -> str:
        lines = [
            f"Run ID: {run.id}",
            f"Pipeline: {run.pipeline_name}",
            f"Timestamp: {run.timestamp.isoformat()}",
            f"Summary Score: {run.summary_score:.4f}",
            f"Overall: {'PASS' if run.passed else 'FAIL'}",
            "",
            "Metrics:",
        ]
        for metric in run.metrics:
            status = "PASS" if metric.passed else "FAIL" if metric.passed is not None else "N/A"
            lines.append(f"  - {metric.name}: {metric.value:.4f} [{status}]")
            if metric.details:
                lines.append(f"    Details: {metric.details}")
        lines.append("")
        return "\n".join(lines)
