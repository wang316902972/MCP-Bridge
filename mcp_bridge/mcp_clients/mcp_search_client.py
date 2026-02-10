#!/usr/bin/env python3
"""
MCP搜索客户端 - HTTP REST API封装
将HTTP REST API封装为MCP兼容接口
连接到 http://192.168.244.189:8003/ 的向量搜索服务
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger(__name__)


class MCPSearchClient:
    """MCP搜索客户端 - 通过HTTP REST API与知识库服务通信"""

    def __init__(self,
                 search_url: str = "http://192.168.244.189:8003/",
                 client_name: str = "mcp-search-client",
                 client_version: str = "1.0.0"):
        """
        初始化MCP搜索客户端

        Args:
            search_url: 搜索服务地址（REST API）
            client_name: 客户端名称
            client_version: 客户端版本
        """
        # 处理URL - 支持 MCP 协议和 REST API 两种模式
        url = search_url.rstrip('/')

        # 判断是否为 MCP 协议地址（包含 /mcp）或 REST API 地址
        if url.endswith('/mcp'):
            # MCP 协议模式：直接使用该 URL
            self.mcp_url = url
            self.search_endpoint = url  # MCP 端点
      
        self.search_url = search_url  # 保存原始 URL
        self.client_name = client_name
        self.client_version = client_version
        self.is_initialized = False
        self._http_client: Optional[httpx.AsyncClient] = None
        self._request_id = 0  # 初始化请求ID
        self._session_id: Optional[str] = None  # 会话ID

        logger.info(f"✅ 创建MCP搜索客户端（REST API）: {self.search_endpoint}")

    def _get_next_id(self) -> int:
        """获取下一个请求ID"""
        self._request_id += 1
        return self._request_id

    async def _send_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送JSON-RPC 2.0请求

        Args:
            method: 方法名
            params: 参数

        Returns:
            Dict[str, Any]: 响应结果
        """
        if not self._http_client:
            raise RuntimeError("HTTP客户端未初始化，请先调用 initialize_async()")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._get_next_id()
        }
        
        if params:
            request_data["params"] = params
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        
        try:
            logger.debug(f"📡 发送MCP请求: {method}")
            # self.mcp_url 已经指向 MCP 端点，直接使用
            response = await self._http_client.post(
                self.mcp_url,
                json=request_data,
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"❌ MCP请求失败: {response.status_code} - {response.text}")
                raise RuntimeError(f"MCP请求失败: {response.status_code}")

            result = response.json()
            logger.debug(f"📥 MCP响应: {result}")

            # 检查是否有错误（MCP 标准格式：error 字段存在且不为 null 表示有错误）
            if result.get("error") is not None:
                error = result["error"]
                error_msg = error.get('message', str(error)) if isinstance(error, dict) else str(error)
                logger.error(f"❌ MCP错误: {error_msg}")
                logger.debug(f"完整错误对象: {error}")
                raise RuntimeError(f"MCP错误: {error_msg}")

            # 返回结果（MCP 标准格式）
            if "result" in result:
                return result["result"]
            # 如果没有 result 字段，直接返回整个响应
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP错误: {e}")
            raise RuntimeError(f"HTTP错误: {e}")

    async def initialize_async(self) -> bool:
        """
        异步初始化MCP连接

        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.debug("🔌 开始初始化MCP连接...")
            
            # 创建HTTP客户端
            if not self._http_client:
                self._http_client = httpx.AsyncClient(
                    timeout=30.0,
                    follow_redirects=True
                )
            
            # 发送MCP initialize请求
            init_result = await self._send_jsonrpc_request(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": self.client_name,
                        "version": self.client_version
                    }
                }
            )
            
            logger.debug(f"📥 MCP初始化响应: {init_result}")
            
            # 发送initialized通知
            await self._send_jsonrpc_request(method="notifications/initialized")
            
            self.is_initialized = True
            logger.info(f"✅ MCP连接初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ MCP初始化失败: {e}")
            self.is_initialized = False
            return False
    
    def initialize(self) -> bool:
        """
        同步初始化MCP连接

        Returns:
            bool: 初始化是否成功
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已运行，创建新任务
                future = asyncio.ensure_future(self.initialize_async())
                return True  # 异步返回，实际初始化在后台进行
            else:
                # 如果没有运行的事件循环，同步执行
                return loop.run_until_complete(self.initialize_async())
        except Exception as e:
            logger.error(f"❌ 同步初始化失败: {e}")
            return False

    async def search_async(
        self,
        question: str,
        top_k: int = 5,
        use_optimization: bool = True
    ) -> str:
        """
        异步搜索知识库（使用MCP tools/call）

        Args:
            question: 查询问题
            top_k: 返回结果数量
            use_optimization: 是否使用优化

        Returns:
            str: 搜索结果（JSON字符串）
        """
        try:
            if not self.is_initialized:
                await self.initialize_async()
            
            # 调用MCP工具：search_knowledge
            result = await self._send_jsonrpc_request(
                method="tools/call",
                params={
                    "name": "search_knowledge",
                    "arguments": {
                        "query": question,
                        "top_k": top_k,
                        "use_optimization": use_optimization
                    }
                }
            )
            
            # 处理MCP响应格式
            if isinstance(result, dict) and "content" in result:
                # 标准MCP响应格式
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # 提取第一个内容项的文本
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        return first_content["text"]
                    elif isinstance(first_content, str):
                        return first_content
                return json.dumps(content, ensure_ascii=False)
            
            # 直接返回结果
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"❌ MCP搜索异常: {e}")
            return json.dumps({
                "error": "搜索异常",
                "detail": str(e),
                "results": []
            }, ensure_ascii=False)

    def search(
        self,
        question: str,
        top_k: int = 5,
        use_optimization: bool = True
    ) -> str:
        """
        同步搜索知识库

        Args:
            question: 查询问题
            top_k: 返回结果数量
            use_optimization: 是否使用优化

        Returns:
            str: 搜索结果（JSON字符串）
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在运行的事件循环中，创建任务
                future = asyncio.ensure_future(
                    self.search_async(question, top_k, use_optimization)
                )
                # 注意：这里返回的是Future，调用者需要await
                # 为了兼容，我们尝试等待完成
                return json.dumps({
                    "status": "async_pending",
                    "message": "请使用异步接口 search_async"
                }, ensure_ascii=False)
            else:
                return loop.run_until_complete(
                    self.search_async(question, top_k, use_optimization)
                )
        except Exception as e:
            logger.error(f"❌ 同步搜索异常: {e}")
            return json.dumps({
                "error": "搜索异常",
                "detail": str(e),
                "results": []
            }, ensure_ascii=False)

    async def close_async(self):
        """关闭异步会话"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("✅ HTTP客户端已关闭")

    def close(self):
        """关闭同步会话"""
        if self._http_client:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.close_async())
                else:
                    loop.run_until_complete(self.close_async())
            except Exception as e:
                logger.error(f"关闭客户端失败: {e}")


# 兼容旧接口
MCPClient = MCPSearchClient


def create_mcp_search_client(
    search_url: str = "http://192.168.244.189:8003/",
    client_name: str = "mcp-search-client",
    client_version: str = "1.0.0"
) -> MCPSearchClient:
    """
    创建MCP搜索客户端

    Args:
        search_url: 搜索服务地址（MCP协议）
        client_name: 客户端名称
        client_version: 客户端版本

    Returns:
        MCPSearchClient: 搜索客户端实例
    """
    return MCPSearchClient(
        search_url=search_url,
        client_name=client_name,
        client_version=client_version
    )


if __name__ == "__main__":
    # 测试客户端
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试异步调用
    async def test_async():
        print("\n=== 测试MCP标准协议搜索 ===")
        client = create_mcp_search_client()
        
        try:
            # 初始化
            await client.initialize_async()
            
            # 搜索
            result = await client.search_async("什么是数据仓库", top_k=3)
            print(f"搜索结果: {result[:500]}...")
            
        finally:
            await client.close_async()

    asyncio.run(test_async())
