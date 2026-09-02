"""phillysim: measures access to health-relevant community resources across Philadelphia.

Descriptive access measurement at the 2020 census-tract level. Not simulation,
prediction, or clinical decision support; no scores or rankings (docs/CLAIMS.md).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("phillysim")
except PackageNotFoundError:  # pragma: no cover - source tree without an install
    __version__ = "0+unknown"

__all__ = ["__version__"]
