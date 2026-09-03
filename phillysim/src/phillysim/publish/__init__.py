"""The publication boundary: license buckets, build-time bins, the public-zone export, and the
publish gate (EP-7).

Nothing leaves the curated zone except through :func:`phillysim.publish.export.build_public_zone`,
which writes every public file with its license label and runs the gate
(:mod:`phillysim.publish.gate`) on the result before the runner installs it; the
``phillysim gate`` command re-checks an installed public zone at any time (CI runs it
on the fixture). ADR-0003 fixes the two buckets; the gate is the reusable artifact
this packet was for.
"""
