"""HTTP MCP Client - 通过HTTP POST JSON-RPC 2.0协议连接MCP服务器"""

import asyncio
import httpx
import json
from loguru import logger
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
    ListResourcesResult,
    ListPromptsResult,
)
from mcp_bridge.config.final import HTTPMCPServer
from .AbstractClient import GenericMcpClient


class HttpClient(GenericMcpClient):
    """HTTP MCP客户端 - 使用HTTP POST和JSON-RPC 2.0协议
    
    这个客户端不使用持久会话，而是为每个请求创建独立的HTTP请求。
    """
    
    config: HTTPMCPServer

    def __init__(self, name: str, config: HTTPMCPServer) -> None:
        super().__init__(name=name)
        self.config = config
        self._http_client: httpx.AsyncClient | None = None
        self._request_id = 0
        self._session_id: str | None = None
        self._is_initialized = False
        self._tools_cache: list[Tool] = []

    def _get_next_id(self) -> int:
        """获取下一个请求ID"""
        self._request_id += 1
        return self._request_id

    async def _send_jsonrpc_request(self, method: str, params: dict | None = None) -> dict:
        """发送JSON-RPC 2.0请求"""
        if not self._http_client:
            raise RuntimeError("HTTP客户端未初始化")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._get_next_id()
        }
        
        if params:
            request_data["params"] = params
        
        headers = {"Content-Type": "application/json"}
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        
        try:
            logger.debug(f"📡 发送MCP请求到 {self.name}: {method} params={params}")
            response = await self._http_client.post(
                self.config.url,
                json=request_data,
                headers=headers,
                timeout=30.0
            )

            logger.debug(f"📥 MCP原始响应 {self.name}: status={response.status_code}")

            if response.status_code != 200:
                logger.error(f"❌ MCP请求失败 {self.name}: {response.status_code} - {response.text}")
                raise RuntimeError(f"MCP请求失败: {response.status_code}")

            result = response.json()
            logger.debug(f"📥 MCP响应 {self.name}: {result}")

            # 检查错误
            if result.get("error") is not None:
                error = result["error"]
                error_msg = error.get('message', str(error)) if isinstance(error, dict) else str(error)
                logger.error(f"❌ MCP错误 {self.name}: {error_msg}")
                raise RuntimeError(f"MCP错误: {error_msg}")

            # 返回结果
            if "result" in result:
                return result["result"]
            return result
            
        except httpx.HTTPError as e:
            error_msg = str(e) or repr(e) or type(e).__name__
            logger.error(f"❌ HTTP错误 {self.name}: {type(e).__name__}: {error_msg}")
            import traceback
            logger.error(f"堆栈追踪:\n{traceback.format_exc()}")
            raise RuntimeError(f"HTTP错误: {type(e).__name__}: {error_msg}")
        except Exception as e:
            error_msg = str(e) or repr(e) or type(e).__name__
            logger.error(f"❌ 未知错误 {self.name}: {type(e).__name__}: {error_msg}")
            import traceback
            logger.error(f"堆栈追踪:\n{traceback.format_exc()}")
            raise

    async def _maintain_session(self):
        """维护HTTP MCP会话"""
        try:
            # 创建HTTP客户端
            if self._http_client is None:
                # 不使用环境变量中的代理设置（特别重要：Docker容器可能设置了代理）
                self._http_client = httpx.AsyncClient(
                    timeout=30.0,
                    follow_redirects=True,
                    trust_env=False  # 禁用环境变量代理，避免内网服务走代理
                )
                logger.info(f"📡 创建HTTP客户端连接到 {self.config.url} (禁用代理)")
            
            # 初始化MCP连接
            init_result = await self._send_jsonrpc_request(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": self.name,
                        "version": "1.0.0"
                    }
                }
            )
            
            logger.debug(f"📥 MCP初始化响应 {self.name}: {init_result}")
            
            # 发送initialized通知（可能返回状态或无返回值）
            try:
                await self._send_jsonrpc_request(method="notifications/initialized")
            except Exception as e:
                # 通知可能不需要响应或返回特殊格式，忽略错误
                logger.debug(f"initialized通知响应: {e}")
            
            self._is_initialized = True
            
            # 获取工具列表并缓存
            try:
                tools_result = await self._send_jsonrpc_request(method="tools/list")
                if tools_result and "tools" in tools_result:
                    self._tools_cache = [Tool(**tool) for tool in tools_result["tools"]]
                    logger.info(f"✅ {self.name} 已加载 {len(self._tools_cache)} 个工具")
            except Exception as e:
                logger.warning(f"⚠️ 无法获取工具列表 {self.name}: {e}")
            
            # 设置伪会话对象以满足 AbstractClient 的期望
            # 创建一个包含必要方法的对象
            class PseudoSession:
                async def list_tools(self):
                    return await self.list_tools()

                async def list_resources(self):
                    return await self.list_resources()

                async def list_prompts(self):
                    return await self.list_prompts()

            self.session = PseudoSession()
            self.session.list_tools = lambda: self.list_tools()
            self.session.list_resources = lambda: self.list_resources()
            self.session.list_prompts = lambda: self.list_prompts()
            
            logger.info(f"✅ HTTP MCP连接初始化成功: {self.name}")
            
            # 保持会话活跃
            while True:
                await asyncio.sleep(30)
                # HTTP不需要ping，只要客户端保持活跃即可
                if not self._is_initialized:
                    break
                    
        except Exception as e:
            error_msg = str(e) or repr(e) or type(e).__name__
            logger.error(f"❌ HTTP会话维护失败 {self.name}: {type(e).__name__}: {error_msg}")
            import traceback
            logger.error(f"完整堆栈:\n{traceback.format_exc()}")
            self.session = None
            self._is_initialized = False
        finally:
            # 清理HTTP客户端
            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None
        
        logger.debug(f"退出会话 {self.name}")

    async def call_tool(self, name: str, arguments: dict, timeout: int | None = None) -> CallToolResult:
        """调用工具"""
        await self._wait_for_session()
        
        try:
            async with asyncio.timeout(timeout or 30):
                result = await self._send_jsonrpc_request(
                    method="tools/call",
                    params={
                        "name": name,
                        "arguments": arguments
                    }
                )
                
                # 将结果转换为 CallToolResult
                if isinstance(result, dict) and "content" in result:
                    content = result["content"]
                    if isinstance(content, list):
                        # 处理content列表，避免双重JSON序列化
                        content_items = []
                        for item in content:
                            if isinstance(item, dict):
                                # 如果item包含type和text字段，说明它已经是MCP标准格式
                                # 直接使用text字段的值，不要再次序列化
                                if "type" in item and "text" in item:
                                    content_items.append(TextContent(type=item.get("type", "text"), text=item["text"]))
                                else:
                                    # 不是标准格式，序列化为JSON字符串
                                    content_items.append(TextContent(type="text", text=json.dumps(item, ensure_ascii=False)))
                            else:
                                content_items.append(TextContent(type="text", text=str(item)))
                        
                        return CallToolResult(
                            content=content_items,
                            isError=result.get("isError", False)
                        )
                    return CallToolResult(
                        content=[TextContent(type="text", text=str(content))],
                        isError=result.get("isError", False)
                    )
                
                # 如果不是标准格式，将整个结果作为文本返回
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
                    isError=False
                )
                
        except asyncio.TimeoutError:
            logger.error(f"调用工具超时: {name}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"超时错误调用 {name}")],
                isError=True,
            )
        except Exception as e:
            logger.error(f"调用工具错误 {name}: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"错误调用 {name}: {e}")],
                isError=True,
            )

    async def list_tools(self) -> ListToolsResult:
        """列出所有工具"""
        await self._wait_for_session()
        
        try:
            # 如果有缓存，直接返回
            if self._tools_cache:
                return ListToolsResult(tools=self._tools_cache)
            
            # 否则请求
            result = await self._send_jsonrpc_request(method="tools/list")
            if result and "tools" in result:
                tools = [Tool(**tool) for tool in result["tools"]]
                self._tools_cache = tools
                return ListToolsResult(tools=tools)
            
            return ListToolsResult(tools=[])
        except Exception as e:
            logger.error(f"列出工具错误: {e}")
            return ListToolsResult(tools=[])

    async def list_resources(self) -> ListResourcesResult:
        """列出所有资源"""
        await self._wait_for_session()
        
        try:
            result = await self._send_jsonrpc_request(method="resources/list")
            if result and "resources" in result:
                return ListResourcesResult(resources=result["resources"])
            return ListResourcesResult(resources=[])
        except Exception as e:
            logger.error(f"列出资源错误: {e}")
            return ListResourcesResult(resources=[])

    async def list_prompts(self) -> ListPromptsResult:
        """列出所有提示"""
        await self._wait_for_session()
        
        try:
            result = await self._send_jsonrpc_request(method="prompts/list")
            if result and "prompts" in result:
                return ListPromptsResult(prompts=result["prompts"])
            return ListPromptsResult(prompts=[])
        except Exception as e:
            logger.error(f"列出提示错误: {e}")
            return ListPromptsResult(prompts=[])

