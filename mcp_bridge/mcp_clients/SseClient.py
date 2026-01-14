import asyncio
from mcp.client.sse import sse_client
from mcp_bridge.config import config
from mcp_bridge.config.final import SSEMCPServer
from mcp_bridge.mcp_clients.session import McpClientSession
from .AbstractClient import GenericMcpClient
from loguru import logger


class SseClient(GenericMcpClient):
    config: SSEMCPServer

    def __init__(self, name: str, config: SSEMCPServer) -> None:
        super().__init__(name=name)

        self.config = config
        self._tools_cache = []  # Cache for tools list

    async def _maintain_session(self):
        async with sse_client(self.config.url) as client:
            async with McpClientSession(*client) as session:
                await session.initialize()
                logger.info(f"✅ {self.name} SSE session initialized")

                self.session = session

                # Load and cache tools (may fail, should not break the session)
                logger.info(f"🔍 Attempting to load tools for {self.name}...")
                try:
                    import asyncio
                    tools_result = await asyncio.wait_for(session.list_tools(), timeout=30.0)
                    self._tools_cache = tools_result.tools
                    logger.info(f"✅ {self.name} 已加载 {len(self._tools_cache)} 个工具")
                except asyncio.TimeoutError:
                    logger.error(f"⏱️ Timeout loading tools for {self.name} (30s)")
                except Exception as e:
                    logger.error(f"⚠️ 无法获取工具列表 {self.name}: {type(e).__name__}: {e}")
                    import traceback
                    logger.error(f"Stack trace:\n{traceback.format_exc()}")

                try:
                    while True:
                        await asyncio.sleep(10)
                        if config.logging.log_server_pings:
                            logger.debug(f"pinging session for {self.name}")

                        await session.send_ping()

                except Exception as exc:
                    logger.error(f"ping failed for {self.name}: {exc}")
                    self.session = None

        logger.debug(f"exiting session for {self.name}")
