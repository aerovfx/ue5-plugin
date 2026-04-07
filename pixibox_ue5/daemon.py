"""Live sync daemon for watching Pixibox generations and auto-importing to UE5."""

import time
import logging
from typing import Optional, Set
from pathlib import Path

import requests

from .bridge import Bridge
from .config import Config
from .live_bridge import LiveBridge


logger = logging.getLogger(__name__)


class SyncDaemon:
    """Live sync daemon that watches for new generations and auto-imports them.

    Polls the Pixibox API at regular intervals and automatically imports
    new generations based on project configuration rules.
    """

    def __init__(
        self,
        config_file: Optional[Path] = None,
        poll_interval: int = 30,
        dry_run: bool = False,
    ) -> None:
        """Initialize sync daemon.

        Args:
            config_file: Path to config file
            poll_interval: Seconds between API polls (default: 30)
            dry_run: If True, log imports without actually importing
        """
        self.config = Config(config_file)
        self.bridge = Bridge(config_file=config_file)
        self.poll_interval = poll_interval
        self.dry_run = dry_run
        self._running = False
        self._last_sync_time = 0
        self._imported_ids: Set[str] = set()
        self._live_bridge: Optional[LiveBridge] = None

    def start(self) -> None:
        """Start the sync daemon (blocking).

        Connects to UE5 and uses Live Bridge for real-time updates.
        Falls back to polling if Live Bridge unavailable.
        Press Ctrl+C to stop.
        """
        logger.info("Starting Pixibox UE5 sync daemon...")

        try:
            # Connect to UE5
            ue5_host = self.config.get("ue5_host", "localhost")
            ue5_port = self.config.get("ue5_port", 30010)

            logger.info(f"Connecting to UE5 at {ue5_host}:{ue5_port}...")
            self.bridge.connect(host=ue5_host, port=ue5_port)
            logger.info("Connected to UE5")

            self._running = True

            # Try to start Live Bridge
            self._try_start_live_bridge()

            # Main loop
            while self._running:
                try:
                    # Check for Live Bridge events
                    if self._live_bridge:
                        self._check_live_bridge_events()
                    else:
                        # Fallback to polling
                        self._sync()

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Sync error: {e}")

                time.sleep(self.poll_interval if not self._live_bridge else 1)

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the sync daemon."""
        self._running = False
        if self._live_bridge:
            self._live_bridge.stop_listener()
            self._live_bridge.disconnect()
        self.bridge.disconnect()
        logger.info("Sync daemon stopped")

    def _try_start_live_bridge(self) -> None:
        """Try to start Live Bridge connection.

        Silently fails and falls back to polling if unavailable.
        """
        try:
            api_url = self.config.get("api_url")
            api_token = self.config.get("api_token")

            if not api_url or not api_token:
                logger.warning("Live Bridge: api_url or api_token not configured")
                return

            self._live_bridge = LiveBridge(api_url, api_token)
            self._live_bridge.connect()
            self._live_bridge.start_listener()
            logger.info("Live Bridge connected and listening")

        except Exception as e:
            logger.warning(f"Live Bridge unavailable, falling back to polling: {e}")
            self._live_bridge = None

    def _check_live_bridge_events(self) -> None:
        """Check for events from Live Bridge queue.

        Processes dcc_push events without blocking.
        """
        if not self._live_bridge:
            return

        auto_import_config = self.config.get("auto_import", {})
        if not auto_import_config.get("enabled", False):
            return

        content_path = auto_import_config.get("content_path", "/Game/Pixibox/Models")
        spawn_actors = auto_import_config.get("spawn_actors", False)

        # Non-blocking check for events
        event = self._live_bridge.get_event(timeout=0.1)
        if event:
            generation_id = event.get("generation_id")

            # Avoid duplicate imports
            if generation_id and generation_id not in self._imported_ids:
                self._imported_ids.add(generation_id)
                self._import_generation(
                    generation_id, content_path, spawn_actors, auto_import_config
                )

    def _sync(self) -> None:
        """Perform one sync cycle (polling fallback).

        Fetches completed generations from Pixibox API and imports those
        that haven't been imported yet.
        """
        auto_import_config = self.config.get("auto_import", {})

        if not auto_import_config.get("enabled", False):
            return

        api_url = self.config.get("api_url")
        api_token = self.config.get("api_token")
        content_path = auto_import_config.get("content_path", "/Game/Pixibox/Models")
        spawn_actors = auto_import_config.get("spawn_actors", False)

        # Fetch completed generations from Pixibox API
        try:
            headers = {"Authorization": f"Bearer {api_token}"}
            url = f"{api_url}/api/v1/generations?limit=10&offset=0&status=completed"
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()

            generations = response.json().get("generations", [])

            for gen in generations:
                generation_id = gen.get("id")

                # Only import if not already imported
                if generation_id and generation_id not in self._imported_ids:
                    self._imported_ids.add(generation_id)
                    self._import_generation(
                        generation_id, content_path, spawn_actors, auto_import_config
                    )

        except Exception as e:
            logger.error(f"Failed to fetch generations: {e}")

    def _import_generation(
        self,
        generation_id: str,
        content_path: str,
        spawn_actors: bool,
        config: dict,
    ) -> None:
        """Import a single generation.

        Args:
            generation_id: Pixibox generation ID
            content_path: Destination content path
            spawn_actors: Whether to spawn actors
            config: Auto-import configuration
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would import generation {generation_id}")
            return

        try:
            logger.info(f"Importing generation {generation_id}...")

            asset_path = self.bridge.import_asset(
                generation_id,
                content_path=content_path,
                spawn_actor=spawn_actors,
                format=config.get("format", "glb"),
            )

            logger.info(f"Successfully imported to {asset_path}")

        except Exception as e:
            logger.error(f"Failed to import generation {generation_id}: {e}")

    def __repr__(self) -> str:
        """String representation of sync daemon."""
        return f"SyncDaemon(poll_interval={self.poll_interval}, running={self._running})"
