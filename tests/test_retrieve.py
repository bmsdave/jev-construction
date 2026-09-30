from core.clause import Clause
from core.retrieve import BM25, tokens


def cl(i, text):
    return Clause(id=f"T:{i}", doc="T", ref=str(i), text=text)


CORPUS = [
    cl(1, "Installation, as a replacement, of a window, rooflight, roof window or door in an existing dwelling."),
    cl(2, "Adding socket outlets and fused spurs to an existing ring or radial circuit, not in a kitchen."),
    cl(3, "The installation of a new circuit or the replacement of a consumer unit."),
    cl(4, "The building shall be constructed so that loads are sustained and transmitted to the ground."),
]


def test_tokens_lowercase_drop_stopwords_and_strip_common_suffixes():
    assert tokens("Adding the Sockets to a Circuit, replacement") == ["add", "socket", "circuit", "replace"]


def test_query_ranks_the_clause_sharing_rare_terms_first():
    hits = BM25(CORPUS).search("replace consumer unit in hallway", k=2)
    assert [c.id for c, _ in hits][0] == "T:3"
    assert len(hits) == 2


def test_clause_with_no_shared_terms_is_not_returned():
    hits = BM25(CORPUS).search("roof window", k=4)
    assert "T:4" not in [c.id for c, _ in hits]
    assert hits[0][0].id == "T:1"
