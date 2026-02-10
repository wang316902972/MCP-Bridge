"""JSON-RPC 2.0 数据模型"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 请求模型"""
    jsonrpc: str = Field("2.0", description="JSON-RPC版本")
    method: str = Field(..., description="要调用的方法名")
    params: Optional[dict[str, Any]] = Field(None, description="方法参数")
    id: Optional[Any] = Field(None, description="请求标识符（通知类型请求为null）")


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 错误模型"""
    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    data: Optional[Any] = Field(None, description="错误详细数据")


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 响应模型"""
    jsonrpc: str = Field("2.0", description="JSON-RPC版本")
    result: Optional[Any] = Field(None, description="方法执行结果")
    error: Optional[JSONRPCError] = Field(None, description="错误信息")
    id: Any = Field(..., description="请求标识符")
