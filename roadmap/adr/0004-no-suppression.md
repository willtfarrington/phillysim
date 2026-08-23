# ADR-0004: No privacy-based small-cell suppression; reliability flags instead

Status: accepted (Planning Baseline v1.0 / RT-3 resolution, 2026-08-23)

## Context
All published quantities derive from public aggregate or public facility
data; suppression would protect nothing while degrading the transparency the
project exists to demonstrate. A contradictory suppression apparatus had
crept into four planning documents and was reconciled out.

## Decision
No privacy-based suppression. Statistical instability is handled by CV-based
reliability tiers (12%/40%) with `reliability_action ∈ {none, interval-only}`;
mosaic/stigma risk by non-ranking presentation and language rules; upstream
provider-suppressed values stay missing (never imputed). The published
methods documentation carries the rationale. Pipeline and UI contain
reliability-flag verification, not suppression stages.

## Consequences
Coherent public story; less machinery. Revisit only if a future source is
not fully public-aggregate (which would trigger the gated-module review
anyway).
