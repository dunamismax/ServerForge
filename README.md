# svforge-mc

A modern Python CLI tool for installing and managing Minecraft servers on macOS and Linux.

## Features

- **Multiple Server Types**: Vanilla, Paper, Spigot, Forge, and Leaf servers
- **Version Management**: Support for Minecraft versions 1.7.x through 1.21.x
- **Automatic Java Management**: Detects and installs required Java versions
- **Cross-Platform**: Works on macOS and Linux
- **Fast Downloads**: Asynchronous downloads with progress tracking
- **Smart Caching**: Speeds up repeated installations (Spigot servers)
- **Rich CLI**: Clean terminal output with progress bars
- **Type-Safe**: Fully typed Python codebase with comprehensive validation

## Quick Start

### Install UV (if not already installed)

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install Python and Setup Project

```bash
# Install latest Python
uv python install

# Clone the repository
git clone https://github.com/dunamismax/svforge-mc.git
cd svforge-mc

# Install dependencies
uv sync

# Verify installation
uv run svforge --help
```

## Usage

### Install a Server

```bash
# Install Paper server (latest version)
uv run svforge install paper 1.21.8

# Install with custom settings
uv run svforge install paper 1.21.8 --ram 4096 --port 25566

# Install specific build
uv run svforge install paper 1.21.8 --build 450
```

### Supported Server Types

- **vanilla**: Official Mojang Minecraft servers
- **paper**: High-performance server with plugin support and optimizations
- **spigot**: Plugin-compatible server (compiles from BuildTools source)
- **forge**: Modded server with Minecraft Forge mod loader support
- **leaf**: Paper fork with additional performance optimizations

### Available Commands

| Command | Description |
|---------|-------------|
| `install` | Install a Minecraft server |
| `versions` | List available versions for a server type |
| `list` | Show installed servers |
| `system` | Display system information |
| `config` | Manage configuration |

### Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--ram` | RAM allocation in MB | 2048 |
| `--port` | Server port | 25565 |
| `--build` | Specific build (Paper/Leaf only) | Latest |
| `--forge-version` | Forge version | Latest |
| `--directory` | Custom install directory | Auto |

## Examples

### List Available Versions

```bash
uv run svforge versions paper
uv run svforge versions vanilla
```

### Check System Compatibility

```bash
uv run svforge system
```

### Install Different Server Types

```bash
# Vanilla server
uv run svforge install vanilla 1.21.8

# Paper server with specific build
uv run svforge install paper 1.21.8 --build 450

# Spigot server (compiles from source)
uv run svforge install spigot 1.20.4

# Forge server
uv run svforge install forge 1.20.1 --forge-version 47.3.0

# Leaf server
uv run svforge install leaf 1.21.8
```

### Manage Installed Servers

```bash
# List installed servers
uv run svforge list

# Start a server (navigate to server directory first)
cd ~/minecraft_servers/paper-1.21.8
./start.sh
```

## Server Management

After installation, each server includes:

- Server JAR file
- Startup script (`start.sh`)
- Basic configuration files
- EULA acceptance

### Starting Servers

Navigate to the server directory and run:

```bash
./start.sh
```

### Server Console Management

svforge uses GNU screen to manage server consoles:

- Detach from console: `Ctrl+A` then `Ctrl+D`
- Reattach to console: `screen -r svforge-[type]-[version]`
- List active sessions: `screen -ls`
- Stop server: Use the `stop` command in the server console

## Configuration

Configuration is stored in YAML format:

- **macOS**: `~/Library/Application Support/serverforge/config.yaml`
- **Linux**: `~/.config/serverforge/config.yaml`

### Reset Configuration

```bash
uv run svforge config --reset
```

## Requirements

- **Python**: 3.10 or higher
- **Operating System**: macOS 10.14+ or Linux (Windows not currently supported)
- **Java**: Automatically installed as needed (Java 8, 11, 17, or 21)
- **Internet Connection**: Required for downloading server files and version information
- **GNU screen**: For console management (typically pre-installed on Linux/macOS)

### Java Version Requirements

- Minecraft 1.7.x - 1.16.x: Java 8
- Minecraft 1.17.x - 1.20.4: Java 17
- Minecraft 1.20.5+: Java 21

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/dunamismax/svforge-mc.git
cd svforge-mc

# Install with development dependencies
uv sync --dev

# Run tests
uv run pytest

# Code formatting
uv run ruff format
uv run ruff check

# Type checking
uv run mypy svforge
```

### Project Structure

```
svforge/
├── __init__.py          # Package initialization
├── cli.py               # Main CLI interface
├── constants.py         # Application constants
├── exceptions.py        # Custom exception classes
├── config/              # Configuration management
│   ├── __init__.py
│   ├── settings.py      # Settings and config loading
│   └── logging_config.py # Logging setup
├── servers/             # Server implementations
│   ├── __init__.py
│   ├── base.py          # Base server class
│   ├── vanilla.py       # Vanilla server
│   ├── paper.py         # Paper server
│   ├── spigot.py        # Spigot server
│   ├── forge.py         # Forge server
│   └── leaf.py          # Leaf server
└── utils/               # Utility modules
    ├── __init__.py
    ├── api.py           # API clients and downloaders
    ├── base_api.py      # Base API classes
    ├── system.py        # System utilities and Java management
    └── validation.py    # Input validation utilities
```

## Troubleshooting

### Java Not Found

Check Java installations and install manually if needed:

```bash
# Check Java installations
uv run svforge system

# Install Java manually if needed
# macOS: brew install openjdk@21
# Linux: sudo apt install openjdk-21-jdk
```

### Permission Errors

Resolve file permission issues:

```bash
# Make start script executable
chmod +x /path/to/server/start.sh

# Fix directory permissions (Linux)
sudo chown -R $USER:$USER ~/minecraft_servers/
```

### Network Connectivity Issues

Test network connectivity to required services:

```bash
# Test Mojang API connectivity
curl -I https://launchermeta.mojang.com/mc/game/version_manifest.json

# Test Paper API connectivity
curl -I https://api.papermc.io/v2/projects/paper
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
uv run svforge --debug install paper 1.21.8
```

## License

This work is licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-nc-sa/4.0/).

## Support

- **Issues**: [GitHub Issues](https://github.com/dunamismax/svforge-mc/issues)
- **Repository**: [GitHub Repository](https://github.com/dunamismax/svforge-mc)

## Author

- **dunamismax** - [GitHub Profile](https://github.com/dunamismax)
