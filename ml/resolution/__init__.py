"""Entity resolution subpackage."""

from ml.resolution.resolver import compare_mentions, propose_resolutions
from ml.resolution.case_memory import propose_case_memory_links
from ml.resolution.contradiction import detect_contradictions

__all__ = [
    "compare_mentions",
    "detect_contradictions",
    "propose_case_memory_links",
    "propose_resolutions",
]
