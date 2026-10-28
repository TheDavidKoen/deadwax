import asyncio
import json

from mcp import Client

from deadwax.agent.loop import SYSTEM_PROMPT
from deadwax.agent.tools import TOOLS, query_library
from deadwax.data import library
from deadwax.mcp.server import build_server


def listed_tools() -> list:
    async def listing() -> list:
        async with Client(build_server()) as client:
            return (await client.list_tools()).tools

    return asyncio.run(listing())


def called(name: str, arguments: dict) -> dict:
    async def calling() -> dict:
        async with Client(build_server()) as client:
            result = await client.call_tool(name, arguments)
            return json.loads(result.content[0].text)

    return asyncio.run(calling())


def test_the_server_offers_exactly_the_agents_tools():
    assert sorted(t.name for t in listed_tools()) == sorted(t.name for t in TOOLS)


def test_every_description_is_the_agents_description_verbatim():
    agent_descriptions = {t.name: t.description for t in TOOLS}
    for tool in listed_tools():
        assert tool.description == agent_descriptions[tool.name]


def test_every_tool_is_declared_read_only():
    for tool in listed_tools():
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False


def test_the_system_prompt_travels_as_the_server_instructions():
    async def instructions() -> str | None:
        async with Client(build_server()) as client:
            return client.instructions

    assert asyncio.run(instructions()) == SYSTEM_PROMPT


def test_a_call_returns_what_the_tool_computes(monkeypatch):
    monkeypatch.setenv(library.LIBRARY_VARIABLE, library.FIXTURES)
    over_mcp = called("query_library", {"genre": "jazz", "limit": 0})
    direct = query_library.invoke({"genre": "jazz", "limit": 0})
    assert over_mcp["total_matching"] == direct["total_matching"]
    assert over_mcp["total_duration_display"] == direct["total_duration_display"]
