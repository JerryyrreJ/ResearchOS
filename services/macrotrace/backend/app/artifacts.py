from __future__ import annotations

import csv
import hashlib
import html
import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4


def _safe(value: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_", "."} else "_" for character in value)


def _table_rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for column, coefficients in table.get("coefficients", {}).items():
        for coefficient in coefficients:
            rows.append({"specification": column, **coefficient})
    return rows


def table_to_csv(table: dict[str, Any]) -> str:
    rows = _table_rows(table)
    output = StringIO()
    fieldnames = ["specification", "variable_id", "label", "coefficient", "standard_error", "p_value", "ci_low", "ci_high", "stars"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def table_to_html(table: dict[str, Any]) -> str:
    columns = table.get("columns", [])
    variables: list[str] = []
    labels: dict[str, str] = {}
    matrix: dict[tuple[str, str], dict[str, Any]] = {}
    for column, coefficients in table.get("coefficients", {}).items():
        for item in coefficients:
            variable_id = item["variable_id"]
            if variable_id not in variables:
                variables.append(variable_id)
            labels[variable_id] = item.get("label", variable_id)
            matrix[(variable_id, column)] = item
    head = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    body_rows = []
    for variable_id in variables:
        estimates = []
        standard_errors = []
        details = []
        for column in columns:
            item = matrix.get((variable_id, column))
            if not item:
                estimates.append("<td></td>")
                standard_errors.append("<td></td>")
                details.append("<td></td>")
                continue
            estimates.append(f"<td>{item['coefficient']}{html.escape(item.get('stars', ''))}</td>")
            standard_errors.append(f"<td class='se'>({item['standard_error']})</td>")
            details.append(f"<td class='detail'>p={item['p_value']}; 95% CI [{item['ci_low']}, {item['ci_high']}]</td>")
        body_rows.extend([
            f"<tr><th>{html.escape(labels[variable_id])}</th>{''.join(estimates)}</tr>",
            f"<tr><th></th>{''.join(standard_errors)}</tr>",
            f"<tr class='detail-row'><th></th>{''.join(details)}</tr>",
        ])
    stats_rows = []
    for label, values in table.get("statistics", {}).items():
        cells = "".join(f"<td>{html.escape(str(value if value is not None else ''))}</td>" for value in values)
        stats_rows.append(f"<tr><th>{html.escape(str(label))}</th>{cells}</tr>")
    notes = " ".join(html.escape(str(note)) for note in table.get("notes", []))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(table.get('title', 'Regression table'))}</title><style>
body{{font-family:Georgia,'Times New Roman',serif;margin:40px;color:#171713}} table{{border-collapse:collapse;width:100%;font-size:14px;border-top:2px solid #111;border-bottom:2px solid #111}} caption{{font-weight:700;font-size:18px;margin-bottom:12px;text-align:left}} thead{{border-bottom:1px solid #111}} th,td{{padding:6px 9px;text-align:right;vertical-align:top}} th:first-child{{text-align:left}} .se{{padding-top:0;color:#444}} .detail{{font-size:10px;color:#666;padding-top:0}} .detail-row{{border-bottom:0}} tbody.stats{{border-top:1px solid #111}} .notes{{font-size:11px;line-height:1.5;margin-top:10px}}
</style></head><body><table><caption>{html.escape(table.get('title', ''))}</caption><thead><tr><th>Variable</th>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody><tbody class="stats">{''.join(stats_rows)}</tbody></table><p class="notes">{notes}</p></body></html>"""


def _tex_escape(value: Any) -> str:
    text = str(value)
    for source, target in (("\\", "\\textbackslash{}"), ("_", "\\_"), ("%", "\\%"), ("&", "\\&"), ("#", "\\#")):
        text = text.replace(source, target)
    return text


def table_to_latex(table: dict[str, Any]) -> str:
    columns = table.get("columns", [])
    variables: list[str] = []
    matrix: dict[tuple[str, str], dict[str, Any]] = {}
    labels: dict[str, str] = {}
    for column, coefficients in table.get("coefficients", {}).items():
        for item in coefficients:
            variable = item["variable_id"]
            if variable not in variables:
                variables.append(variable)
            labels[variable] = item.get("label", variable)
            matrix[(variable, column)] = item
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        f"\\caption{{{_tex_escape(table.get('title', ''))}}}",
        f"\\begin{{tabular}}{{l{'c' * len(columns)}}}",
        "\\toprule",
        "Variable & " + " & ".join(_tex_escape(column) for column in columns) + " \\\\",
        "\\midrule",
    ]
    for variable in variables:
        estimates = []
        errors = []
        for column in columns:
            item = matrix.get((variable, column))
            estimates.append("" if item is None else f"{item['coefficient']}{item.get('stars', '')}")
            errors.append("" if item is None else f"({item['standard_error']})")
        lines.append(_tex_escape(labels[variable]) + " & " + " & ".join(estimates) + " \\\\")
        lines.append(" & " + " & ".join(errors) + " \\\\")
    lines.append("\\midrule")
    for label, values in table.get("statistics", {}).items():
        lines.append(_tex_escape(label) + " & " + " & ".join(_tex_escape(value if value is not None else "") for value in values) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\begin{minipage}{0.95\\linewidth}\\footnotesize " + " ".join(_tex_escape(note) for note in table.get("notes", [])) + "\\end{minipage}", "\\end{table}"])
    return "\n".join(lines) + "\n"


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _write(self, job_id: str, node_id: str, artifact_type: str, title: str, suffix: str, media_type: str, content: str) -> dict[str, Any]:
        artifact_id = "ART_" + uuid4().hex[:16].upper()
        directory = self.root / _safe(job_id) / _safe(node_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{artifact_id}{suffix}"
        path.write_text(content, encoding="utf-8", newline="\n")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return {
            "artifact_id": artifact_id,
            "job_id": job_id,
            "node_id": node_id,
            "artifact_type": artifact_type,
            "title": title,
            "media_type": media_type,
            "sha256": digest,
            "relative_path": path.relative_to(self.root).as_posix(),
            "created_at": datetime.now(UTC).isoformat(),
        }

    def save_model_result(self, job_id: str, node_id: str, result: dict[str, Any]) -> list[dict[str, Any]]:
        artifacts = [
            self._write(job_id, node_id, "JSON", f"{result['title']} - structured result", ".json", "application/json", json.dumps(result, ensure_ascii=False, indent=2)),
        ]
        table = result.get("table")
        if table:
            artifacts.extend([
                self._write(job_id, node_id, "CSV", table["title"], ".csv", "text/csv", table_to_csv(table)),
                self._write(job_id, node_id, "HTML", table["title"], ".html", "text/html", table_to_html(table)),
                self._write(job_id, node_id, "LATEX", table["title"], ".tex", "application/x-tex", table_to_latex(table)),
            ])
        for chart in result.get("charts", []):
            artifacts.append(self._write(job_id, node_id, "CHART", chart.get("title", "Chart data"), ".chart.json", "application/json", json.dumps(chart, ensure_ascii=False, indent=2)))
        return artifacts

    def path_for(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if self.root.resolve() not in candidate.parents:
            raise ValueError("artifact path escapes store")
        return candidate
