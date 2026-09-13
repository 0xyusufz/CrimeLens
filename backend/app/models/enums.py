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


class RelationshipType(str, Enum):
    CALLED = "CALLED"
    SENT_MONEY_TO = "SENT_MONEY_TO"
    OWNS_VEHICLE = "OWNS_VEHICLE"
    USED_VEHICLE = "USED_VEHICLE"
    WORKS_FOR = "WORKS_FOR"
    LOCATED_AT = "LOCATED_AT"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    PART_OF_EVENT = "PART_OF_EVENT"


class RelationshipStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    INFERRED = "INFERRED"
    PREDICTED = "PREDICTED"
