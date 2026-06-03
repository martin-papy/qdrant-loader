SCHEMA_VERSION_NODE = "_SchemaVersion"


def get_version_query() -> str:
    return f"""
        MATCH (s:{SCHEMA_VERSION_NODE} {{id: "schema"}})
        RETURN s.version AS version
    """


def set_version_query() -> str:
    return f"""
    MERGE (s:{SCHEMA_VERSION_NODE} {{id: "schema"}})
    SET s.version = $version
    """
