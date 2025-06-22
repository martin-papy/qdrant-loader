"""Daemon Management CLI Commands.

This module provides CLI commands for managing the QDrant Loader daemon process,
including start, stop, status, and restart operations.
"""

import click
import json
import sys
import time
from pathlib import Path
from typing import Optional

from .core import (
    LOG_LEVEL_OPTION,
    WORKSPACE_OPTION,
    load_config_with_workspace,
    setup_logging,
    setup_workspace,
    validate_workspace_flags,
)
from ..daemon import DaemonManager, DaemonConfig
from ..daemon.service import ServiceManager
from ..daemon.scheduler import BackgroundScheduler, ScheduleConfig


@click.group(name="daemon")
def daemon_group():
    """Daemon process management commands.
    
    These commands manage the QDrant Loader daemon process that provides
    continuous operation with background tasks, API server, and web interface.
    """
    pass


@daemon_group.command(name="start")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@click.option(
    "--pid-dir",
    type=click.Path(),
    help="Directory for PID file (default: /var/run/qdrant-loader)"
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Log file path for daemon output"
)
@click.option(
    "--working-dir",
    type=click.Path(exists=True),
    help="Working directory for daemon process"
)
@click.option(
    "--foreground",
    "-f",
    is_flag=True,
    help="Run in foreground instead of daemonizing"
)
def start_daemon(
    workspace: Optional[Path],
    log_level: str,
    pid_dir: Optional[str],
    log_file: Optional[str],
    working_dir: Optional[str],
    foreground: bool
):
    """Start the QDrant Loader daemon process.
    
    The daemon provides continuous operation with:
    - Background task scheduling
    - REST API server 
    - Web interface
    - Automated validation and monitoring
    """
    try:
        # Setup workspace if provided
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)
        
        # Setup logging with workspace support
        setup_logging(log_level, workspace_config)
        
        # Load configuration with workspace support
        load_config_with_workspace(
            workspace_config=workspace_config,
            skip_validation=True  # Skip validation for daemon startup
        )
        
        # Create daemon configuration
        daemon_config = DaemonConfig()
        
        if pid_dir:
            daemon_config.pid_dir = Path(pid_dir)
        if log_file:
            daemon_config.log_file = Path(log_file)
        if working_dir:
            daemon_config.working_dir = Path(working_dir)
        elif workspace_config:
            # Use workspace directory as working directory
            daemon_config.working_dir = workspace_config.workspace_path
        
        # Create daemon manager
        daemon_manager = DaemonManager(daemon_config)
        
        # Check if already running
        if daemon_manager.is_running():
            click.echo("Daemon is already running", err=True)
            sys.exit(1)
        
        if foreground:
            click.echo("Starting daemon in foreground mode...")
            _run_daemon_services(daemon_manager, workspace_config)
        else:
            click.echo("Starting daemon...")
            daemon_manager.daemonize()
            _run_daemon_services(daemon_manager, workspace_config)
        
    except Exception as e:
        click.echo(f"Failed to start daemon: {e}", err=True)
        sys.exit(1)


@daemon_group.command(name="stop")
@click.option(
    "--pid-dir",
    type=click.Path(),
    help="Directory for PID file (default: /var/run/qdrant-loader)"
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=30,
    help="Timeout in seconds for graceful shutdown"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force kill if graceful shutdown fails"
)
def stop_daemon(pid_dir: Optional[str], timeout: int, force: bool):
    """Stop the running daemon process.
    
    Sends SIGTERM for graceful shutdown, with optional force kill
    if the process doesn't stop within the timeout period.
    """
    try:
        # Create daemon configuration
        daemon_config = DaemonConfig()
        if pid_dir:
            daemon_config.pid_dir = Path(pid_dir)
        
        # Create daemon manager
        daemon_manager = DaemonManager(daemon_config)
        
        # Check if running
        if not daemon_manager.is_running():
            click.echo("Daemon is not running")
            return
        
        click.echo("Stopping daemon...")
        
        # Stop daemon
        if daemon_manager.stop(timeout=timeout):
            click.echo("Daemon stopped successfully")
        else:
            click.echo("Daemon was not running")
            
    except Exception as e:
        click.echo(f"Failed to stop daemon: {e}", err=True)
        sys.exit(1)


@daemon_group.command(name="restart")
@WORKSPACE_OPTION
@LOG_LEVEL_OPTION
@click.option(
    "--pid-dir",
    type=click.Path(),
    help="Directory for PID file"
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=30,
    help="Timeout in seconds for shutdown"
)
def restart_daemon(workspace: Optional[Path], log_level: str, pid_dir: Optional[str], timeout: int):
    """Restart the daemon process.
    
    Stops the current daemon and starts a new one with the same configuration.
    """
    try:
        # Create daemon configuration
        daemon_config = DaemonConfig()
        if pid_dir:
            daemon_config.pid_dir = Path(pid_dir)
        
        # Create daemon manager
        daemon_manager = DaemonManager(daemon_config)
        
        # Stop if running
        if daemon_manager.is_running():
            click.echo("Stopping daemon...")
            daemon_manager.stop(timeout=timeout)
            
            # Wait a moment for cleanup
            time.sleep(2)
        
        # Setup workspace and configuration for restart
        workspace_config = None
        if workspace:
            workspace_config = setup_workspace(workspace)
        
        # Start daemon
        click.echo("Starting daemon...")
        daemon_manager.daemonize()
        _run_daemon_services(daemon_manager, workspace_config)
        
        click.echo("Daemon restarted successfully")
        
    except Exception as e:
        click.echo(f"Failed to restart daemon: {e}", err=True)
        sys.exit(1)


@daemon_group.command(name="status")
@click.option(
    "--pid-dir",
    type=click.Path(),
    help="Directory for PID file"
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output status in JSON format"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed status information"
)
def status_daemon(pid_dir: Optional[str], output_json: bool, verbose: bool):
    """Show daemon process status.
    
    Displays current status including PID, resource usage, and service health.
    """
    try:
        # Create daemon configuration
        daemon_config = DaemonConfig()
        if pid_dir:
            daemon_config.pid_dir = Path(pid_dir)
        
        # Create daemon manager
        daemon_manager = DaemonManager(daemon_config)
        
        # Get status
        status = daemon_manager.status()
        
        if output_json:
            # JSON output
            print(json.dumps(status, indent=2, default=str))
        else:
            # Human-readable output
            if status["running"]:
                click.echo(f"✅ Daemon is running (PID: {status['pid']})")
                
                if verbose:
                    if "cpu_percent" in status:
                        click.echo(f"   CPU: {status['cpu_percent']:.1f}%")
                    if "memory_percent" in status:
                        click.echo(f"   Memory: {status['memory_percent']:.1f}%")
                    if "create_time" in status:
                        click.echo(f"   Started: {status['create_time']}")
                    if "status" in status:
                        click.echo(f"   Status: {status['status']}")
                        
                    click.echo(f"   PID file: {status['pid_file']}")
                    
                    if status.get("access_denied"):
                        click.echo("   ⚠️  Access denied for detailed process info")
            else:
                click.echo("❌ Daemon is not running")
                
                if status["pid_file_exists"]:
                    click.echo("   ⚠️  Stale PID file exists")
                    
    except Exception as e:
        click.echo(f"Failed to get daemon status: {e}", err=True)
        sys.exit(1)


@daemon_group.command(name="logs")
@click.option(
    "--lines",
    "-n",
    type=int,
    default=50,
    help="Number of log lines to show"
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output (like tail -f)"
)
@click.option(
    "--log-file",
    type=click.Path(exists=True),
    help="Path to log file"
)
def show_logs(lines: int, follow: bool, log_file: Optional[str]):
    """Show daemon log output.
    
    Displays recent log entries from the daemon process.
    """
    import subprocess
    
    try:
        # Default log file path
        if not log_file:
            log_file = "/var/log/qdrant-loader/daemon.log"
        
        log_path = Path(log_file)
        if not log_path.exists():
            click.echo(f"Log file not found: {log_path}", err=True)
            sys.exit(1)
        
        # Use tail command to show logs
        cmd = ["tail"]
        if follow:
            cmd.append("-f")
        cmd.extend(["-n", str(lines), str(log_path)])
        
        # Execute tail command
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully when following logs
            pass
            
    except Exception as e:
        click.echo(f"Failed to show logs: {e}", err=True)
        sys.exit(1)





def _run_daemon_services(daemon_manager: DaemonManager, workspace_config):
    """Run daemon services (scheduler, API, web interface)."""
    import asyncio
    
    # For now, just run the scheduler service
    # TODO: Add API server and web interface services
    
    async def run_services():
        # Create service manager
        service_manager = ServiceManager()
        
        # Register shutdown handler
        daemon_manager.register_shutdown_handler(
            "service_manager",
            lambda: asyncio.create_task(service_manager.stop_all())
        )
        
        try:
            # Create and register scheduler service
            scheduler_config = ScheduleConfig()  # TODO: Load from config file
            scheduler = BackgroundScheduler(scheduler_config)
            service_manager.register_service(scheduler, startup_priority=1)
            
            # Start all services
            await service_manager.start_all()
            
            # Keep running until signal received
            while True:
                await asyncio.sleep(1)
                
                # Check if services are healthy
                health_status = await service_manager.health_check_all()
                if not all(health_status.values()):
                    unhealthy = [name for name, healthy in health_status.items() if not healthy]
                    click.echo(f"Unhealthy services detected: {unhealthy}", err=True)
                
        except Exception as e:
            click.echo(f"Service error: {e}", err=True)
        finally:
            # Cleanup
            await service_manager.stop_all()
            service_manager.cleanup()
            daemon_manager.cleanup()
    
    # Run the event loop
    try:
        asyncio.run(run_services())
    except KeyboardInterrupt:
        click.echo("Daemon interrupted")
    except Exception as e:
        click.echo(f"Daemon error: {e}", err=True)
        sys.exit(1) 