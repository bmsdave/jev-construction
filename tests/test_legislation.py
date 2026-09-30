from pathlib import Path

from core.legislation import clauses_from_xml

FIXTURE = (Path(__file__).parent / "fixtures" / "legislation_sample.xml").read_text()


def by_ref(clauses):
    return {c.ref: c for c in clauses}


def test_second_level_paragraph_becomes_one_clause_with_its_subitems():
    c = by_ref(clauses_from_xml(FIXTURE, doc="BR2010"))["reg 12(6A)"]
    assert c.text == ("(6A) A person intending to carry out building work is required to give a building notice "
                      "where the work consists of— (a) the installation of a new circuit;")
    assert c.doc == "BR2010"
    assert c.id == "BR2010:reg-12-6A"
    assert c.url == "https://www.legislation.gov.uk/uksi/2010/2214/regulation/12/6A"


def test_other_extent_repealed_text_and_commentary_are_dropped():
    clauses = clauses_from_xml(FIXTURE, doc="BR2010")
    text = " ".join(c.text for c in clauses)
    assert "Welsh version" not in text
    assert "S.I. 2023/1234" not in text
    assert "reg 12(5)" not in by_ref(clauses)


def test_schedule_paragraph_without_children_is_one_clause():
    c = by_ref(clauses_from_xml(FIXTURE, doc="BR2010"))["Sch 4 para 2"]
    assert c.text == "(2) Work which consists of adding socket outlets to an existing ring circuit."


def test_table_row_becomes_clause_referenced_by_its_number():
    c = by_ref(clauses_from_xml(FIXTURE, doc="BR2010"))["Sch 3 para 10"]
    assert c.text == ("10. Installation, as a replacement, of a window in an existing dwelling. | "
                      "A person registered by Fensa Limited.")
    assert c.url == "https://www.legislation.gov.uk/uksi/2010/2214/schedule/3"


def test_paragraph_with_few_subitems_stays_whole_because_they_read_together():
    refs = by_ref(clauses_from_xml(FIXTURE, doc="BR2010"))
    assert refs["Sch 4 para 3"].text == "(3) Work on— (a) telephone wiring; (b) equipment associated with that wiring."
    assert "Sch 4 para 3(a)" not in refs


def test_schedule_part_is_cited_as_part():
    c = by_ref(clauses_from_xml(FIXTURE, doc="BR2010"))["Sch 2 Part 6 para 1"]
    assert c.id == "BR2010:sch-2-Part-6-para-1"


def test_schedule_1_requirement_row_is_cited_by_requirement_and_titled_by_heading_row():
    c = by_ref(clauses_from_xml(FIXTURE, doc="BR2010"))["Sch 1 A1"]
    assert c.text == "Loading: A1.—(1) The building shall be constructed so that loads are sustained safely."


def test_unnumbered_paragraph_of_a_schedule_part_is_cited_by_the_part():
    c = by_ref(clauses_from_xml(FIXTURE, doc="BR2010"))["Sch 2 Part 7"]
    assert c.text == "The extension of a building by the addition at ground level of— (a) a conservatory or porch,"
