from enum import Enum


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


class ResolutionSignal(str, Enum):
    NAME_SIMILARITY = "name_similarity"
    PHONE_MATCH = "phone_match"
    ACCOUNT_MATCH = "account_match"
    VEHICLE_MATCH = "vehicle_match"
    LOCATION_MATCH = "location_match"
    ORGANIZATION_MATCH = "organization_match"


class PatternType(str, Enum):
    CIRCULAR_TRANSACTION = "CIRCULAR_TRANSACTION"
    RAPID_TRANSFER_CHAIN = "RAPID_TRANSFER_CHAIN"
    LOCATION_TIME_OVERLAP = "LOCATION_TIME_OVERLAP"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class LeadType(str, Enum):
    FINANCIAL_NETWORK = "FINANCIAL_NETWORK"
    CIRCULAR_TRANSACTION = "CIRCULAR_TRANSACTION"
    RAPID_TRANSFER_CHAIN = "RAPID_TRANSFER_CHAIN"
    LOCATION_TIME_OVERLAP = "LOCATION_TIME_OVERLAP"
    CROSS_CASE = "CROSS_CASE"


class LeadPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class LeadStatus(str, Enum):
    """Investigative workflow status. Distinct from priority."""

    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PREDICTED = "PREDICTED"
