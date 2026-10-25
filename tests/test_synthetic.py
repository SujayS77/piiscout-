from piiscout.synthetic import ENTITY_TYPES, generate_dataset


def test_offsets_match_values():
    for rec in generate_dataset(n=200, seed=1):
        for e in rec["entities"]:
            assert rec["text"][e["start"] : e["end"]] == e["value"]


def test_same_seed_gives_same_data():
    assert generate_dataset(50, seed=7) == generate_dataset(50, seed=7)
    assert generate_dataset(50, seed=7) != generate_dataset(50, seed=8)


def test_entity_types_are_known_and_all_appear():
    seen = set()
    for rec in generate_dataset(n=300, seed=3):
        for e in rec["entities"]:
            assert e["type"] in ENTITY_TYPES
            seen.add(e["type"])
    assert seen == set(ENTITY_TYPES)


def test_contains_hard_variants_and_negative_samples():
    recs = generate_dataset(n=300, seed=3)
    assert any(e["hard"] for r in recs for e in r["entities"])
    assert any(not r["entities"] for r in recs)


def test_entities_do_not_overlap():
    for rec in generate_dataset(n=200, seed=5):
        spans = sorted((e["start"], e["end"]) for e in rec["entities"])
        for (_, end), (start, _) in zip(spans, spans[1:]):
            assert end <= start
