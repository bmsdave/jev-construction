from core.approved_docs import clauses_from_text

SAMPLE = """Contents
Section 2: Application of Part P
2.1 All electrical installation work carried out in a dwelling is subject to requirement P1, and should
be designed and installed in accordance with BS 7671.

ONLINE VERSION
14
Approved Document P
2.5 Electrical installation work that is notifiable is set out in regulation 12(6A).
Section 3: Certification, inspection and testing
3.1 For notifiable electrical installation work, one of the following three procedures must be used.
1.3 Part P covers the safety of electrical installation work.
"""


def refs(clauses):
    return {c.ref: c for c in clauses}


def test_numbered_paragraph_spans_lines_until_next_paragraph_without_page_furniture():
    c = refs(clauses_from_text(SAMPLE, doc="ADP2013", sections={"2", "3"}, url="https://x/ad_p.pdf"))["para 2.1"]
    assert c.text == ("2.1 All electrical installation work carried out in a dwelling is subject to requirement P1, "
                      "and should be designed and installed in accordance with BS 7671.")
    assert c.id == "ADP2013:para-2-1"
    assert c.url == "https://x/ad_p.pdf"


def test_section_heading_ends_a_paragraph_and_only_chosen_sections_are_kept():
    got = refs(clauses_from_text(SAMPLE, doc="ADP2013", sections={"2", "3"}, url=""))
    assert got["para 2.5"].text == "2.5 Electrical installation work that is notifiable is set out in regulation 12(6A)."
    assert "para 3.1" in got
    assert "para 1.3" not in got


def test_paragraph_number_alone_on_its_line_starts_a_paragraph():
    text = "Introduction\n1.1\nThis section is relevant to all building types\nand lists codes.\n\nReferences\n1.2\n"
    got = refs(clauses_from_text(text, doc="ADA2013", sections={"1"}, url=""))
    assert got["para 1.1"].text == "1.1 This section is relevant to all building types and lists codes. References"


def test_cross_reference_wrapped_to_line_start_does_not_start_a_paragraph():
    text = "11.1 This section covers work to elements.\nSee Diagram 11.1 and Diagram\n11.2 and Diagram 11.3, respectively.\n"
    got = refs(clauses_from_text(text, doc="ADL1", sections={"11"}, url=""))
    assert got["para 11.1"].text.endswith("Diagram 11.2 and Diagram 11.3, respectively.")
    assert "para 11.2" not in got


def test_overlong_paragraph_is_cut_so_it_fits_a_jev_state():
    text = "2.1 Start " + "word " * 1000
    c = refs(clauses_from_text(text, doc="X", sections={"2"}, url=""))["para 2.1"]
    assert len(c.text) <= 1500 and c.text.endswith(" …")
