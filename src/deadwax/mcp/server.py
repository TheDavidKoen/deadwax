from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from deadwax.agent.loop import SYSTEM_PROMPT
from deadwax.agent.tools import TOOLS
from deadwax.config import load_env_file

SERVER_NAME = "deadwax"
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)


def build_server() -> MCPServer:
    server = MCPServer(SERVER_NAME, instructions=SYSTEM_PROMPT)
    for tool in TOOLS:
        server.add_tool(
            tool.func,
            name=tool.name,
            description=tool.description,
            annotations=READ_ONLY,
        )
    return server


def main() -> None:
    load_env_file()
    build_server().run()


if __name__ == "__main__":
    main()
