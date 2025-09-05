"""
Command Line Interface for ServerForge.

This module provides the main CLI interface using Click framework
for easy and interactive Minecraft server management.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel

from .config.logging_config import setup_logging
from .config.settings import config
from .servers.vanilla import VanillaServer
from .servers.paper import PaperServer
from .servers.spigot import SpigotServer
from .servers.forge import ForgeServer
from .servers.leaf import LeafServer
from .utils.system import SystemInfo, JavaManager
from .utils.validation import validate_server_installation_input
from .exceptions import ValidationError

console = Console()
logger = logging.getLogger(__name__)

# Server type mapping
SERVER_TYPES = {
    "vanilla": VanillaServer,
    "paper": PaperServer,
    "spigot": SpigotServer,
    "forge": ForgeServer,
    "leaf": LeafServer,
}


async def _install_server_async(server, progress_callback):
    """Async helper function to install server with proper resource management."""
    async with server:
        return await server.install(progress_callback)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.version_option(version="2.0.0", prog_name="svforge")
def main(debug: bool, no_color: bool) -> None:
    """ServerForge - A modern Python CLI tool for installing and managing Minecraft servers."""
    
    # Setup logging
    log_level = "DEBUG" if debug else config.get("logging.level", "INFO")
    enable_rich = not no_color and config.get("ui.colored_output", True)
    setup_logging(log_level=log_level, enable_rich_logging=enable_rich)
    
    # Check system compatibility
    if not SystemInfo.is_supported_platform():
        console.print("[red]Error: This tool only supports macOS and Linux.[/red]")
        sys.exit(1)


@main.command()
@click.argument('server_type', type=click.Choice(list(SERVER_TYPES.keys())))
@click.argument('version')
@click.option('--ram', '-r', default=2048, help='RAM allocation in MB (default: 2048)')
@click.option('--port', '-p', default=25565, help='Server port (default: 25565)')
@click.option('--build', '-b', type=int, help='Specific build number (Paper/Leaf only)')
@click.option('--forge-version', help='Specific Forge version (Forge only)')
@click.option('--directory', '-d', type=click.Path(), help='Custom installation directory')
@click.option('--force', is_flag=True, help='Force installation even if server exists')
def install(
    server_type: str,
    version: str,
    ram: int,
    port: int,
    build: Optional[int],
    forge_version: Optional[str],
    directory: Optional[str],
    force: bool
) -> None:
    """Install a Minecraft server of the specified type and version."""
    
    console.print(f"[bold blue]Installing {server_type.title()} server version {version}[/bold blue]")
    
    # Validate all inputs using shared validation utility
    try:
        validated_params = validate_server_installation_input(
            server_type=server_type,
            version=version,
            ram=ram,
            port=port,
            build=build,
            forge_version=forge_version,
            directory=directory,
            force=force
        )
        
        # Extract validated values
        validated_version = validated_params['version']
        validated_ram = validated_params['ram']
        validated_port = validated_params['port']
        validated_build = validated_params.get('build')
        validated_forge_version = validated_params.get('forge_version')
        validated_directory = validated_params.get('directory')
        validated_force = validated_params['force']
        
    except ValidationError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    
    try:
        # Create server instance
        server_class = SERVER_TYPES[server_type]
        
        kwargs = {
            "ram_allocation": validated_ram,
            "server_port": validated_port,
        }
        
        if validated_directory:
            kwargs["install_directory"] = validated_directory
        
        if server_type == "paper" and validated_build:
            kwargs["build"] = validated_build
        elif server_type == "leaf" and validated_build:
            kwargs["build"] = validated_build
        elif server_type == "forge" and validated_forge_version:
            kwargs["forge_version"] = validated_forge_version
        
        server = server_class(validated_version, **kwargs)
        
        # Check if already installed
        if server.is_installed() and not validated_force:
            console.print(f"[yellow]Server {server_type} {validated_version} is already installed at {server.install_directory}[/yellow]")
            if not click.confirm("Do you want to reinstall?"):
                sys.exit(0)
        
        # Show installation info
        info_table = Table(title=f"{server_type.title()} Server Installation")
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")
        
        info_table.add_row("Server Type", server_type.title())
        info_table.add_row("Minecraft Version", validated_version)
        info_table.add_row("RAM Allocation", f"{validated_ram} MB")
        info_table.add_row("Server Port", str(validated_port))
        info_table.add_row("Install Directory", str(server.install_directory))
        info_table.add_row("Java Version", f"Java {server.get_required_java_version()}")
        
        if hasattr(server, 'build') and server.build:
            info_table.add_row("Build", str(server.build))
        if hasattr(server, 'forge_version') and server.forge_version:
            info_table.add_row("Forge Version", server.forge_version)
        
        console.print(info_table)
        console.print()
        
        if config.get("ui.confirmation_prompts", True):
            if not click.confirm("Proceed with installation?"):
                sys.exit(0)
        
        # Install server with progress tracking
        progress_task_id = None
        progress_instance = None
        
        def progress_callback(downloaded: int, total: int) -> None:
            nonlocal progress_task_id, progress_instance
            if progress_task_id is not None and progress_instance is not None:
                progress_instance.update(progress_task_id, completed=downloaded)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            progress_task_id = progress.add_task("Installing server...", total=100)
            progress_instance = progress
            
            success = asyncio.run(_install_server_async(server, progress_callback))
        
        if success:
            console.print(Panel(
                f"[green]Successfully installed {server_type.title()} server {validated_version}![/green]\n\n"
                f"Server directory: {server.install_directory}\n"
                f"To start the server, run: ./start.sh\n"
                f"Server will be available on port {validated_port}",
                title="Installation Complete",
                border_style="green"
            ))
        else:
            console.print("[red]Server installation failed. Check logs for details.[/red]")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        console.print(f"[red]Installation failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument('server_type', type=click.Choice(list(SERVER_TYPES.keys())))
def versions(server_type: str) -> None:
    """List available versions for a server type."""
    
    console.print(f"[bold blue]Fetching available {server_type.title()} versions...[/bold blue]")
    
    try:
        server_class = SERVER_TYPES[server_type]
        temp_server = server_class("1.21")  # Temporary instance to get versions
        
        available_versions = temp_server.supported_versions
        
        if not available_versions:
            console.print(f"[yellow]No versions found for {server_type}[/yellow]")
            return
        
        # Display versions in a nice table
        table = Table(title=f"Available {server_type.title()} Versions")
        table.add_column("Version", style="cyan")
        table.add_column("Java", style="green")
        
        # Show recent versions (last 20)
        recent_versions = available_versions[-20:]
        
        for version in recent_versions:
            try:
                temp_server_for_java = server_class(version)
                java_version = temp_server_for_java.get_required_java_version()
                table.add_row(version, f"Java {java_version}")
            except:
                table.add_row(version, "Unknown")
        
        console.print(table)
        
        if len(available_versions) > 20:
            console.print(f"[dim]Showing recent 20 versions out of {len(available_versions)} total[/dim]")
            
    except Exception as e:
        logger.error(f"Failed to fetch versions: {e}")
        console.print(f"[red]Failed to fetch versions: {e}[/red]")
        sys.exit(1)


@main.command()
def list() -> None:
    """List all installed Minecraft servers."""
    
    servers_dir = config.get_servers_directory()
    
    if not servers_dir.exists():
        console.print("[yellow]No servers directory found. No servers installed.[/yellow]")
        return
    
    installed_servers = []
    
    # Scan for server directories
    for item in servers_dir.iterdir():
        if item.is_dir():
            # Try to identify server type and version from directory name
            parts = item.name.split('-', 1)
            if len(parts) == 2:
                server_type, version_part = parts
                if server_type in SERVER_TYPES:
                    # Check if server files exist
                    has_jar = any(item.glob("*.jar"))
                    has_start_script = (item / "start.sh").exists()
                    
                    installed_servers.append({
                        "type": server_type,
                        "version": version_part,
                        "directory": str(item),
                        "status": "Complete" if (has_jar and has_start_script) else "Incomplete"
                    })
    
    if not installed_servers:
        console.print("[yellow]No Minecraft servers found.[/yellow]")
        return
    
    # Display servers table
    table = Table(title="Installed Minecraft Servers")
    table.add_column("Type", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Directory", style="blue")
    
    for server in sorted(installed_servers, key=lambda x: (x["type"], x["version"])):
        status_color = "green" if server["status"] == "Complete" else "red"
        table.add_row(
            server["type"].title(),
            server["version"],
            f"[{status_color}]{server['status']}[/{status_color}]",
            server["directory"]
        )
    
    console.print(table)


@main.command()
def system() -> None:
    """Display system information and requirements."""
    
    # Get system info
    sys_info = SystemInfo.get_os_info()
    java_installations = JavaManager.find_java_installations()
    
    # System information table
    sys_table = Table(title="System Information")
    sys_table.add_column("Property", style="cyan")
    sys_table.add_column("Value", style="green")
    
    sys_table.add_row("Operating System", f"{sys_info['system']} {sys_info['release']}")
    sys_table.add_row("Architecture", sys_info["machine"])
    sys_table.add_row("Python Version", f"{sys.version.split()[0]}")
    sys_table.add_row("Supported Platform", "Yes" if SystemInfo.is_supported_platform() else "No")
    
    console.print(sys_table)
    console.print()
    
    # Java installations table
    if java_installations:
        java_table = Table(title="Java Installations")
        java_table.add_column("Version", style="cyan")
        java_table.add_column("Path", style="green")
        
        for version, path in sorted(java_installations.items()):
            java_table.add_row(f"Java {version}", path)
        
        console.print(java_table)
    else:
        console.print("[yellow]No Java installations detected.[/yellow]")
    
    console.print()
    
    # Configuration information
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Servers Directory", str(config.get_servers_directory()))
    config_table.add_row("Cache Directory", str(config.get_cache_directory()))
    config_table.add_row("Log Directory", str(config.get_log_directory()))
    config_table.add_row("Default RAM", f"{config.get('servers.default_ram')} MB")
    config_table.add_row("Auto Install Java", "Yes" if config.get('servers.java_auto_install') else "No")
    
    console.print(config_table)


@main.command()
@click.option('--reset', is_flag=True, help='Reset configuration to defaults')
def config_cmd(reset: bool) -> None:
    """Manage configuration settings."""
    
    if reset:
        if click.confirm("Are you sure you want to reset configuration to defaults?"):
            config.reset_to_defaults()
            console.print("[green]Configuration reset to defaults.[/green]")
        return
    
    console.print(f"[blue]Configuration file: {config.config_file}[/blue]")
    console.print("Use --reset to reset to defaults or edit the file directly.")


if __name__ == "__main__":
    main()