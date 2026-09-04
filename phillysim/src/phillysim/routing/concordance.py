"""The walk concordance against the fallback engine (EP-15; methodology.md "Validation").

methodology.md names the fallback for a spike kill: **OSMnx 2.x + scipy sparse
Dijkstra, walk only**. The concordance builds that engine on the same clipped
extract the night routed (``intermediate/network/<clip>.osm.pbf``) and
compares its walk times with R5's over the 408 origins × the supermarket-format
retailers at 4.8 km/h: Spearman ρ over the pairs both engines report under
the censor; the gate is ρ ≥ 0.95. It is also the fallback's rehearsal: on a
kill the code stays and the fallback packet grows from it.

**No network call.** OSMnx's downloading paths are never used: the walkable
ways are selected from the clip with pyosmium (:func:`walkable` mirrors the
tag rules of OSMnx's own ``walk`` network filter, substring semantics
included, so the two engines see the same streets), written as OSM XML under
``<data root>/cache/concordance/``, and read with ``graph_from_xml``; the
settings that would let OSMnx reach Overpass or Nominatim are pointed at a
disabled URL and its cache is off (:func:`configure_osmnx`; the test suite
also refuses every socket). OSMnx and scipy live in the optional ``routing``
group (ADR-0008), so nothing here is imported at module level.

**The engine.** ``graph_from_xml(bidirectional=True, simplify=True,
retain_all=False)`` (walking is two-way; the largest connected component),
projected to the analysis CRS; each point snapped to its nearest graph node
(scipy's k-d tree through OSMnx); scipy's ``dijkstra`` on the edge lengths in
metres from every origin; the walk time is the path length plus both snap
distances, at the walking speed, in fractional minutes (R5 reports integer
minutes; the ranks are what ρ compares). A pair the largest component cannot
join, or beyond the censor, is censored like R5's.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import osmium
import osmium.filter
import osmium.osm
import pandas as pd
import psutil
from pyproj import Transformer

from phillysim.destinations import SNAP_RETAILERS
from phillysim.routing import records
from phillysim.routing.matrix import MATRIX_FILE, Night
from phillysim.routing.plan import (
    POINTS_FILE,
    ROLE_DESTINATION,
    ROLE_ORIGIN,
    MatrixPlan,
    load_plan,
    read_points,
)
from phillysim.spine import ANALYSIS_CRS

CONCORDANCE_DIR = "concordance"
CONCORDANCE_FILE = "concordance.json"
FALLBACK_TIMES_FILE = "fallback_walk_times.parquet"
CACHE_DIR = "cache/concordance"
CONCORDANCE_SCHEMA_VERSION = 1
GATE = 0.95
DISABLED_URL = "disabled://no-network"
#: OSMnx 2.1.1's ``walk`` filter (``_overpass._get_network_filter``), as tag rules. Overpass'
#: ``!~`` is a regular-expression match, so every entry is a **substring** of the value.
EXCLUDED_HIGHWAY_SUBSTRINGS: tuple[str, ...] = (
    "abandoned",
    "bus_guideway",
    "construction",
    "cycleway",
    "motor",
    "no",
    "planned",
    "platform",
    "proposed",
    "raceway",
    "razed",
    "rest_area",
    "services",
)
SIDEWALK_KEYS: tuple[str, ...] = ("sidewalk", "sidewalk:both", "sidewalk:left", "sidewalk:right")


def walkable(tags: Mapping[str, str]) -> bool:
    """OSMnx's ``walk`` network filter as a predicate over a way's tags."""
    highway = tags.get("highway")
    if not highway:
        return False
    if "yes" in tags.get("area", ""):
        return False
    if "private" in tags.get("access", ""):
        return False
    if any(fragment in highway for fragment in EXCLUDED_HIGHWAY_SUBSTRINGS):
        return False
    if "no" in tags.get("foot", ""):
        return False
    if "private" in tags.get("service", ""):
        return False
    return not any("separate" in tags.get(key, "") for key in SIDEWALK_KEYS)


# --- the walkable ways as OSM XML -------------------------------------------------------------


def write_walk_xml(source: Path, target: Path) -> dict[str, Any]:
    """Select the walkable ways of ``source`` (a PBF) with their nodes and write them as OSM
    XML to ``target`` (two streaming passes; no relations; the source's order)."""
    src = str(source)
    keep_ways: set[int] = set()
    keep_nodes: set[int] = set()
    highway_ways = 0
    for way in osmium.FileProcessor(src, osmium.osm.WAY).with_filter(
        osmium.filter.KeyFilter("highway")
    ):
        highway_ways += 1
        if walkable(dict(way.tags)):
            keep_ways.add(way.id)
            keep_nodes.update(ref.ref for ref in way.nodes)
    if target.exists():
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    nodes = ways = 0
    with osmium.SimpleWriter(str(target)) as writer:
        processor = (
            osmium.FileProcessor(src, osmium.osm.NODE | osmium.osm.WAY)
            .with_filter(osmium.filter.IdFilter(keep_nodes).enable_for(osmium.osm.NODE))
            .with_filter(osmium.filter.IdFilter(keep_ways).enable_for(osmium.osm.WAY))
        )
        for obj in processor:
            if obj.is_node():
                nodes += 1
            else:
                ways += 1
            writer.add(obj)
    return {
        "source": source.name,
        "source_bytes": source.stat().st_size,
        "source_sha256": records.sha256_file(source),
        "file": target.name,
        "bytes": target.stat().st_size,
        "highway_ways": highway_ways,
        "walkable_ways": ways,
        "nodes": nodes,
    }


# --- the graph ----------------------------------------------------------------------------------


def configure_osmnx(ox: Any) -> dict[str, Any]:
    """Turn every path that could reach a server off: no cache, no Overpass, no Nominatim."""
    ox.settings.use_cache = False
    ox.settings.cache_only_mode = False
    ox.settings.log_console = False
    ox.settings.log_file = False
    ox.settings.overpass_url = DISABLED_URL
    ox.settings.nominatim_url = DISABLED_URL
    return {
        "use_cache": ox.settings.use_cache,
        "overpass_url": ox.settings.overpass_url,
        "nominatim_url": ox.settings.nominatim_url,
    }


def build_graph(xml_path: Path, *, crs: str = ANALYSIS_CRS) -> tuple[Any, dict[str, Any]]:
    """The walk graph from the XML: bidirectional, simplified, the largest component,
    projected to the analysis CRS. Returns the graph and its counts."""
    import osmnx as ox  # noqa: PLC0415 - the optional routing group

    configure_osmnx(ox)
    started = time.perf_counter()
    graph = ox.graph_from_xml(xml_path, bidirectional=True, simplify=True, retain_all=False)
    graph = ox.project_graph(graph, to_crs=crs)
    return graph, {
        "osmnx_version": ox.__version__,
        "nodes": int(graph.number_of_nodes()),
        "edges": int(graph.number_of_edges()),
        "edge_length_km": round(
            float(sum(d.get("length", 0.0) for _, _, d in graph.edges(data=True))) / 1000, 1
        ),
        "crs": crs,
        "build_seconds": round(time.perf_counter() - started, 1),
        "settings": configure_osmnx(ox),
    }


def walk_times(
    graph: Any,
    origins: pd.DataFrame,
    destinations: pd.DataFrame,
    *,
    speed_kmh: float,
    max_time_minutes: int,
    crs: str = ANALYSIS_CRS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Walk minutes from every origin to every destination (``id``, ``lon``, ``lat`` frames,
    WGS 84): the shortest path on the graph plus both snap distances at ``speed_kmh``;
    ``NaN`` where no path is within the censor."""
    import networkx as nx  # noqa: PLC0415 - the optional routing group
    import osmnx as ox  # noqa: PLC0415
    from scipy.sparse.csgraph import dijkstra  # noqa: PLC0415

    started = time.perf_counter()
    to_plane = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    ox_, oy_ = to_plane.transform(origins["lon"].to_numpy(), origins["lat"].to_numpy())
    dx_, dy_ = to_plane.transform(destinations["lon"].to_numpy(), destinations["lat"].to_numpy())
    o_nodes, o_snap = ox.distance.nearest_nodes(graph, ox_, oy_, return_dist=True)
    d_nodes, d_snap = ox.distance.nearest_nodes(graph, dx_, dy_, return_dist=True)
    digraph = ox.convert.to_digraph(graph, weight="length")
    nodelist = list(digraph.nodes)
    index = {node: i for i, node in enumerate(nodelist)}
    lengths = nx.to_scipy_sparse_array(digraph, nodelist=nodelist, weight="length", format="csr")
    metres_per_minute = speed_kmh * 1000.0 / 60.0
    radius = metres_per_minute * max_time_minutes
    o_index = np.asarray([index[n] for n in o_nodes])
    d_index = np.asarray([index[n] for n in d_nodes])
    path = dijkstra(lengths, directed=True, indices=o_index, limit=radius)
    metres = path[:, d_index] + np.asarray(o_snap)[:, None] + np.asarray(d_snap)[None, :]
    minutes = metres / metres_per_minute
    minutes = np.where(np.isfinite(minutes) & (minutes < max_time_minutes), minutes, np.nan)
    frame = pd.DataFrame(
        {
            "origin_geoid": np.repeat(origins["id"].astype(str).to_numpy(), len(destinations)),
            "site_id": np.tile(destinations["id"].astype(str).to_numpy(), len(origins)),
            "fallback_minutes": np.round(minutes.ravel(), 3),
            "fallback_metres": np.where(np.isfinite(metres), np.round(metres, 1), np.nan).ravel(),
        }
    )
    return frame, {
        "speed_kmh": speed_kmh,
        "max_time_minutes": max_time_minutes,
        "origins": int(len(origins)),
        "destinations": int(len(destinations)),
        "snap_distance_m": {
            "origins_max": round(float(np.max(o_snap)), 1),
            "origins_median": round(float(np.median(o_snap)), 1),
            "destinations_max": round(float(np.max(d_snap)), 1),
            "destinations_median": round(float(np.median(d_snap)), 1),
        },
        "route_seconds": round(time.perf_counter() - started, 1),
    }


# --- the comparison ----------------------------------------------------------------------------


def spearman(a: pd.Series, b: pd.Series) -> float:
    """Spearman's ρ as the Pearson correlation of average ranks (pandas' own ranking; the
    comparison runs where scipy is not installed, CI included)."""
    return float(a.rank(method="average").corr(b.rank(method="average")))


def compare(fallback: pd.DataFrame, r5: pd.DataFrame, *, max_time_minutes: int) -> dict[str, Any]:
    """Spearman ρ between the fallback's minutes and R5's typical minutes over the pairs both
    engines report under the censor, with the counts of what was excluded and why."""
    joined = fallback.merge(
        r5[["origin_geoid", "site_id", "time_median_min"]],
        on=["origin_geoid", "site_id"],
        how="inner",
    )
    r5_finite = joined["time_median_min"] < max_time_minutes
    fb_finite = joined["fallback_minutes"].notna() & (joined["fallback_minutes"] < max_time_minutes)
    both = joined[r5_finite & fb_finite]
    rho = spearman(both["fallback_minutes"], both["time_median_min"]) if len(both) > 2 else None
    pearson = (
        float(both["fallback_minutes"].corr(both["time_median_min"])) if len(both) > 2 else None
    )
    diff = both["fallback_minutes"] - both["time_median_min"]
    return {
        "pairs": int(len(joined)),
        "r5_finite_pairs": int(r5_finite.sum()),
        "fallback_finite_pairs": int(fb_finite.sum()),
        "pairs_compared": int(len(both)),
        "excluded_r5_censored_only": int((~r5_finite & fb_finite).sum()),
        "excluded_fallback_censored_only": int((r5_finite & ~fb_finite).sum()),
        "excluded_both_censored": int((~r5_finite & ~fb_finite).sum()),
        "spearman_rho": round(rho, 6) if rho is not None else None,
        "pearson_r": round(pearson, 6) if pearson is not None else None,
        "mean_abs_diff_minutes": round(float(diff.abs().mean()), 3) if len(both) else None,
        "median_abs_diff_minutes": round(float(diff.abs().median()), 3) if len(both) else None,
        "mean_diff_minutes": round(float(diff.mean()), 3) if len(both) else None,
        "median_ratio_fallback_over_r5": (
            round(
                float(
                    (both["fallback_minutes"] / both["time_median_min"].replace(0, np.nan)).median()
                ),
                4,
            )
            if len(both)
            else None
        ),
        "gate": GATE,
        "gate_met": bool(rho is not None and rho >= GATE),
    }


def _rss_bytes() -> int:
    info = psutil.Process().memory_info()
    return int(getattr(info, "peak_wset", info.rss))


def run_concordance(
    night_dir: Path,
    *,
    data_root: Path,
    walk_run: str | None = None,
    rebuild: bool = False,
    echo: Callable[[str], None] | None = None,
    supermarket_only: bool = True,
    plan: MatrixPlan | None = None,
) -> dict[str, Any]:
    """The concordance for a night: the fallback engine on the night's clip, its walk times
    for the night's origins × the supermarket-format destinations, and the comparison with
    the night's core walk run; ``concordance.json`` and the fallback's table under
    ``<night>/concordance/``."""
    say = echo or (lambda _line: None)
    night_dir, data_root = night_dir.resolve(), data_root.resolve()
    night = Night.load(night_dir)
    plan = plan or load_plan(night.data["plan"]["file"])
    walk_run = walk_run or next(r for r in plan.core_runs if plan.run(r).mode == "walk")
    run = plan.run(walk_run)
    points = read_points(night_dir / POINTS_FILE)
    origins = points[points["role"] == ROLE_ORIGIN][["id", "lon", "lat"]].reset_index(drop=True)
    destinations = points[points["role"] == ROLE_DESTINATION][["id", "lon", "lat"]]
    if supermarket_only:
        layer = pd.read_parquet(
            data_root / SNAP_RETAILERS, columns=["site_id", "supermarket_format"]
        )
        chosen = set(layer.loc[layer["supermarket_format"].astype(bool), "site_id"].astype(str))
        destinations = destinations[destinations["id"].astype(str).isin(chosen)]
    destinations = destinations.reset_index(drop=True)
    r5 = pd.read_parquet(night_dir / night.runs[walk_run]["dir"] / MATRIX_FILE)
    r5 = r5[r5["site_id"].isin(set(destinations["id"].astype(str)))]

    clip = data_root / night.data["inputs"]["osm"]
    xml = data_root / CACHE_DIR / f"{clip.name.removesuffix('.osm.pbf')}.walk.osm"
    if rebuild or not xml.is_file():
        say(f"concordance: selecting the walkable ways of {clip.name} into {xml.name}")
        selection = write_walk_xml(clip, xml)
        say(
            f"concordance: {selection['walkable_ways']} of {selection['highway_ways']} highway "
            f"ways walkable, {selection['nodes']} nodes, {selection['bytes'] / 10**6:.0f} MB"
        )
    else:
        selection = {"file": xml.name, "bytes": xml.stat().st_size, "reused": True}
    rss_after_selection = _rss_bytes()
    say("concordance: building the walk graph with OSMnx (no network call)")
    graph, graph_info = build_graph(xml)
    rss_after_graph = _rss_bytes()
    say(
        f"concordance: graph {graph_info['nodes']} nodes, {graph_info['edges']} edges, "
        f"{graph_info['edge_length_km']} km, in {graph_info['build_seconds']} s"
    )
    fallback, route_info = walk_times(
        graph,
        origins,
        destinations,
        speed_kmh=run.speed_walking_kmh,
        max_time_minutes=plan.max_time_minutes,
    )
    say(f"concordance: {len(fallback)} pairs routed in {route_info['route_seconds']} s")
    comparison = compare(fallback, r5, max_time_minutes=plan.max_time_minutes)
    say(
        f"concordance: Spearman rho {comparison['spearman_rho']} over "
        f"{comparison['pairs_compared']} finite pairs "
        f"({'meets' if comparison['gate_met'] else 'BELOW'} the {GATE} gate)"
    )
    directory = night_dir / CONCORDANCE_DIR
    directory.mkdir(exist_ok=True)
    fallback.to_parquet(directory / FALLBACK_TIMES_FILE, index=False)
    report = {
        "schema_version": CONCORDANCE_SCHEMA_VERSION,
        "night_id": night.id,
        "walk_run": walk_run,
        "r5_matrix_canonical_value_sha256": night.runs[walk_run]["matrix"][
            "canonical_value_sha256"
        ],
        "engine": "OSMnx graph_from_xml (bidirectional, simplified, largest component) + scipy "
        "sparse dijkstra on edge lengths; snap distances added at walking speed",
        "selection": selection,
        "graph": graph_info,
        "routing": route_info,
        "destinations": "supermarket-format retailers" if supermarket_only else "all retailers",
        "fallback_table": FALLBACK_TIMES_FILE,
        "peak_rss_bytes": max(rss_after_selection, rss_after_graph, _rss_bytes()),
        **comparison,
    }
    records.write_json(directory / CONCORDANCE_FILE, report, {"<data-root>": data_root})
    return report


def concordance_lines(report: Mapping[str, Any]) -> list[str]:
    graph, routing = report["graph"], report["routing"]
    verdict = "meets" if report["gate_met"] else "BELOW"
    return [
        f"concordance for night {report['night_id']} ({report['walk_run']} vs the fallback "
        f"engine, {report['destinations']}):",
        f"  graph: {graph['nodes']} nodes, {graph['edges']} edges, {graph['edge_length_km']} km; "
        f"build {graph['build_seconds']} s; routing {routing['route_seconds']} s; peak RSS "
        f"{report['peak_rss_bytes'] / 10**9:.2f} GB",
        f"  pairs {report['pairs']}: R5 finite {report['r5_finite_pairs']}, fallback finite "
        f"{report['fallback_finite_pairs']}, compared {report['pairs_compared']} (excluded: "
        f"R5 censored only {report['excluded_r5_censored_only']}, fallback censored only "
        f"{report['excluded_fallback_censored_only']}, both {report['excluded_both_censored']})",
        f"  Spearman rho {report['spearman_rho']} ({verdict} the {report['gate']} gate); "
        f"Pearson r {report['pearson_r']}; mean |diff| {report['mean_abs_diff_minutes']} min, "
        f"median |diff| {report['median_abs_diff_minutes']} min, mean diff (fallback - R5) "
        f"{report['mean_diff_minutes']} min, median ratio "
        f"{report['median_ratio_fallback_over_r5']}",
    ]


__all__: Sequence[str] = (
    "CACHE_DIR",
    "CONCORDANCE_DIR",
    "CONCORDANCE_FILE",
    "EXCLUDED_HIGHWAY_SUBSTRINGS",
    "GATE",
    "build_graph",
    "compare",
    "concordance_lines",
    "configure_osmnx",
    "run_concordance",
    "walk_times",
    "walkable",
    "write_walk_xml",
)
