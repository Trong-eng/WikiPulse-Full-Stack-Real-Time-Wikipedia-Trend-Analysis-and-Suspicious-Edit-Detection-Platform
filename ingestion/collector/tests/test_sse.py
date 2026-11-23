from ingestion.collector.app.sse import parse_sse


def test_sse_joins_data_and_preserves_opaque_id():
    events = list(parse_sse([": heartbeat", 'id: [{"offset":1}]', "data: first",
                             "data: second", "", "data: next", ""]))
    assert [(event.data, event.id) for event in events] == [
        ("first\nsecond", '[{"offset":1}]'), ("next", '[{"offset":1}]')
    ]


def test_sse_discards_incomplete_event_at_eof():
    assert list(parse_sse(["data: incomplete"])) == []


def test_sse_handles_empty_id_and_ignores_nul_id():
    events = list(parse_sse(["id: one", "data: a", "", "id: bad\x00id", "data: b", "",
                             "id:", "data: c", ""]))
    assert [event.id for event in events] == ["one", "one", ""]


def test_sse_uses_previous_id_after_reconnect():
    events = list(parse_sse(["data: continued", ""], initial_id="old"))
    assert events[0].id == "old"


def test_sse_ignores_initial_bom():
    events = list(parse_sse(["\ufeffid: initial", "data: value", ""]))
    assert events[0].id == "initial"
