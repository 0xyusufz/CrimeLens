"""Evidence-first intelligence utilities used by the ML pipeline.

The package is deliberately database- and transport-free.  It adds internal
quality metadata around the frozen ``shared.schemas`` contract without adding
fields to that contract or introducing another HTTP surface.
"""

from ml.intelligence.document_understanding import (
    DocumentUnderstanding,
    EvidenceBlock,
    understand_document,
)
from ml.intelligence.candidates import integrate_ai_candidates
from ml.intelligence.orphans import analyze_orphans
from ml.intelligence.quality import (
    GraphQualityReport,
    apply_graph_quality_firewall,
)
from ml.intelligence.sos import SosAssessment, assess_sos

__all__ = [
    "DocumentUnderstanding",
    "EvidenceBlock",
    "GraphQualityReport",
    "SosAssessment",
    "apply_graph_quality_firewall",
    "analyze_orphans",
    "assess_sos",
    "integrate_ai_candidates",
    "understand_document",
]
