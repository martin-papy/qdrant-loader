SCHEMA_VERSION_NODE = "SchemaVersion"


def get_version_query() -> str:
    return """
        MATCH (s:_SchemaVersion {id: "schema"})
        RETURN s.version
    """


def set_version_query() -> str:
    return """
    MERGE (s:_SchemaVersion {id: "schema"})
    SET s.version = $version
    """
