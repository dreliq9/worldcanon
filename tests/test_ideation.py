import pytest

from worldcanon.ideation import (
    SessionNotFoundError,
    append_turn,
    end_session,
    get_session,
    install_ideation_schema,
    start_session,
)
from worldcanon.store import open_store


@pytest.fixture
def con(tmp_path):
    store = open_store(tmp_path / "t.sqlite", dim=4)
    c = store.connection()
    install_ideation_schema(c)
    yield c
    store.close()


def test_start_session_returns_id(con):
    sid = start_session(con, entity="Aerin", entity_type="character")
    assert isinstance(sid, str)
    assert len(sid) >= 6


def test_get_session_returns_state(con):
    sid = start_session(con, entity="Aerin", entity_type="character")
    state = get_session(con, sid)
    assert state["entity"] == "Aerin"
    assert state["entity_type"] == "character"
    assert state["transcript"] == []
    assert state["addressed_gaps"] == []
    assert state["ended_at"] is None


def test_get_session_unknown_raises(con):
    with pytest.raises(SessionNotFoundError):
        get_session(con, "nonexistent")


def test_append_turn_grows_transcript(con):
    sid = start_session(con, entity="A", entity_type="character")
    append_turn(con, sid, role="ai", content="What does A want?")
    append_turn(con, sid, role="writer", content="To be free.")
    state = get_session(con, sid)
    assert len(state["transcript"]) == 2
    assert state["transcript"][0]["role"] == "ai"
    assert state["transcript"][1]["content"] == "To be free."


def test_append_turn_records_addressed_gap(con):
    sid = start_session(con, entity="A", entity_type="character")
    append_turn(con, sid, role="writer", content="X", addressed_gap="Motivation / what they want")
    state = get_session(con, sid)
    assert "Motivation / what they want" in state["addressed_gaps"]


def test_end_session_marks_timestamp(con):
    sid = start_session(con, entity="A", entity_type="character")
    end_session(con, sid)
    state = get_session(con, sid)
    assert state["ended_at"] is not None
