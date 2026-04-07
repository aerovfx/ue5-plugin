"""Asset import logic for downloading and importing 3D models into UE5."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urljoin

import requests

from .remote_control import RemoteControlAPI


class AssetImporter:
    """Handles downloading and importing 3D assets from Pixibox API.

    Supports multiple formats (GLB, FBX, USD) with automatic material setup
    and content browser organization.
    """

    SUPPORTED_FORMATS = ("glb", "fbx", "usdz", "usd")

    def __init__(
        self, api_url: str, api_token: str, remote_control: RemoteControlAPI
    ) -> None:
        """Initialize asset importer.

        Args:
            api_url: Pixibox API base URL
            api_token: Pixibox API authentication token
            remote_control: Connected RemoteControlAPI instance
        """
        self.api_url = api_url
        self.api_token = api_token
        self.remote_control = remote_control
        self._headers = {"Authorization": f"Bearer {api_token}"}

    def download_generation(
        self, generation_id: str, format: str = "glb", output_dir: Optional[Path] = None
    ) -> Path:
        """Download a 3D generation from Pixibox API.

        Args:
            generation_id: Pixibox generation ID
            format: Output format (glb, fbx, usdz, usd)
            output_dir: Directory to save file. Defaults to system temp

        Returns:
            Path to downloaded file

        Raises:
            ValueError: If format is not supported
            RuntimeError: If download fails
        """
        if format.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}. Supported: {self.SUPPORTED_FORMATS}")

        if output_dir is None:
            output_dir = Path(tempfile.gettempdir())

        output_dir.mkdir(parents=True, exist_ok=True)

        # First, get generation details to retrieve modelUrl
        gen_url = urljoin(self.api_url, f"/api/v1/generations/{generation_id}")
        gen_response = requests.get(gen_url, headers=self._headers, timeout=10)
        gen_response.raise_for_status()

        gen_data = gen_response.json()
        model_url = gen_data.get("modelUrl")

        if not model_url:
            raise RuntimeError(f"No modelUrl in generation {generation_id}")

        # Download from model URL (GCS signed URL, no auth needed)
        response = requests.get(model_url, stream=True, timeout=30)
        response.raise_for_status()

        # Save to file
        filename = f"{generation_id}.{format.lower()}"
        file_path = output_dir / filename

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return file_path

    def import_to_content_browser(
        self, file_path: Path, destination: str = "/Game/Pixibox/Models"
    ) -> str:
        """Import asset file into UE5 Content Browser.

        Args:
            file_path: Path to asset file
            destination: UE5 content path (e.g., "/Game/Pixibox/Models")

        Returns:
            Asset path in UE5 content browser

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If import fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Asset file not found: {file_path}")

        # Ensure destination ends without trailing slash
        destination = destination.rstrip("/")

        # Call UE5 import function
        result = self.remote_control.call_function(
            "/Engine/Core/Engine.Engine_C",
            "ImportAsset",
            {
                "FilePath": str(file_path),
                "DestinationPath": destination,
            },
        )

        # Extract imported asset path from result
        asset_path = result.get("AssetPath", f"{destination}/{file_path.stem}")

        return asset_path

    def setup_materials(self, asset_path: str) -> None:
        """Configure PBR materials for imported asset.

        Sets up material properties based on generation metadata:
        - Enables PBR workflow
        - Sets metallic, roughness, normal maps if available

        Args:
            asset_path: Path to imported asset in content browser
        """
        # Get asset metadata
        metadata = self._get_asset_metadata(asset_path)

        if metadata:
            # Apply material settings based on metadata
            material_settings = metadata.get("material", {})

            if material_settings:
                self.remote_control.call_function(
                    asset_path,
                    "SetMaterialSettings",
                    {
                        "Metallic": material_settings.get("metallic", 0.5),
                        "Roughness": material_settings.get("roughness", 0.5),
                        "UseNormalMap": material_settings.get("useNormalMap", True),
                    },
                )

    def _get_asset_metadata(self, asset_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata for an asset.

        Args:
            asset_path: Path to asset in content browser

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            result = self.remote_control.call_function(
                asset_path,
                "GetMetadata",
                {},
            )
            return result.get("Metadata", {})
        except Exception:
            return None

    def import_and_setup(
        self,
        generation_id: str,
        format: str = "glb",
        destination: str = "/Game/Pixibox/Models",
        setup_materials: bool = True,
    ) -> str:
        """Complete import workflow: download, import, and setup materials.

        Args:
            generation_id: Pixibox generation ID
            format: Output format (glb, fbx, usdz, usd)
            destination: UE5 content destination path
            setup_materials: Whether to configure materials

        Returns:
            Imported asset path in content browser

        Raises:
            ValueError: If format unsupported
            RuntimeError: If any step fails
        """
        # Download
        file_path = self.download_generation(generation_id, format)

        try:
            # Import to content browser
            asset_path = self.import_to_content_browser(file_path, destination)

            # Setup materials
            if setup_materials:
                self.setup_materials(asset_path)

            return asset_path
        finally:
            # Cleanup temp file
            if file_path.exists():
                file_path.unlink()

    def __repr__(self) -> str:
        """String representation of asset importer."""
        return f"AssetImporter(api={self.api_url})"
