"""Neo4j uniqueness constraints for MERGE-safe canonical lookups.

Application identity is always the PostgreSQL UUID:
- entity nodes: entity_id = entities.id
- Case: case_id = cases.id
- Document: document_id = documents.id

Never use Neo4j internal IDs or ML grouping IDs as graph identity.
"""

ENTITY_LABELS = (
    "Person",
    "Phone",
    "BankAccount",
    "Vehicle",
    "Organization",
    "Location",
    "Event",
)

RELATIONSHIP_TYPES = (
    "CALLED",
    "SENT_MONEY_TO",
    "OWNS_VEHICLE",
    "USED_VEHICLE",
    "WORKS_FOR",
    "LOCATED_AT",
    "ASSOCIATED_WITH",
    "PART_OF_EVENT",
)

CONSTRAINTS = [
    *[
        (
            f"{label.lower()}_entity_id",
            f"CREATE CONSTRAINT {label.lower()}_entity_id IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.entity_id IS UNIQUE",
        )
        for label in ENTITY_LABELS
    ],
    (
        "case_case_id",
        "CREATE CONSTRAINT case_case_id IF NOT EXISTS "
        "FOR (n:Case) REQUIRE n.case_id IS UNIQUE",
    ),
    (
        "document_document_id",
        "CREATE CONSTRAINT document_document_id IF NOT EXISTS "
        "FOR (n:Document) REQUIRE n.document_id IS UNIQUE",
    ),
    *[
        (
            f"{rel_type.lower()}_relationship_id",
            f"CREATE CONSTRAINT {rel_type.lower()}_relationship_id IF NOT EXISTS "
            f"FOR ()-[r:{rel_type}]-() REQUIRE r.relationship_id IS UNIQUE",
        )
        for rel_type in RELATIONSHIP_TYPES
    ],
]


def init_schema(driver) -> list[str]:
    names: list[str] = []
    with driver.session() as session:
        for name, cypher in CONSTRAINTS:
            session.run(cypher)
            names.append(name)
    return names


def list_constraint_names(driver) -> set[str]:
    with driver.session() as session:
        result = session.run("SHOW CONSTRAINTS YIELD name RETURN name")
        return {record["name"] for record in result}
