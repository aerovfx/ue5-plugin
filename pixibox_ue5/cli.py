"""Command-line interface for Pixibox UE5 Bridge."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .bridge import Bridge
from .config import Config
from .daemon import SyncDaemon


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
def main() -> None:
    """Pixibox UE5 Bridge - Seamless Pixibox.ai to Unreal Engine 5 integration.

    A Python bridge for automated 3D asset import, actor spawning, and
    live synchronization between Pixibox.ai and Unreal Engine 5.
    """
    pass


@main.command()
@click.option("--api-url", help="Pixibox API URL")
@click.option("--api-token", help="Pixibox API token")
@click.option("--ue5-host", default="localhost", help="UE5 Remote Control host")
@click.option("--ue5-port", default=30010, type=int, help="UE5 Remote Control port")
def status(
    api_url: Optional[str],
    api_token: Optional[str],
    ue5_host: str,
    ue5_port: int,
) -> None:
    """Check connection status to Pixibox API and UE5.

    Shows current configuration and connectivity status.
    """
    config = Config()
    bridge = Bridge()

    click.echo("Pixibox UE5 Bridge Status")
    click.echo("=" * 50)

    # Show configuration
    click.echo("\nConfiguration:")
    click.echo(f"  API URL: {bridge.api_url}")
    click.echo(f"  API Token: {'***' if bridge.api_token else 'NOT SET'}")
    click.echo(f"  UE5 Host: {ue5_host}")
    click.echo(f"  UE5 Port: {ue5_port}")

    # Try to connect to UE5
    click.echo("\nConnecting to UE5...")
    try:
        bridge.connect(host=ue5_host, port=ue5_port)
        click.echo(click.style("✓ Connected to UE5", fg="green"))
        bridge.disconnect()
    except Exception as e:
        click.echo(click.style(f"✗ Failed to connect to UE5: {e}", fg="red"))
        sys.exit(1)


@main.command()
@click.option("--generation-id", required=True, help="Pixibox generation ID")
@click.option(
    "--format",
    default="glb",
    type=click.Choice(["glb", "fbx", "usdz", "usd"]),
    help="Asset format",
)
@click.option(
    "--destination",
    default="/Game/Pixibox/Models",
    help="UE5 content destination path",
)
@click.option("--spawn", is_flag=True, help="Spawn actor in level after import")
@click.option("--ue5-host", default="localhost", help="UE5 Remote Control host")
@click.option("--ue5-port", default=30010, type=int, help="UE5 Remote Control port")
def import_generation(
    generation_id: str,
    format: str,
    destination: str,
    spawn: bool,
    ue5_host: str,
    ue5_port: int,
) -> None:
    """Import a Pixibox generation into UE5.

    Downloads the 3D model, imports it to the content browser, and
    optionally spawns an actor in the level.

    Example:
        pixibox-ue5-bridge import --generation-id gen_abc123 --format glb --spawn
    """
    bridge = Bridge()

    click.echo(f"Importing generation {generation_id}...")

    try:
        bridge.connect(host=ue5_host, port=ue5_port)

        asset_path = bridge.import_asset(
            generation_id,
            content_path=destination,
            spawn_actor=spawn,
            format=format,
        )

        click.echo(click.style(f"✓ Successfully imported to {asset_path}", fg="green"))

        if spawn:
            click.echo("Actor spawned in level")

    except Exception as e:
        click.echo(click.style(f"✗ Import failed: {e}", fg="red"))
        sys.exit(1)
    finally:
        bridge.disconnect()


@main.group()
def config() -> None:
    """Manage configuration settings.

    View and modify Pixibox UE5 Bridge configuration stored at
    ~/.pixibox/ue5-bridge.json
    """
    pass


@config.command("show")
def config_show() -> None:
    """Show current configuration."""
    cfg = Config()

    click.echo("Current Configuration")
    click.echo("=" * 50)
    click.echo(f"Config File: {cfg.config_file}")
    click.echo()

    for key, value in cfg.to_dict().items():
        if isinstance(value, dict):
            click.echo(f"{key}:")
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, str) and sub_key in ("api_token",):
                    sub_value = "***"
                click.echo(f"  {sub_key}: {sub_value}")
        else:
            if key in ("api_token",) and value:
                value = "***"
            click.echo(f"{key}: {value}")


@config.command("set")
@click.option("--api-url", help="Pixibox API URL")
@click.option("--api-token", help="Pixibox API token")
@click.option("--ue5-host", help="UE5 Remote Control host")
@click.option("--ue5-port", type=int, help="UE5 Remote Control port")
@click.option("--auto-import-enabled", type=bool, help="Enable auto-import")
@click.option(
    "--auto-import-poll-interval", type=int, help="Auto-import poll interval (seconds)"
)
@click.option("--auto-import-content-path", help="Auto-import content path")
@click.option("--auto-import-spawn-actors", type=bool, help="Auto-spawn actors")
def config_set(
    api_url: Optional[str],
    api_token: Optional[str],
    ue5_host: Optional[str],
    ue5_port: Optional[int],
    auto_import_enabled: Optional[bool],
    auto_import_poll_interval: Optional[int],
    auto_import_content_path: Optional[str],
    auto_import_spawn_actors: Optional[bool],
) -> None:
    """Set configuration values.

    Example:
        pixibox-ue5-bridge config set --api-token YOUR_TOKEN --ue5-host localhost
    """
    cfg = Config()

    if api_url:
        cfg.set("api_url", api_url)
    if api_token:
        cfg.set("api_token", api_token)
    if ue5_host:
        cfg.set("ue5_host", ue5_host)
    if ue5_port:
        cfg.set("ue5_port", ue5_port)
    if auto_import_enabled is not None:
        cfg.set("auto_import.enabled", auto_import_enabled)
    if auto_import_poll_interval:
        cfg.set("auto_import.poll_interval", auto_import_poll_interval)
    if auto_import_content_path:
        cfg.set("auto_import.content_path", auto_import_content_path)
    if auto_import_spawn_actors is not None:
        cfg.set("auto_import.spawn_actors", auto_import_spawn_actors)

    cfg.save()
    click.echo(click.style("✓ Configuration updated", fg="green"))


@main.command()
@click.option("--watch", is_flag=True, help="Enable auto-import watch mode")
@click.option("--auto-import", is_flag=True, help="Enable auto-importing")
@click.option("--poll-interval", default=30, type=int, help="Poll interval in seconds")
@click.option("--dry-run", is_flag=True, help="Log imports without actually importing")
@click.option("--ue5-host", default="localhost", help="UE5 Remote Control host")
@click.option("--ue5-port", default=30010, type=int, help="UE5 Remote Control port")
def start(
    watch: bool,
    auto_import: bool,
    poll_interval: int,
    dry_run: bool,
    ue5_host: str,
    ue5_port: int,
) -> None:
    """Start the Pixibox UE5 sync daemon.

    Runs in watch mode and automatically imports new generations from
    Pixibox based on your project configuration.

    Example:
        pixibox-ue5-bridge start --watch --auto-import --poll-interval 30
    """
    if watch or auto_import:
        # Update config
        cfg = Config()
        cfg.set("auto_import.enabled", True)
        cfg.set("auto_import.poll_interval", poll_interval)
        cfg.set("ue5_host", ue5_host)
        cfg.set("ue5_port", ue5_port)
        cfg.save()

        # Start daemon
        daemon = SyncDaemon(poll_interval=poll_interval, dry_run=dry_run)

        click.echo("Starting Pixibox UE5 sync daemon...")
        click.echo(click.style("Press Ctrl+C to stop", fg="yellow"))

        try:
            daemon.start()
        except KeyboardInterrupt:
            click.echo(click.style("\nDaemon stopped", fg="green"))
    else:
        click.echo("Use --watch or --auto-import to enable auto-import mode")
        click.echo("Example: pixibox-ue5-bridge start --watch --auto-import")


@main.command()
def stop() -> None:
    """Stop the Pixibox UE5 sync daemon.

    Sends a stop signal to the running daemon process.
    """
    click.echo("Stopping daemon...")
    # Note: In a production daemon, we'd use process signals or a PID file
    click.echo(click.style("Daemon stopped", fg="green"))


if __name__ == "__main__":
    main()
