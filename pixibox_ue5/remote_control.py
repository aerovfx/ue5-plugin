"""Low-level Unreal Engine 5 Remote Control API wrapper."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Callable
from urllib.parse import urljoin

import aiohttp
import requests
import websockets
from websockets.client import WebSocketClientProtocol


class RemoteControlAPI:
    """Low-level wrapper for UE5 Remote Control API (HTTP/WebSocket).

    Provides methods to call functions, get/set properties, and subscribe to
    events on the UE5 Remote Control API endpoint.

    Typical endpoint: http://localhost:30010/remote/
    """

    def __init__(self, host: str = "localhost", port: int = 30010) -> None:
        """Initialize Remote Control API client.

        Args:
            host: UE5 Remote Control host (default: localhost)
            port: UE5 Remote Control port (default: 30010)
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/remote"
        self.ws_url = f"ws://{host}:{port}/remote/events"
        self._session: Optional[requests.Session] = None
        self._ws_connection: Optional[WebSocketClientProtocol] = None
        self._event_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def connect(self) -> None:
        """Establish connection to Remote Control API.

        Creates HTTP session for REST calls. WebSocket connection is
        established lazily on first event subscription.
        """
        self._session = requests.Session()

    def disconnect(self) -> None:
        """Disconnect from Remote Control API."""
        if self._session:
            self._session.close()
            self._session = None

    def is_connected(self) -> bool:
        """Check if connection is established.

        Returns:
            True if connected, False otherwise
        """
        return self._session is not None

    def call_function(
        self, object_path: str, function_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call a function on a UE5 object.

        Args:
            object_path: Full path to the object (e.g., "/Game/MyActor.MyActor_C")
            function_name: Name of the function to call
            params: Optional dictionary of function parameters

        Returns:
            Response from UE5 containing result

        Raises:
            ConnectionError: If not connected to UE5
            RuntimeError: If API call fails
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Remote Control API")

        endpoint = urljoin(self.base_url, "/object/call")
        payload = {
            "objectPath": object_path,
            "functionName": function_name,
            "parameters": params or {},
        }

        response = self._session.post(endpoint, json=payload)
        response.raise_for_status()

        return response.json()

    def get_property(self, object_path: str, property_name: str) -> Any:
        """Get a property value from a UE5 object.

        Args:
            object_path: Full path to the object
            property_name: Name of the property

        Returns:
            Property value

        Raises:
            ConnectionError: If not connected to UE5
            RuntimeError: If API call fails
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Remote Control API")

        endpoint = urljoin(self.base_url, "/object/property")
        params = {"objectPath": object_path, "propertyName": property_name}

        response = self._session.get(endpoint, params=params)
        response.raise_for_status()

        result = response.json()
        return result.get("value")

    def set_property(self, object_path: str, property_name: str, value: Any) -> Dict[str, Any]:
        """Set a property value on a UE5 object.

        Args:
            object_path: Full path to the object
            property_name: Name of the property
            value: Value to set

        Returns:
            Response from UE5

        Raises:
            ConnectionError: If not connected to UE5
            RuntimeError: If API call fails
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Remote Control API")

        endpoint = urljoin(self.base_url, "/object/property")
        payload = {"objectPath": object_path, "propertyName": property_name, "value": value}

        response = self._session.put(endpoint, json=payload)
        response.raise_for_status()

        return response.json()

    def execute_console_command(self, command: str) -> Dict[str, Any]:
        """Execute a console command in UE5.

        Args:
            command: Console command to execute

        Returns:
            Response from UE5

        Raises:
            ConnectionError: If not connected to UE5
            RuntimeError: If API call fails
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Remote Control API")

        endpoint = urljoin(self.base_url, "/execute/command")
        payload = {"command": command}

        response = self._session.post(endpoint, json=payload)
        response.raise_for_status()

        return response.json()

    def subscribe_event(
        self, event_name: str, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribe to a Remote Control event.

        Args:
            event_name: Name of the event to subscribe to
            callback: Callback function to call when event is received
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []

        self._event_handlers[event_name].append(callback)

    def unsubscribe_event(
        self, event_name: str, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Unsubscribe from a Remote Control event.

        Args:
            event_name: Name of the event
            callback: Callback function to remove
        """
        if event_name in self._event_handlers:
            self._event_handlers[event_name] = [
                h for h in self._event_handlers[event_name] if h != callback
            ]

    async def listen_events(self) -> None:
        """Listen for Remote Control events (async).

        This should be run in an event loop. Connects to WebSocket and
        dispatches events to registered handlers.
        """
        try:
            async with websockets.connect(self.ws_url) as websocket:
                self._ws_connection = websocket
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        event_name = data.get("type", "")

                        if event_name in self._event_handlers:
                            for handler in self._event_handlers[event_name]:
                                handler(data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"WebSocket error: {e}")

    def start_event_loop(self) -> None:
        """Start listening for events in a background thread (blocking)."""
        try:
            asyncio.run(self.listen_events())
        except Exception as e:
            print(f"Event loop error: {e}")

    def health_check(self) -> bool:
        """Check if Remote Control API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            endpoint = urljoin(self.base_url, "/")
            response = self._session.get(endpoint, timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def __repr__(self) -> str:
        """String representation of Remote Control API."""
        status = "connected" if self.is_connected() else "disconnected"
        return f"RemoteControlAPI({self.host}:{self.port}, {status})"
