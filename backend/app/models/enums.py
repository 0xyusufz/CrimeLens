from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
