from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class RecordType(str, Enum):
    CDR = "CDR"
    TRANSACTION = "TRANSACTION"
