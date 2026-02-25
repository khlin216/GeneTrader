"""
Agent API module for external AI agent integration.

This module provides REST API and WebSocket endpoints for AI agents
to interact with the GeneTrader optimization system.

Features:
- Query live performance metrics
- Get optimization status
- Approve/reject optimization deployments
- Trigger manual optimizations
- Receive real-time alerts

Components:
- AgentAPI: FastAPI-based REST API server
- WebSocketManager: Real-time WebSocket connections
- AuthManager: API key authentication
"""

from agent_api.api_server import AgentAPI, create_app
from agent_api.websocket_manager import WebSocketManager
from agent_api.auth import AuthManager, APIKeyAuth

__all__ = [
    'AgentAPI',
    'create_app',
    'WebSocketManager',
    'AuthManager',
    'APIKeyAuth',
]
