import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm_backend.inspect_ai_backend import _to_plain_messages


def test_plain_string_with_system_prompt_becomes_system_then_user():
    result = _to_plain_messages("diagnose this", system_prompt="You are a judge.")

    assert result == [
        {"role": "system", "content": "You are a judge."},
        {"role": "user", "content": "diagnose this"},
    ]


def test_plain_string_without_system_prompt_becomes_just_user():
    result = _to_plain_messages("diagnose this", system_prompt=None)

    assert result == [{"role": "user", "content": "diagnose this"}]


def test_langchain_message_list_is_converted_role_by_role():
    messages = [
        SystemMessage(content="You are a judge."),
        HumanMessage(content="diagnose this"),
        AIMessage(content="here is my answer"),
    ]

    result = _to_plain_messages(messages, system_prompt=None)

    assert result == [
        {"role": "system", "content": "You are a judge."},
        {"role": "user", "content": "diagnose this"},
        {"role": "assistant", "content": "here is my answer"},
    ]


def test_unsupported_message_type_raises():
    class Weird:
        content = "???"

    with pytest.raises(TypeError, match="Unsupported message type"):
        _to_plain_messages([Weird()], system_prompt=None)
