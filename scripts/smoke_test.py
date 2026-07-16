from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings  # noqa: E402
from backend.app.engine import ResearchEngine  # noqa: E402
from backend.app.storage import MacroStore  # noqa: E402


QUESTIONS = [
    "未来1到3个月美国通胀是否会加速，这会不会推动10年期美债收益率上升？",
    "美国经济当前是在走弱还是重新加速，未来三个月衰退风险怎么样？",
    "美国联邦债务扩张是否正在增加10年期收益率压力？",
    "用州级真实面板数据检验房价同比和失业率的关系，并加入州和季度固定效应。",
    "AI是否已经显著推高美国失业率？",
]


def main() -> None:
    settings = get_settings()
    store = MacroStore(settings.database_path)
    if not store.has_data():
        raise SystemExit("Data warehouse is empty. Run scripts/sync_data.py first.")
    engine = ResearchEngine(settings, store)
    results = []
    for question in QUESTIONS:
        result = engine.run(question)
        results.append(
            {
                "question": question,
                "run_id": result["run_id"],
                "status": result["status"],
                "coverage": result["synthesis"]["coverage"],
                "headline": result["synthesis"]["headline"],
                "modules": [
                    {"id": module["module_id"], "status": module["status"]}
                    for module in result["modules"]
                ],
                "language_layer": result["trace"][-1]["detail"]["language_layer"]["status"],
            }
        )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(item["status"] not in ("COMPLETE", "PARTIAL") for item in results):
        raise SystemExit(1)
    if any(any(module["status"] != "SUCCESS" for module in item["modules"]) for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
