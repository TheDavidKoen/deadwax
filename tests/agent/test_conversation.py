from deadwax.agent.conversation import Exchange, opening_messages, remember

ROCK = Exchange("any rock songs?", "None are tagged rock. Shall I count art rock instead?")


def test_a_first_question_is_sent_alone():
    assert opening_messages("any rock songs?") == [{"role": "user", "content": "any rock songs?"}]


def test_earlier_exchanges_come_before_the_new_question_in_order():
    messages = opening_messages("yes", [ROCK])
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == ROCK.question
    assert messages[1]["content"] == ROCK.answer
    assert messages[-1]["content"] == "yes"


def test_only_the_most_recent_exchanges_are_kept():
    history: tuple[Exchange, ...] = ()
    for n in range(5):
        history = remember(history, Exchange(f"q{n}", f"a{n}"), limit=3)
    assert [e.question for e in history] == ["q2", "q3", "q4"]


def test_a_limit_of_zero_remembers_nothing():
    assert remember((ROCK,), ROCK, limit=0) == ()


def test_history_carries_text_only_so_the_supervisor_sees_no_old_tool_calls():
    for message in opening_messages("yes", [ROCK]):
        assert set(message) == {"role", "content"}
