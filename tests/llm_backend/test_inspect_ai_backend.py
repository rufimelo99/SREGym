import pytest
from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm_backend.inspect_ai_backend import _to_inspect_messages


def test_plain_string_with_system_prompt_becomes_system_then_user():
    result = _to_inspect_messages("diagnose this", system_prompt="You are a judge.")

    assert len(result) == 2
    assert isinstance(result[0], ChatMessageSystem)
    assert result[0].content == "You are a judge."
    assert isinstance(result[1], ChatMessageUser)
    assert result[1].content == "diagnose this"


def test_plain_string_without_system_prompt_becomes_just_user():
    result = _to_inspect_messages("diagnose this", system_prompt=None)

    assert len(result) == 1
    assert isinstance(result[0], ChatMessageUser)
    assert result[0].content == "diagnose this"


def test_langchain_message_list_is_converted_role_by_role():
    messages = [
        SystemMessage(content="You are a judge."),
        HumanMessage(content="diagnose this"),
        AIMessage(content="here is my answer"),
    ]

    result = _to_inspect_messages(messages, system_prompt=None)

    assert [type(m) for m in result] == [ChatMessageSystem, ChatMessageUser, ChatMessageAssistant]
    assert [m.content for m in result] == ["You are a judge.", "diagnose this", "here is my answer"]


def test_unsupported_message_type_raises():
    class Weird:
        content = "???"

    with pytest.raises(TypeError, match="Unsupported message type"):
        _to_inspect_messages([Weird()], system_prompt=None)
