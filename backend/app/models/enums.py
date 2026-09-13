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


class EntityType(str, Enum):
    PERSON = "PERSON"
    PHONE = "PHONE"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    VEHICLE = "VEHICLE"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
