"""Live Bridge support for Socket.IO v4 real-time generation updates."""

import json
import logging
import threading
import time
from queue import Queue, Empty
from typing import Any, Callable, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
import websockets
import websockets.client

logger = logging.getLogger(__name__)


class LiveBridge:
    """Socket.IO v4 bridge for real-time Pixibox generation updates.

    Connects to the /bridge namespace using Socket.IO protocol over raw WebSocket.
    Handles dcc_push events and queues them for processing.

    Example:
        bridge = LiveBridge(api_url="https://api.pixibox.ai", api_token="token")
        bridge.connect()
        bridge.start_listener()

        # Wait for dcc_push events
        event = bridge.get_event(timeout=5)
        if event:
            generation_id = event["generation_id"]
    """

    def __init__(self, api_url: str, api_token: str) -> None:
        """Initialize Live Bridge client.

        Args:
            api_url: Pixibox API base URL (e.g., https://api.pixibox.ai)
            api_token: API authentication token
        """
        self.api_url = api_url
        self.api_token = api_token
        self._ws_url = self._build_ws_url()
        self._ws_connection: Optional[websockets.WebSocketClientProtocol] = None
        self._event_queue: Queue[Dict[str, Any]] = Queue()
        self._listener_thread: Optional[threading.Thread] = None
        self._running = False

    def _build_ws_url(self) -> str:
        """Build WebSocket URL from API URL."""
        parsed = urlparse(self.api_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        netloc = parsed.netloc
        return f"{scheme}://{netloc}/socket.io/?EIO=4&transport=websocket"

    def connect(self) -> None:
        """Establish WebSocket connection and perform Socket.IO handshake.

        Raises:
            RuntimeError: If connection fails
        """
        try:
            logger.info(f"Connecting to Live Bridge at {self._ws_url}")
            self._ws_connection = websockets.connect(self._ws_url)
            logger.info("Live Bridge connected")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Live Bridge: {e}")

    def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._ws_connection:
            self._running = False
            if self._listener_thread:
                self._listener_thread.join(timeout=2)
            self._ws_connection = None
            logger.info("Live Bridge disconnected")

    def start_listener(self) -> None:
        """Start listening for events in background thread."""
        if self._listener_thread and self._listener_thread.is_alive():
            logger.warning("Listener already running")
            return

        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        logger.info("Live Bridge listener started")

    def stop_listener(self) -> None:
        """Stop the listener thread."""
        self._running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=5)

    def get_event(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get the next event from the queue.

        Args:
            timeout: Seconds to wait for an event (None = wait forever)

        Returns:
            Event dictionary or None if timeout
        """
        try:
            return self._event_queue.get(timeout=timeout)
        except Empty:
            return None

    async def _async_listen(self) -> None:
        """Async listener for WebSocket messages."""
        try:
            async with await websockets.connect(self._ws_url) as ws:
                self._ws_connection = ws

                # Send Socket.IO connection message: 40/bridge,{"token":"api_key"}
                auth_payload = json.dumps({"token": self.api_token})
                await ws.send(f"40/bridge,{auth_payload}")
                logger.info("Socket.IO auth sent")

                # Listen for messages
                async for message in ws:
                    if not self._running:
                        break

                    try:
                        # Parse Socket.IO message format: 42/bridge,[event_name, data]
                        if message.startswith("42/bridge,"):
                            payload = message[10:]  # Remove "42/bridge," prefix
                            data = json.loads(payload)

                            if isinstance(data, list) and len(data) >= 2:
                                event_name = data[0]
                                event_data = data[1] if isinstance(data[1], dict) else {}

                                if event_name == "dcc_push":
                                    logger.debug(f"Received dcc_push event: {event_data}")
                                    self._event_queue.put(event_data)

                    except (json.JSONDecodeError, IndexError) as e:
                        logger.debug(f"Failed to parse message: {e}")

        except Exception as e:
            if self._running:
                logger.error(f"WebSocket error: {e}")

    def _listen_loop(self) -> None:
        """Blocking listener loop that runs in background thread."""
        try:
            import asyncio

            # For threading, we need to create a new event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(self._async_listen())
        except Exception as e:
            logger.error(f"Listener loop error: {e}")

    def __repr__(self) -> str:
        """String representation of Live Bridge."""
        status = "connected" if self._ws_connection else "disconnected"
        return f"LiveBridge(api={self.api_url}, status={status})"
