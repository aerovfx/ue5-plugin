"""High-level Bridge class for Pixibox-UE5 integration."""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .config import Config
from .remote_control import RemoteControlAPI
from .importer import AssetImporter


class Bridge:
    """Main bridge class for Pixibox.ai to Unreal Engine 5 integration.

    Provides high-level API for connecting to UE5, importing assets,
    spawning actors, and managing 3D content.

    Example:
        bridge = Bridge(api_url="https://api.pixibox.ai")
        bridge.connect(host="localhost", port=30010)
        asset_path = bridge.import_asset("gen_abc123", spawn_actor=True)
        bridge.disconnect()
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        config_file: Optional[Path] = None,
    ) -> None:
        """Initialize Pixibox UE5 Bridge.

        Args:
            api_url: Pixibox API URL. If not provided, loads from config
            api_token: Pixibox API token. If not provided, loads from config
            config_file: Path to config file. Defaults to ~/.pixibox/ue5-bridge.json
        """
        self.config = Config(config_file)
        self.api_url = api_url or self.config.get("api_url")
        self.api_token = api_token or self.config.get("api_token")

        self.remote_control: Optional[RemoteControlAPI] = None
        self.importer: Optional[AssetImporter] = None

    def connect(self, host: str = "localhost", port: int = 30010) -> None:
        """Connect to Unreal Engine 5 Remote Control API.

        Args:
            host: UE5 Remote Control host (default: localhost)
            port: UE5 Remote Control port (default: 30010)

        Raises:
            RuntimeError: If connection fails
        """
        self.remote_control = RemoteControlAPI(host, port)
        self.remote_control.connect()

        if not self.remote_control.health_check():
            raise RuntimeError(
                f"Failed to connect to UE5 at {host}:{port}. "
                "Ensure UE5 is running with Remote Control API enabled."
            )

        self.importer = AssetImporter(self.api_url, self.api_token, self.remote_control)

    def disconnect(self) -> None:
        """Disconnect from Unreal Engine 5."""
        if self.remote_control:
            self.remote_control.disconnect()
            self.remote_control = None

    def is_connected(self) -> bool:
        """Check if connected to UE5.

        Returns:
            True if connected, False otherwise
        """
        return self.remote_control is not None and self.remote_control.is_connected()

    def import_asset(
        self,
        generation_id: str,
        content_path: str = "/Game/Pixibox/Models",
        spawn_actor: bool = False,
        location: Optional[Tuple[float, float, float]] = None,
        rotation: Optional[Tuple[float, float, float]] = None,
        format: str = "glb",
    ) -> str:
        """Import a Pixibox generation into UE5.

        Downloads the asset, imports it to the content browser, optionally
        sets up materials, and can spawn an actor in the level.

        Args:
            generation_id: Pixibox generation ID
            content_path: Destination in content browser
            spawn_actor: Whether to spawn an actor in the level
            location: Actor spawn location (x, y, z)
            rotation: Actor spawn rotation (pitch, yaw, roll)
            format: Asset format (glb, fbx, usdz, usd)

        Returns:
            Path to imported asset in content browser

        Raises:
            RuntimeError: If not connected to UE5
            ValueError: If generation_id or format invalid
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to UE5")

        # Import asset
        asset_path = self.importer.import_and_setup(
            generation_id, format=format, destination=content_path
        )

        # Optionally spawn actor
        if spawn_actor:
            location = location or (0, 0, 100)
            rotation = rotation or (0, 0, 0)
            self.spawn_actor(asset_path, location, rotation)

        return asset_path

    def spawn_actor(
        self,
        asset_path: str,
        location: Tuple[float, float, float] = (0, 0, 0),
        rotation: Tuple[float, float, float] = (0, 0, 0),
        scale: Optional[Tuple[float, float, float]] = None,
    ) -> str:
        """Spawn an actor in the UE5 level from an asset.

        Args:
            asset_path: Path to asset in content browser
            location: Spawn location (x, y, z)
            rotation: Spawn rotation (pitch, yaw, roll) in degrees
            scale: Spawn scale (x, y, z). Defaults to (1, 1, 1)

        Returns:
            Path to spawned actor

        Raises:
            RuntimeError: If not connected to UE5
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to UE5")

        scale = scale or (1.0, 1.0, 1.0)

        result = self.remote_control.call_function(
            "/Engine/Core/Engine.Engine_C",
            "SpawnActorFromAsset",
            {
                "AssetPath": asset_path,
                "Location": {"x": location[0], "y": location[1], "z": location[2]},
                "Rotation": {"pitch": rotation[0], "yaw": rotation[1], "roll": rotation[2]},
                "Scale": {"x": scale[0], "y": scale[1], "z": scale[2]},
            },
        )

        return result.get("ActorPath", asset_path)

    def list_assets(self, path: str = "/Game/Pixibox") -> List[Dict[str, Any]]:
        """List all assets in a content browser directory.

        Args:
            path: Content browser path to list

        Returns:
            List of asset dictionaries with name, type, and metadata

        Raises:
            RuntimeError: If not connected to UE5
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to UE5")

        result = self.remote_control.call_function(
            "/Engine/Core/Engine.Engine_C",
            "ListAssets",
            {"Path": path},
        )

        return result.get("Assets", [])

    def get_viewport_transform(self) -> Dict[str, Any]:
        """Get current viewport camera transform.

        Returns:
            Dictionary containing location and rotation of viewport camera

        Raises:
            RuntimeError: If not connected to UE5
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to UE5")

        result = self.remote_control.call_function(
            "/Engine/Core/Engine.Engine_C",
            "GetViewportCameraTransform",
            {},
        )

        return {
            "location": result.get("Location", {}),
            "rotation": result.get("Rotation", {}),
        }

    def set_viewport_transform(
        self,
        location: Optional[Tuple[float, float, float]] = None,
        rotation: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        """Set viewport camera transform.

        Args:
            location: Camera location (x, y, z)
            rotation: Camera rotation (pitch, yaw, roll)

        Raises:
            RuntimeError: If not connected to UE5
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to UE5")

        params: Dict[str, Any] = {}

        if location:
            params["Location"] = {"x": location[0], "y": location[1], "z": location[2]}

        if rotation:
            params["Rotation"] = {"pitch": rotation[0], "yaw": rotation[1], "roll": rotation[2]}

        self.remote_control.call_function(
            "/Engine/Core/Engine.Engine_C",
            "SetViewportCameraTransform",
            params,
        )

    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a console command in UE5.

        Args:
            command: Console command to execute

        Returns:
            Response from UE5

        Raises:
            RuntimeError: If not connected to UE5
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to UE5")

        return self.remote_control.execute_console_command(command)

    def __repr__(self) -> str:
        """String representation of bridge."""
        status = "connected" if self.is_connected() else "disconnected"
        return f"Bridge(api={self.api_url}, ue5={status})"
