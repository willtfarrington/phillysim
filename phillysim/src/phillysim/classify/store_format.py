"""USDA SNAP store types to format classes: the published, versioned mapping (EP-6).

The USDA SNAP Retailer Locator file types every retailer with one of a small
set of **store types** (``Supermarket``, ``Super Store``, ``Small Grocery
Store``, ``Convenience Store``, ...), defined on the USDA "SNAP Store Type
Definitions" page by what the store sells and how it operates. This module
maps each of those provider labels to a project **format class** and says
which classes count as *supermarket-format* (AM-4, methodology.md
"Destination layers"). The mapping is a methods artifact: it lives in the
packaged table ``store_formats.csv`` beside this module, carries a version
(:data:`MAPPING_VERSION`, one of the manifest-recorded axes of ADR-0006),
is rendered verbatim into the method card (``docs/method-cards/store-formats.md``,
kept in sync by a test), and changes only with a version bump and a
changelog entry.

Vocabulary rule (docs/CLAIMS.md, C-2): every class name is format-based
(``supermarket``, ``grocery``, ``combination``, ``convenience``,
``specialty``, ``farmers_market``, ``other``); no nutrition-quality adjective
appears here, in the table, or in any column the mapping produces.
Classification is total on the file's vocabulary and strict: a store type
the table does not know is an error, never silently ``other``, because a new
provider label is the packet's stop condition (its semantics must be read
before it is mapped).
"""

from __future__ import annotations

import io
import re
from importlib import resources
from pathlib import Path

import pandas as pd

#: The methods version of this mapping; bump on any change to the table.
MAPPING_VERSION = "store-formats-1"
TABLE_FILE = "store_formats.csv"
TABLE_COLUMNS: tuple[str, ...] = (
    "store_type",
    "store_code",
    "format_class",
    "supermarket_format",
    "basis",
)
#: The one class AM-4 names as the supermarket-format destination layer.
SUPERMARKET_FORMAT = "supermarket"
FORMAT_CLASSES: tuple[str, ...] = (
    "supermarket",
    "grocery",
    "combination",
    "convenience",
    "specialty",
    "farmers_market",
    "other",
)
#: Where the provider's definitions live (archived with the data card, not the snapshot).
DEFINITIONS_URL = "https://www.fna.usda.gov/snap/store-definitions"

METHOD_CARD = Path("docs") / "method-cards" / "store-formats.md"
BEGIN_MARK = "<!-- store-formats:begin -->"
END_MARK = "<!-- store-formats:end -->"

#: Words that may never appear in a class name or the mapping's output vocabulary (C-2).
PROHIBITED_TERMS: tuple[str, ...] = ("healthy", "nutritious", "quality", "good", "bad", "fresh")


def load_table() -> pd.DataFrame:
    """The mapping table as packaged, validated: one row per provider store type."""
    text = resources.files(__package__).joinpath(TABLE_FILE).read_text("utf-8")
    table = pd.read_csv(io.StringIO(text), dtype="string", keep_default_na=False)
    if tuple(table.columns) != TABLE_COLUMNS:
        raise ValueError(f"{TABLE_FILE}: columns {tuple(table.columns)} != {TABLE_COLUMNS}")
    if table["store_type"].duplicated().any() or (table["store_type"] == "").any():
        raise ValueError(f"{TABLE_FILE}: store types must be unique and non-empty")
    unknown = sorted(set(table["format_class"]) - set(FORMAT_CLASSES))
    if unknown:
        raise ValueError(f"{TABLE_FILE}: format class(es) {unknown} not in {FORMAT_CLASSES}")
    flags = table["supermarket_format"].str.lower()
    if not flags.isin(["true", "false"]).all():
        raise ValueError(f"{TABLE_FILE}: supermarket_format must be true or false")
    table["supermarket_format"] = (flags == "true").astype("bool")
    consistent = table["supermarket_format"] == (table["format_class"] == SUPERMARKET_FORMAT)
    if not consistent.all():
        raise ValueError(
            f"{TABLE_FILE}: supermarket_format must be true exactly for class "
            f"{SUPERMARKET_FORMAT!r}"
        )
    for column in ("format_class",):
        for term in PROHIBITED_TERMS:
            if table[column].str.contains(term, case=False).any():
                raise ValueError(f"{TABLE_FILE}: prohibited term {term!r} in {column}")
    return table


def store_types() -> tuple[str, ...]:
    """Every provider store type the mapping knows, in table order."""
    return tuple(load_table()["store_type"])


def classify(store_type: pd.Series) -> pd.DataFrame:
    """``format_class`` and ``supermarket_format`` for each store type, index preserved.

    Raises :class:`ValueError` naming any store type the table does not know.
    """
    table = load_table().set_index("store_type")
    values = store_type.astype("string")
    unknown = sorted(set(values.dropna()) - set(table.index))
    if unknown or values.isna().any():
        raise ValueError(
            f"store type(s) not in the {MAPPING_VERSION} mapping: {unknown[:5]}"
            + (" (and null store types)" if values.isna().any() else "")
            + "; read their definitions before mapping them (stop condition)"
        )
    return pd.DataFrame(
        {
            "format_class": values.map(table["format_class"]).astype("string"),
            "supermarket_format": values.map(table["supermarket_format"]).astype("bool"),
        },
        index=store_type.index,
    )


def render_markdown() -> str:
    """The mapping as the Markdown table the method card carries, verbatim."""
    table = load_table()
    lines = [
        f"Mapping version `{MAPPING_VERSION}` ({len(table)} provider store types, "
        f"{len(FORMAT_CLASSES)} format classes; rendered from "
        f"`phillysim/src/phillysim/classify/{TABLE_FILE}`).",
        "",
        "| USDA store type | Code | Format class | Supermarket-format | "
        "Basis (USDA definition, abridged) |",
        "|---|---|---|---|---|",
    ]
    for row in table.itertuples(index=False):
        code = row.store_code if row.store_code else "—"
        flag = "yes" if row.supermarket_format else "no"
        basis = str(row.basis).replace("|", "\\|")
        lines.append(f"| {row.store_type} | {code} | `{row.format_class}` | {flag} | {basis} |")
    return "\n".join(lines) + "\n"


def splice(document: str, rendered: str) -> str:
    """``document`` with the region between the markers replaced by ``rendered``."""
    pattern = re.compile(re.escape(BEGIN_MARK) + r".*?" + re.escape(END_MARK), re.S)
    if pattern.search(document) is None:
        raise ValueError(f"method card lacks the {BEGIN_MARK} ... {END_MARK} region")
    return pattern.sub(lambda _: f"{BEGIN_MARK}\n{rendered}{END_MARK}", document, count=1)


def update_method_card(path: Path) -> bool:
    """Re-render the table into the method card at ``path``; True if the file changed."""
    before = path.read_text("utf-8")
    after = splice(before, render_markdown())
    if after != before:
        path.write_text(after, "utf-8", newline="\n")
    return after != before


def _main() -> None:
    from phillysim.config import find_repo_root

    root = find_repo_root()
    if root is None:
        raise SystemExit("run from inside the repository")
    target = root / METHOD_CARD
    changed = update_method_card(target)
    print(f"{target}: {'updated' if changed else 'already in sync'} ({MAPPING_VERSION})")


if __name__ == "__main__":
    _main()
