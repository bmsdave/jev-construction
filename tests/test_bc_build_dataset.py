from packs.building_control.build_dataset import scope_rows

HOUSE = [{"phase": "P5", "zone": "OFFICE", "trade": "Electrical", "item": "Office distribution board",
          "contracted_net_likely": "900", "how": "For the GBP 7,500 grant ...", "legal_key": "partp",
          "diy_allowed": "Yes, notify"}]
LABELS = [{"row": "1", "label": "competent_person_scheme", "gold_clauses": "BR2010:reg-9-3",
           "confidence": "high", "rationale": "Part P applies to outbuildings."}]


def test_scope_row_keeps_item_and_zone_context_but_no_money_and_keeps_old_label_as_candidate():
    [r] = scope_rows(HOUSE, LABELS)
    assert r["id"] == "s001" and r["text"] == "Office distribution board"
    assert r["context"] == ("Renovation of a terraced house (dwelling) in England. Trade: Electrical. "
                            "Part of: detached single-storey garden office, under 15 m2, no sleeping accommodation.")
    assert r["candidate_label"] == "partp" and r["provenance"] == "house-scope200 (relabelled)"
    assert "900" not in str(r) and "GBP" not in str(r)


def test_unlabelled_rows_are_left_out():
    assert scope_rows(HOUSE, []) == []


def test_reference_rows_keep_their_source_and_are_held_out_as_a_reference_split():
    from packs.building_control.build_dataset import reference_rows
    [r] = reference_rows([{"id": "re001", "text": "Replace a consumer unit", "context": "House in England",
                           "label": "competent_person_scheme", "gold_clauses": "BR2010:reg-12-6A",
                           "source_org": "LABC", "source_url": "https://www.labc.co.uk/x",
                           "source_claim": "Consumer unit replacement is notifiable.", "confidence": "high"}])
    assert r["split"] == "reference" and r["provenance"] == "reference: LABC https://www.labc.co.uk/x"
    assert r["rationale"] == "Consumer unit replacement is notifiable."
