from app.ai.evaluation.schemas import EvaluationRun


class ReportGenerator:
    @staticmethod
    def generate_text_report(run: EvaluationRun) -> str:
        lines = [
            "=" * 60,
            "EVALUATION RUN REPORT",
            "=" * 60,
            f"Run ID:        {run.id}",
            f"Pipeline:      {run.pipeline_name}",
            f"Timestamp:     {run.timestamp.isoformat()}",
            f"Summary Score: {run.summary_score:.4f}",
            f"Overall:       {'PASS' if run.passed else 'FAIL'}",
            "",
            "Metrics:",
            "-" * 40,
        ]
        for metric in run.metrics:
            status = "PASS" if metric.passed else "FAIL" if metric.passed is not None else "N/A"
            category_display = metric.category.value.replace("_", " ").title()
            lines.append(f"  [{category_display}] {metric.name}")
            lines.append(f"    Value:    {metric.value:.4f}")
            lines.append(f"    Weight:   {metric.weight:.2f}")
            lines.append(f"    Status:   {status}")
            if metric.threshold is not None:
                lines.append(f"    Threshold: {metric.threshold:.4f}")
            if metric.details:
                lines.append(f"    Details:  {metric.details}")
            lines.append("")

        if run.metadata:
            lines.append("Metadata:")
            lines.append("-" * 40)
            for key, value in run.metadata.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    @staticmethod
    def generate_markdown_report(run: EvaluationRun) -> str:
        lines = [
            f"# Evaluation Run Report",
            f"",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Run ID | `{run.id}` |",
            f"| Pipeline | {run.pipeline_name} |",
            f"| Timestamp | {run.timestamp.isoformat()} |",
            f"| Summary Score | {run.summary_score:.4f} |",
            f"| Overall | {'**PASS**' if run.passed else '**FAIL**'} |",
            f"",
            f"## Metrics",
            f"",
            f"| Category | Metric | Value | Weight | Threshold | Status |",
            f"|----------|--------|-------|--------|-----------|--------|",
        ]
        for metric in run.metrics:
            status = "✅ PASS" if metric.passed else "❌ FAIL" if metric.passed is not None else "—"
            threshold = f"{metric.threshold:.4f}" if metric.threshold is not None else "—"
            category_display = metric.category.value.replace("_", " ").title()
            escaped_name = metric.name.replace("|", "\\|")
            lines.append(f"| {category_display} | {escaped_name} | {metric.value:.4f} | {metric.weight:.2f} | {threshold} | {status} |")

        for metric in run.metrics:
            if metric.details:
                lines.append(f"")
                lines.append(f"**{metric.name}** — {metric.details}")

        if run.metadata:
            lines.append(f"")
            lines.append(f"## Metadata")
            lines.append(f"")
            for key, value in run.metadata.items():
                lines.append(f"- **{key}**: {value}")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_summary(run: EvaluationRun) -> str:
        status = "PASS" if run.passed else "FAIL"
        return f"[{status}] {run.pipeline_name} — score: {run.summary_score:.4f} ({len(run.metrics)} metrics, {run.timestamp.isoformat()})"
