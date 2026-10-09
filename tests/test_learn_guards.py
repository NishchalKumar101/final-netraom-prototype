import pytest

from app.learn_cypher import validate_cypher
from app.learn_postgres import validate_select_only


def test_sql_allows_select():
    assert validate_select_only("SELECT 1").startswith("SELECT")


def test_sql_rejects_delete():
    with pytest.raises(ValueError, match="SELECT"):
        validate_select_only("DELETE FROM assets")


def test_cypher_requires_tenant():
    with pytest.raises(ValueError, match="tenant"):
        validate_cypher("MATCH (n) RETURN n LIMIT 1")


def test_cypher_rejects_merge():
    tid = "11111111-1111-4111-8111-111111111111"
    with pytest.raises(ValueError, match="Write"):
        validate_cypher(f"MERGE (n:TrustGraphNode {{tenant_id: '{tid}'}}) RETURN n")
