"""EP-15: the walk concordance. The pyosmium side (OSMnx's walk filter as tag rules; the
walkable ways of the committed OSM sample written as XML) runs everywhere; the OSMnx + scipy
side (the graph from that XML with no network call, the nearest nodes, Dijkstra, the
comparison) runs where the optional routing group is installed and is skipped otherwise
(CI never installs it, ADR-0008). The comparison itself is pandas and runs everywhere.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from phillysim.routing import concordance
from phillysim.routing.concordance import (
    DISABLED_URL,
    EXCLUDED_HIGHWAY_SUBSTRINGS,
    compare,
    walkable,
    write_walk_xml,
)

SAMPLE_PBF = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "spine-samples"
    / "raw"
    / "osm_network"
    / "2026-09-03"
    / "pennsylvania-260831.osm.pbf"
)


def test_walkable_mirrors_osmnx_walk_filter_with_substring_semantics() -> None:
    assert walkable({"highway": "residential"})
    assert walkable({"highway": "footway"}) and walkable({"highway": "steps"})
    assert walkable({"highway": "service", "service": "parking_aisle"})
    assert not walkable({})
    assert not walkable({"highway": "motorway"}) and not walkable({"highway": "motorway_link"})
    assert not walkable({"highway": "cycleway"})
    assert not walkable({"highway": "abandoned"})  # "no" is a substring of it, as in Overpass
    assert not walkable({"highway": "residential", "area": "yes"})
    assert not walkable({"highway": "residential", "access": "private"})
    assert not walkable({"highway": "residential", "foot": "no"})
    assert not walkable({"highway": "service", "service": "private"})
    assert not walkable({"highway": "residential", "sidewalk": "separate"})
    assert not walkable({"highway": "residential", "sidewalk:left": "separate"})
    assert walkable({"highway": "residential", "sidewalk": "both"})
    assert "motor" in EXCLUDED_HIGHWAY_SUBSTRINGS and "services" in EXCLUDED_HIGHWAY_SUBSTRINGS


def test_write_walk_xml_selects_the_walkable_ways_of_the_sample(tmp_path: Path) -> None:
    target = tmp_path / "walk.osm"
    info = write_walk_xml(SAMPLE_PBF, target)
    assert target.is_file() and info["bytes"] == target.stat().st_size
    assert 0 < info["walkable_ways"] < info["highway_ways"]
    assert info["nodes"] > info["walkable_ways"]
    text = target.read_text("utf-8")
    assert text.lstrip().startswith("<?xml") and "<osm " in text
    assert text.count("<way ") == info["walkable_ways"]
    assert text.count("<node ") == info["nodes"]
    assert "<relation " not in text
    assert 'k="highway" v="motorway"' not in text
    # Idempotent and deterministic.
    again = write_walk_xml(SAMPLE_PBF, target)
    assert again == info


def test_compare_uses_finite_pairs_only_and_counts_the_rest() -> None:
    fallback = pd.DataFrame(
        {
            "origin_geoid": ["o"] * 6,
            "site_id": [f"s{i}" for i in range(6)],
            "fallback_minutes": [10.0, 20.5, 30.0, np.nan, 50.0, 119.0],
            "fallback_metres": [800.0, 1640.0, 2400.0, np.nan, 4000.0, 9520.0],
        }
    )
    r5 = pd.DataFrame(
        {
            "origin_geoid": ["o"] * 6,
            "site_id": [f"s{i}" for i in range(6)],
            "mode": "walk",
            "time_median_min": [11.0, 21.0, 29.0, 120.0, 120.0, 120.0],
            "time_p85_min": [11.0, 21.0, 29.0, 120.0, 120.0, 120.0],
        }
    )
    out = compare(fallback, r5, max_time_minutes=120)
    assert out["pairs"] == 6 and out["r5_finite_pairs"] == 3 and out["fallback_finite_pairs"] == 5
    assert out["pairs_compared"] == 3
    assert out["excluded_r5_censored_only"] == 2 and out["excluded_fallback_censored_only"] == 0
    assert out["excluded_both_censored"] == 1
    assert out["spearman_rho"] == 1.0 and out["gate_met"] is True
    assert out["mean_abs_diff_minutes"] == pytest.approx(0.833, abs=0.001)
    inverted = r5.assign(time_median_min=[29.0, 21.0, 11.0, 120.0, 120.0, 120.0])
    assert compare(fallback, inverted, max_time_minutes=120)["spearman_rho"] == -1.0
    empty = compare(fallback.iloc[:1], r5.iloc[:1], max_time_minutes=120)
    assert empty["spearman_rho"] is None and empty["gate_met"] is False


# --- the OSMnx side (the optional routing group) ---------------------------------------------


@pytest.fixture(scope="module")
def sample_graph(tmp_path_factory: pytest.TempPathFactory):
    pytest.importorskip("osmnx")
    pytest.importorskip("scipy")
    target = tmp_path_factory.mktemp("walk") / "walk.osm"
    write_walk_xml(SAMPLE_PBF, target)
    return concordance.build_graph(target)


def test_build_graph_reads_the_xml_with_every_network_path_disabled(sample_graph) -> None:
    import osmnx as ox

    graph, info = sample_graph
    assert info["nodes"] == graph.number_of_nodes() > 100
    assert info["edges"] == graph.number_of_edges() > info["nodes"]
    assert info["crs"] == "EPSG:26918" and graph.graph["crs"].to_epsg() == 26918
    assert info["settings"] == {
        "use_cache": False,
        "overpass_url": DISABLED_URL,
        "nominatim_url": DISABLED_URL,
    }
    assert ox.settings.use_cache is False and ox.settings.overpass_url == DISABLED_URL
    # Bidirectional: every edge has its reverse.
    u, v, _ = next(iter(graph.edges(keys=True)))
    assert graph.has_edge(v, u)


def test_walk_times_on_the_sample_are_finite_ordered_and_censored(sample_graph) -> None:
    graph, _info = sample_graph
    origins = pd.DataFrame(
        {"id": ["a", "b"], "lon": [-75.1442, -75.1563], "lat": [39.9505, 39.9554]}
    )
    destinations = pd.DataFrame(
        {"id": ["near", "far"], "lon": [-75.1450, -75.16], "lat": [39.9520, 39.95]}
    )
    frame, info = concordance.walk_times(
        graph, origins, destinations, speed_kmh=4.8, max_time_minutes=120
    )
    assert list(frame.columns) == ["origin_geoid", "site_id", "fallback_minutes", "fallback_metres"]
    assert len(frame) == 4 and frame["fallback_minutes"].notna().all()
    by = frame.set_index(["origin_geoid", "site_id"])
    assert by.loc[("a", "near"), "fallback_minutes"] < by.loc[("a", "far"), "fallback_minutes"]
    # Minutes are metres at 80 m/min, and the straight line is a lower bound.
    assert by["fallback_minutes"].to_numpy() == pytest.approx(
        by["fallback_metres"].to_numpy() / 80.0, rel=1e-3
    )
    assert by.loc[("a", "near"), "fallback_metres"] >= 100
    assert info["origins"] == 2 and info["destinations"] == 2
    assert info["snap_distance_m"]["origins_max"] < 200
    # A tight censor turns the far pairs into NaN.
    tight, _ = concordance.walk_times(
        graph, origins, destinations, speed_kmh=4.8, max_time_minutes=5
    )
    assert tight["fallback_minutes"].isna().any()
    assert (tight["fallback_minutes"].dropna() < 5).all()
