"""Static contracts for the Chinese-only MacroTrace research interface.

These tests intentionally compare the frontend dictionaries with the live v2
registries.  A registry addition must therefore ship with its Chinese display
label instead of silently falling back to an English Registry name or ID.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
INDEX_HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
REGISTRY_DIR = ROOT / "registry" / "v2"
CHINESE = re.compile(r"[\u3400-\u9fff]")


def _registry_ids(filename: str, id_field: str) -> set[str]:
    registry = json.loads((REGISTRY_DIR / filename).read_text(encoding="utf-8"))
    return {item[id_field] for item in registry["items"]}


def _frontend_mapping(name: str) -> dict[str, str]:
    match = re.search(
        rf"const\s+{re.escape(name)}\s*=\s*\{{(?P<body>.*?)\n\}};",
        APP_JS,
        flags=re.DOTALL,
    )
    assert match, f"frontend/app.js 缺少 {name} 中文映射表"
    pairs = re.findall(r'"([^"\\]+)"\s*:\s*"([^"\\]*)"', match.group("body"))
    return dict(pairs)


def _function_body(name: str) -> str:
    signature = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", APP_JS)
    assert signature, f"frontend/app.js 缺少 {name} 函数"
    start = signature.end()
    depth = 1
    for index in range(start, len(APP_JS)):
        char = APP_JS[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return APP_JS[start:index]
    raise AssertionError(f"无法读取 {name} 函数体")


def _assert_complete_chinese_mapping(
    *, registry_file: str, id_field: str, mapping_name: str, expected_count: int | None = None
) -> None:
    registry_ids = _registry_ids(registry_file, id_field)
    if expected_count is not None:
        assert len(registry_ids) == expected_count, (
            f"{registry_file} 应保持 {expected_count} 条美国研究通道；"
            f"当前为 {len(registry_ids)} 条，请同步更新本合同"
        )
    mapping = _frontend_mapping(mapping_name)
    missing = sorted(registry_ids - mapping.keys())
    assert not missing, f"{mapping_name} 缺少中文映射：{missing}"
    non_chinese = sorted(item_id for item_id in registry_ids if not CHINESE.search(mapping[item_id]))
    assert not non_chinese, f"{mapping_name} 仍显示非中文标签：{non_chinese}"


def test_all_thirteen_us_lanes_have_chinese_labels() -> None:
    _assert_complete_chinese_mapping(
        registry_file="lanes.json",
        id_field="lane_id",
        mapping_name="ZH_LANES",
        expected_count=13,
    )


def test_every_registered_factor_has_a_chinese_label() -> None:
    _assert_complete_chinese_mapping(
        registry_file="factors.json",
        id_field="factor_id",
        mapping_name="ZH_FACTORS",
    )


@pytest.mark.parametrize(
    ("registry_file", "id_field", "mapping_name"),
    [
        ("nodes.json", "node_id", "ZH_NODES"),
        ("mechanisms.json", "mechanism_id", "ZH_MECHANISMS"),
    ],
)
def test_research_nodes_and_mechanisms_have_complete_chinese_labels(
    registry_file: str, id_field: str, mapping_name: str
) -> None:
    _assert_complete_chinese_mapping(
        registry_file=registry_file,
        id_field=id_field,
        mapping_name=mapping_name,
    )


def test_us_data_network_never_loads_the_akshare_catalog() -> None:
    body = _function_body("loadDataEvidenceCatalog")
    assert "/api/v1/data-plugins/akshare/datasets" not in body
    assert 'plugin.plugin_id !== "akshare"' in body
    assert re.search(r"state\.pluginCatalog\s*=\s*\{\s*akshare:\s*\[\]", body)


def test_research_graph_nodes_use_the_chinese_label_resolver() -> None:
    body = _function_body("renderGraph")
    assert "graphNodeLabel(node)" in body
    assert '<strong class="node-label">${escapeHtml(node.label)}</strong>' not in body


def test_visible_graph_zoom_controls_have_chinese_accessible_names() -> None:
    expected = {
        "dataZoomOut": "缩小数据网络",
        "dataZoomIn": "放大数据网络",
        "zoomOut": "缩小研究图谱",
        "zoomIn": "放大研究图谱",
    }
    for element_id, label in expected.items():
        tag = re.search(rf'<button\b[^>]*\bid="{element_id}"[^>]*>', INDEX_HTML)
        assert tag, f"缺少缩放按钮 #{element_id}"
        assert f'aria-label="{label}"' in tag.group(0), f"#{element_id} 的 aria-label 必须为中文"

    assert not re.search(r'aria-label="[^"]*\bzoom\b[^"]*"', INDEX_HTML, flags=re.IGNORECASE)
