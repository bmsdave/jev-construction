from packs.building_control.labels import stratified_split


def test_split_is_deterministic_and_holds_out_about_30_percent_of_each_label():
    rows = [{"id": f"r{i}", "label": "a" if i < 20 else "b"} for i in range(30)]
    s1, s2 = stratified_split(rows, share=0.3, seed=7), stratified_split(rows, share=0.3, seed=7)
    assert s1 == s2
    assert sum(1 for r in rows if r["label"] == "a" and s1[r["id"]] == "test") == 6
    assert sum(1 for r in rows if r["label"] == "b" and s1[r["id"]] == "test") == 3
