"""EP-6 golden mapping test: the store-type -> format-class table, its rules, and the
method card it is rendered into."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from phillysim.classify import store_format
from phillysim.config import find_repo_root

#: The mapping, pinned. Any change here is a methods change: bump MAPPING_VERSION,
#: re-render the method card, and say so in the changelog.
GOLDEN: dict[str, str] = {
    "Supermarket": "supermarket",
    "Super Store": "supermarket",
    "Large Grocery Store": "grocery",
    "Medium Grocery Store": "grocery",
    "Small Grocery Store": "grocery",
    "Combination Grocery/Other": "combination",
    "Convenience Store": "convenience",
    "Meat/Poultry Specialty": "specialty",
    "Seafood Specialty": "specialty",
    "Fruits/Veg Specialty": "specialty",
    "Bakery Specialty": "specialty",
    "Farmers' Market": "farmers_market",
    "Delivery Route": "other",
    "Food Buying Co-op": "other",
    "Military Commissary": "other",
    "Wholesaler": "other",
    "Unknown": "other",
}
GOLDEN_VERSION = "store-formats-1"


def test_golden_mapping() -> None:
    table = store_format.load_table()
    assert dict(zip(table["store_type"], table["format_class"], strict=True)) == GOLDEN
    assert store_format.MAPPING_VERSION == GOLDEN_VERSION
    assert list(table["supermarket_format"]) == [c == "supermarket" for c in GOLDEN.values()]
    assert store_format.store_types() == tuple(GOLDEN)
    assert set(GOLDEN.values()) == set(store_format.FORMAT_CLASSES)


def test_usda_codes_are_the_crosswalk_where_defined() -> None:
    table = store_format.load_table().set_index("store_type")
    assert table.loc["Supermarket", "store_code"] == "SM"
    assert table.loc["Super Store", "store_code"] == "SS"
    assert table.loc["Farmers' Market", "store_code"] == "FM"
    # Two labels exist in the file but not on the USDA definitions page: no code.
    assert table.loc["Wholesaler", "store_code"] == ""
    assert table.loc["Unknown", "store_code"] == ""
    codes = table["store_code"][table["store_code"] != ""]
    assert codes.is_unique and codes.str.fullmatch(r"[A-Z]{2}").all()


def test_vocabulary_is_format_based_only() -> None:
    """C-2: no nutrition-quality adjective in any class name, column, or identifier."""
    table = store_format.load_table()
    names = list(store_format.FORMAT_CLASSES) + list(table.columns) + [store_format.MAPPING_VERSION]
    names += [store_format.SUPERMARKET_FORMAT]
    for name in names:
        for term in store_format.PROHIBITED_TERMS:
            assert term not in name.lower(), (name, term)
    tree = ast.parse(Path(store_format.__file__).read_text("utf-8"))
    identifiers = {
        node.id if isinstance(node, ast.Name) else node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Name | ast.FunctionDef | ast.ClassDef)
    }
    identifiers |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    identifiers |= {node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)}
    for identifier in identifiers:
        for term in ("healthy", "nutritious", "quality"):
            assert term not in identifier.lower(), identifier


def test_classify_is_total_and_strict() -> None:
    series = pd.Series(["Super Store", "Convenience Store", "Supermarket"], index=[7, 3, 5])
    out = store_format.classify(series)
    assert list(out.index) == [7, 3, 5]
    assert list(out["format_class"]) == ["supermarket", "convenience", "supermarket"]
    assert list(out["supermarket_format"]) == [True, False, True]
    assert out["supermarket_format"].dtype == bool
    with pytest.raises(ValueError, match="stop condition"):
        store_format.classify(pd.Series(["Supermarket", "Hypermarket"]))
    with pytest.raises(ValueError, match="null store types"):
        store_format.classify(pd.Series(["Supermarket", None]))


def test_render_matches_the_table() -> None:
    rendered = store_format.render_markdown()
    assert rendered.startswith(f"Mapping version `{store_format.MAPPING_VERSION}`")
    rows = [line for line in rendered.splitlines() if line.startswith("| ") and "`" in line]
    assert len(rows) == len(GOLDEN)
    for store_type, klass in GOLDEN.items():
        assert any(line.startswith(f"| {store_type} |") and f"`{klass}`" in line for line in rows)


def test_method_card_carries_the_rendered_table() -> None:
    """The mapping table renders into the method-card stub (acceptance criterion)."""
    root = find_repo_root(Path(__file__).parent)
    assert root is not None
    card = root / store_format.METHOD_CARD
    text = card.read_text("utf-8")
    assert store_format.splice(text, store_format.render_markdown()) == text, (
        "method card out of sync: run `uv run python -m phillysim.classify.store_format`"
    )
    assert "supermarket-format" in text and "C-2" in text


def test_splice_requires_the_markers() -> None:
    with pytest.raises(ValueError, match="region"):
        store_format.splice("no markers here", "x")
    doc = f"before\n{store_format.BEGIN_MARK}\nold\n{store_format.END_MARK}\nafter\n"
    out = store_format.splice(doc, "new\n")
    assert out == f"before\n{store_format.BEGIN_MARK}\nnew\n{store_format.END_MARK}\nafter\n"


def test_update_method_card_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "card.md"
    target.write_text(f"{store_format.BEGIN_MARK}\nstale\n{store_format.END_MARK}\n", "utf-8")
    assert store_format.update_method_card(target) is True
    assert store_format.update_method_card(target) is False
    assert store_format.render_markdown() in target.read_text("utf-8")
