"""Structured records handling package (Phase 7).

Provides validation, normalization, and relationship adapters for:
- Call Detail Records (CDR)
- Financial transaction records
"""

from ml.structured.cdr import CDRRecord, cdr_to_relationship, parse_cdr, parse_cdrs
from ml.structured.transactions import (
    TransactionRecord,
    parse_transaction,
    parse_transactions,
    transaction_to_relationship,
)

__all__ = [
    "CDRRecord",
    "parse_cdr",
    "parse_cdrs",
    "cdr_to_relationship",
    "TransactionRecord",
    "parse_transaction",
    "parse_transactions",
    "transaction_to_relationship",
]
