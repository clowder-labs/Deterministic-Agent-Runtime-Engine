from dare_framework.hook._internal.decision_arbiter import arbitrate


def test_block_has_highest_precedence() -> None:
    winner = arbitrate([{"decision": "allow"}, {"decision": "block"}])
    assert winner["decision"] == "block"


def test_ask_has_higher_precedence_than_allow() -> None:
    winner = arbitrate([{"decision": "allow"}, {"decision": "ask"}])
    assert winner["decision"] == "ask"
