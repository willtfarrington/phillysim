"""Build-time class bins (methodology.md "Uncertainty": bins are computed at build time so
that map, table, and CSV agree; governance.md: a five-class binned palette).

The publish stage computes one set of edges per published column over that
column's non-null values, records the edges in the public manifest, and writes
the class of every row as a ``<column>_bin`` companion. The site never bins on
its own. Quantile edges are the default (equal counts per class, which is what
a non-ranking choropleth of ~408 tracts reads best with); ties collapse
duplicate edges, so a column with few distinct values gets fewer classes, never
an empty one.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

BIN_CLASSES = 5
BIN_METHOD = "quantile"
METHODS: tuple[str, ...] = ("quantile", "equal_interval")


def bin_edges(
    values: pd.Series, classes: int = BIN_CLASSES, method: str = BIN_METHOD
) -> list[float]:
    """Ascending, strictly increasing class edges (``classes + 1`` of them at most; fewer when
    values tie); empty when there is no non-null value."""
    if classes < 1:
        raise ValueError("classes must be at least 1")
    if method not in METHODS:
        raise ValueError(f"unknown bin method {method!r}; expected one of {METHODS}")
    present = pd.to_numeric(values, errors="raise").dropna().astype("float64").to_numpy()
    if present.size == 0:
        return []
    if method == "quantile":
        raw = np.quantile(present, np.linspace(0.0, 1.0, classes + 1))
    else:
        raw = np.linspace(present.min(), present.max(), classes + 1)
    edges: list[float] = []
    for edge in raw:
        value = round(float(edge), 6)  # interpolation noise (355.50000000000006) is not an edge
        if not edges or value > edges[-1]:
            edges.append(value)
    return edges


def assign_bins(values: pd.Series, edges: list[float]) -> pd.Series:
    """The 1-based class of every value (nullable Int64; null stays null).

    Class ``i`` covers ``(edges[i-1], edges[i]]`` with the first class closed on the left,
    so every value from the lowest edge to the highest lands in exactly one class.
    """
    out = pd.Series(pd.array([pd.NA] * len(values), dtype="Int64"), index=values.index)
    if len(edges) < 2:
        if len(edges) == 1:  # a single distinct value: one class
            present = values.notna()
            out[present] = 1
        return out
    numeric = pd.to_numeric(values, errors="raise").astype("float64")
    present = numeric.notna()
    classes = np.searchsorted(
        np.asarray(edges, dtype="float64"), numeric[present].to_numpy(), "left"
    )
    classes = np.clip(classes, 1, len(edges) - 1)
    out[present] = pd.array(classes.astype("int64"), dtype="Int64")
    return out


def bin_record(edges: list[float], classes: int, method: str) -> dict[str, Any]:
    """What the public manifest records for one binned column."""
    return {
        "method": method,
        "classes_requested": classes,
        "classes": max(len(edges) - 1, 0),
        "edges": edges,
    }
