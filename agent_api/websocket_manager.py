"""
WebSocket manager for real-time updates to agents.

Provides real-time streaming of performance metrics, alerts,
and optimization status to connected AI agents.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from utils.logging_config import logger


class MessageType(Enum):
    """Types of WebSocket messages."""
    METRICS_UPDATE = "metrics_update"
    ALERT = "alert"
    OPTIMIZATION_STATUS = "optimization_status"
    DEPLOYMENT_STATUS = "deployment_status"
    TRADE = "trade"
    APPROVAL_REQUEST = "approval_request"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message."""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_name: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'strategy_name': self.strategy_name,
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(
            type=MessageType(data['type']),
            data=data['data'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            strategy_name=data.get('strategy_name'),
        )


class WebSocketConnection:
    """Represents a single WebSocket connection."""

    def __init__(
        self,
        connection_id: str,
        api_key_id: str,
        send_func: Callable[[str], None],
        subscriptions: Optional[Set[str]] = None
    ):
        """
        Initialize connection.

        Args:
            connection_id: Unique connection ID
            api_key_id: API key used for authentication
            send_func: Function to send messages
            subscriptions: Set of subscribed topics
        """
        self.connection_id = connection_id
        self.api_key_id = api_key_id
        self.send_func = send_func
        self.subscriptions = subscriptions or set()
        self.connected_at = datetime.now()
        self.last_message_at = datetime.now()

    async def send(self, message: WebSocketMessage) -> bool:
        """Send a message to this connection."""
        try:
            await self.send_func(message.to_json())
            self.last_message_at = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error sending to {self.connection_id}: {e}")
            return False


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - Multiple concurrent connections
    - Topic-based subscriptions
    - Broadcast and targeted messaging
    - Heartbeat monitoring
    - Connection cleanup

    Topics:
    - metrics:{strategy_name} - Performance metrics updates
    - alerts:{strategy_name} - Alert notifications
    - optimization:{strategy_name} - Optimization status
    - deployment:{strategy_name} - Deployment status
    - all - All messages

    Usage:
        manager = WebSocketManager()

        # Add connection
        manager.add_connection(conn_id, api_key_id, send_func)

        # Subscribe to topics
        manager.subscribe(conn_id, "metrics:MyStrategy")

        # Broadcast message
        await manager.broadcast(message)
    """

    def __init__(self, heartbeat_interval: int = 30):
        """
        Initialize WebSocket manager.

        Args:
            heartbeat_interval: Seconds between heartbeats
        """
        self.heartbeat_interval = heartbeat_interval
        self._connections: Dict[str, WebSocketConnection] = {}
        self._topic_subscribers: Dict[str, Set[str]] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None

    def add_connection(
        self,
        connection_id: str,
        api_key_id: str,
        send_func: Callable[[str], None],
        subscriptions: Optional[Set[str]] = None
    ) -> WebSocketConnection:
        """
        Add a new WebSocket connection.

        Args:
            connection_id: Unique connection ID
            api_key_id: API key used for authentication
            send_func: Async function to send messages
            subscriptions: Initial subscriptions

        Returns:
            WebSocketConnection object
        """
        conn = WebSocketConnection(
            connection_id=connection_id,
            api_key_id=api_key_id,
            send_func=send_func,
            subscriptions=subscriptions or set()
        )

        self._connections[connection_id] = conn

        # Add to topic subscribers
        for topic in conn.subscriptions:
            if topic not in self._topic_subscribers:
                self._topic_subscribers[topic] = set()
            self._topic_subscribers[topic].add(connection_id)

        logger.info(f"WebSocket connected: {connection_id}")
        return conn

    def remove_connection(self, connection_id: str) -> bool:
        """
        Remove a WebSocket connection.

        Args:
            connection_id: Connection to remove

        Returns:
            True if removed
        """
        if connection_id not in self._connections:
            return False

        conn = self._connections[connection_id]

        # Remove from topic subscribers
        for topic in conn.subscriptions:
            if topic in self._topic_subscribers:
                self._topic_subscribers[topic].discard(connection_id)

        del self._connections[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")
        return True

    def subscribe(self, connection_id: str, topic: str) -> bool:
        """
        Subscribe a connection to a topic.

        Args:
            connection_id: Connection ID
            topic: Topic to subscribe to

        Returns:
            True if subscribed
        """
        if connection_id not in self._connections:
            return False

        self._connections[connection_id].subscriptions.add(topic)

        if topic not in self._topic_subscribers:
            self._topic_subscribers[topic] = set()
        self._topic_subscribers[topic].add(connection_id)

        return True

    def unsubscribe(self, connection_id: str, topic: str) -> bool:
        """
        Unsubscribe a connection from a topic.

        Args:
            connection_id: Connection ID
            topic: Topic to unsubscribe from

        Returns:
            True if unsubscribed
        """
        if connection_id not in self._connections:
            return False

        self._connections[connection_id].subscriptions.discard(topic)

        if topic in self._topic_subscribers:
            self._topic_subscribers[topic].discard(connection_id)

        return True

    async def send_to_connection(
        self,
        connection_id: str,
        message: WebSocketMessage
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection
            message: Message to send

        Returns:
            True if sent successfully
        """
        if connection_id not in self._connections:
            return False

        return await self._connections[connection_id].send(message)

    async def broadcast(
        self,
        message: WebSocketMessage,
        topic: Optional[str] = None
    ) -> int:
        """
        Broadcast a message to all connections or topic subscribers.

        Args:
            message: Message to broadcast
            topic: Optional topic to filter by

        Returns:
            Number of connections message was sent to
        """
        sent_count = 0

        if topic:
            # Send to topic subscribers
            subscriber_ids = self._topic_subscribers.get(topic, set())
        else:
            # Send to all connections
            subscriber_ids = set(self._connections.keys())

        # Also send to 'all' subscribers
        subscriber_ids |= self._topic_subscribers.get('all', set())

        for conn_id in subscriber_ids:
            if conn_id in self._connections:
                if await self._connections[conn_id].send(message):
                    sent_count += 1

        return sent_count

    async def send_metrics_update(
        self,
        strategy_name: str,
        metrics: Dict[str, Any]
    ) -> int:
        """Send a metrics update to subscribers."""
        message = WebSocketMessage(
            type=MessageType.METRICS_UPDATE,
            data=metrics,
            strategy_name=strategy_name,
        )
        return await self.broadcast(message, f"metrics:{strategy_name}")

    async def send_alert(
        self,
        strategy_name: str,
        alert: Dict[str, Any]
    ) -> int:
        """Send an alert to subscribers."""
        message = WebSocketMessage(
            type=MessageType.ALERT,
            data=alert,
            strategy_name=strategy_name,
        )
        return await self.broadcast(message, f"alerts:{strategy_name}")

    async def send_optimization_status(
        self,
        strategy_name: str,
        status: Dict[str, Any]
    ) -> int:
        """Send optimization status update."""
        message = WebSocketMessage(
            type=MessageType.OPTIMIZATION_STATUS,
            data=status,
            strategy_name=strategy_name,
        )
        return await self.broadcast(message, f"optimization:{strategy_name}")

    async def request_approval(
        self,
        strategy_name: str,
        version_id: str,
        metrics: Dict[str, Any]
    ) -> int:
        """Send approval request to connected agents."""
        message = WebSocketMessage(
            type=MessageType.APPROVAL_REQUEST,
            data={
                'version_id': version_id,
                'metrics': metrics,
                'requires_response': True,
            },
            strategy_name=strategy_name,
        )
        return await self.broadcast(message, f"optimization:{strategy_name}")

    async def start_heartbeat(self) -> None:
        """Start the heartbeat task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        """Stop the heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                message = WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    data={'connections': len(self._connections)},
                )

                dead_connections = []

                for conn_id, conn in self._connections.items():
                    if not await conn.send(message):
                        dead_connections.append(conn_id)

                # Clean up dead connections
                for conn_id in dead_connections:
                    self.remove_connection(conn_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)

    def get_connections_info(self) -> List[Dict[str, Any]]:
        """Get information about all connections."""
        return [
            {
                'connection_id': conn.connection_id,
                'api_key_id': conn.api_key_id,
                'subscriptions': list(conn.subscriptions),
                'connected_at': conn.connected_at.isoformat(),
                'last_message_at': conn.last_message_at.isoformat(),
            }
            for conn in self._connections.values()
        ]
