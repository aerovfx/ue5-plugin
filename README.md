# Pixibox UE5 Bridge

A professional Python bridge for seamless integration between **Pixibox.ai** and **Unreal Engine 5**, enabling automated 3D asset import, spawning, and live synchronization.

## Features

- **Remote Control Bridge** — Direct HTTP/WebSocket communication with UE5's Remote Control API (localhost:30010)
- **Auto-Import** — Automatically download and import 3D generations into your UE5 Content Browser
- **Actor Spawning** — Programmatically spawn actors with custom locations, rotations, and materials
- **Live Sync Daemon** — Watch mode that polls Pixibox API and auto-imports new generations based on project rules
- **Multi-Format Support** — GLB, FBX, and USD asset import with automatic material setup
- **Type-Safe Python** — Fully typed with docstrings, async/await support for production workflows

## Requirements

- **Unreal Engine 5.2+** with Remote Control API enabled
- **Python 3.9+**
- **pixibox-cli v2.0+** (for API authentication)
- Network access to UE5 Remote Control endpoint (default: `localhost:30010`)

## Installation

Install via pip:

```bash
pip install pixibox-ue5-bridge
```

Or from source:

```bash
git clone https://github.com/pixibox-ai/ue5-bridge.git
cd ue5-bridge
pip install -e .
```

## Quick Start

### 1. Configure Your Project

```bash
pixibox-ue5-bridge config set --api-url https://api.pixibox.ai \
  --ue5-host localhost \
  --ue5-port 30010
```

### 2. Connect to UE5

```bash
pixibox-ue5-bridge status
# Connected to UE5 at localhost:30010
```

### 3. Import a Generation

```bash
pixibox-ue5-bridge import --generation-id <ID> \
  --format glb \
  --destination /Game/Pixibox/Models
```

### 4. Start Live Sync Daemon

```bash
pixibox-ue5-bridge start --watch --auto-import
```

The daemon will poll Pixibox API every 30 seconds and auto-import new generations based on your project rules.

## Python API Usage

### Basic Asset Import

```python
from pixibox_ue5 import Bridge

# Initialize bridge
bridge = Bridge(api_url="https://api.pixibox.ai")
bridge.connect(host="localhost", port=30010)

# Import a 3D generation
asset_path = bridge.import_asset(
    generation_id="gen_abc123",
    content_path="/Game/Pixibox/Models",
    spawn_actor=True,
    location=(0, 0, 100)
)

print(f"Asset imported at: {asset_path}")
bridge.disconnect()
```

### Spawn Actor with Custom Transform

```python
from pixibox_ue5 import Bridge

bridge = Bridge()
bridge.connect()

actor = bridge.spawn_actor(
    asset_path="/Game/Pixibox/Models/MyModel",
    location=(100, 200, 0),
    rotation=(0, 0, 45)
)

print(f"Actor spawned: {actor}")
bridge.disconnect()
```

### List Available Assets

```python
assets = bridge.list_assets(path="/Game/Pixibox")
for asset in assets:
    print(f"- {asset['name']} ({asset['type']})")
```

### Get Viewport Camera Transform

```python
transform = bridge.get_viewport_transform()
print(f"Camera Location: {transform['location']}")
print(f"Camera Rotation: {transform['rotation']}")
```

## Configuration

Configuration is stored at `~/.pixibox/ue5-bridge.json`:

```json
{
  "api_url": "https://api.pixibox.ai",
  "api_token": "YOUR_PIXIBOX_TOKEN",
  "ue5_host": "localhost",
  "ue5_port": 30010,
  "auto_import": {
    "enabled": true,
    "poll_interval": 30,
    "content_path": "/Game/Pixibox/Models",
    "spawn_actors": true
  }
}
```

## CLI Commands

```bash
# Show current configuration
pixibox-ue5-bridge config show

# Set configuration value
pixibox-ue5-bridge config set --api-token YOUR_TOKEN

# Check connection status
pixibox-ue5-bridge status

# Import a specific generation
pixibox-ue5-bridge import --generation-id ID --format glb

# Start the live sync daemon
pixibox-ue5-bridge start --watch --auto-import --poll-interval 30

# Stop the daemon
pixibox-ue5-bridge stop
```

## Architecture

```
pixibox_ue5/
├── bridge.py              # High-level Bridge class
├── remote_control.py      # Low-level UE5 Remote Control API
├── importer.py            # Asset download & import logic
├── daemon.py              # Live sync watch daemon
├── config.py              # Configuration management
└── cli.py                 # Click-based CLI
```

## How It Works

1. **Bridge Connection**: Establishes HTTP/WebSocket connection to UE5's Remote Control API on `localhost:30010`
2. **Asset Download**: Fetches 3D models from Pixibox API in your preferred format (GLB, FBX, USD)
3. **Content Browser Import**: Uses UE5 Remote Control to import assets into your project
4. **Material Setup**: Automatically configures PBR materials based on generation metadata
5. **Actor Spawning**: Creates actors in the level with specified transforms
6. **Live Sync**: Optional daemon mode watches for new generations and auto-imports them

## Troubleshooting

**Connection Refused?**
- Ensure UE5 is running with Remote Control API enabled
- Check that `localhost:30010` is accessible from your Python environment

**Import Failed?**
- Verify your Pixibox API token is set: `pixibox-ue5-bridge config set --api-token YOUR_TOKEN`
- Check file format is supported (GLB, FBX, USD)

**Daemon Not Syncing?**
- Check logs: `pixibox-ue5-bridge status --logs`
- Verify auto-import is enabled: `pixibox-ue5-bridge config show`

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linting
black pixibox_ue5/ tests/
flake8 pixibox_ue5/ tests/
mypy pixibox_ue5/
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License - Copyright 2026 Pixibox.ai. See [LICENSE](LICENSE) for details.

## Support

- Issues: [GitHub Issues](https://github.com/pixibox-ai/ue5-bridge/issues)
- Docs: [Full Documentation](https://docs.pixibox.ai/ue5-bridge)
- Discord: [Pixibox Community](https://discord.gg/pixibox)
