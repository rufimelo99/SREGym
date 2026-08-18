import asyncio

import pytest
from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm_backend.inspect_ai_backend import _run_sync, _to_inspect_messages


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


async def _return_42():
    return 42


def test_run_sync_works_from_a_plain_sync_context():
    assert _run_sync(_return_42) == 42


def test_run_sync_works_from_inside_an_already_running_event_loop():
    # This is the exact bug hit in production: inference() is called from
    # SREGym's judge preflight, which itself runs inside inspect_ai's async
    # solver -- i.e. inside an already-running event loop. A naive
    # asyncio.run() there raises "cannot be called from a running event
    # loop"; _run_sync must handle it by running on a separate thread.
    async def call_from_within_a_loop():
        return _run_sync(_return_42)

    assert asyncio.run(call_from_within_a_loop()) == 42


def test_run_sync_propagates_exceptions_raised_inside_an_event_loop():
    async def _raise():
        raise ValueError("boom")

    async def call_from_within_a_loop():
        return _run_sync(_raise)

    with pytest.raises(ValueError, match="boom"):
        asyncio.run(call_from_within_a_loop())
