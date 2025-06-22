"""Daemon Manager for QDrant Loader.

This module provides the core daemon infrastructure including process lifecycle
management, PID file handling, signal processing, and graceful shutdown capabilities.
"""

import os
import sys
import signal
import atexit
import psutil
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field

from ..utils.exceptions import QDrantLoaderError

logger = logging.getLogger(__name__)


class DaemonError(QDrantLoaderError):
    """Daemon-specific error."""
    pass


@dataclass
class DaemonConfig:
    """Configuration for daemon operation."""
    
    pid_dir: Path = field(default_factory=lambda: Path("/var/run/qdrant-loader"))
    pid_file: str = "qdrant-loader.pid"
    log_file: Optional[Path] = None
    working_dir: Path = field(default_factory=lambda: Path.cwd())
    umask: int = 0o022
    
    def __post_init__(self):
        """Ensure paths are Path objects."""
        if isinstance(self.pid_dir, str):
            self.pid_dir = Path(self.pid_dir)
        if isinstance(self.working_dir, str):
            self.working_dir = Path(self.working_dir)
        if self.log_file and isinstance(self.log_file, str):
            self.log_file = Path(self.log_file)


class DaemonManager:
    """Manages daemon process lifecycle and operations."""
    
    def __init__(self, config: Optional[DaemonConfig] = None):
        """Initialize daemon manager.
        
        Args:
            config: Daemon configuration. Uses defaults if None.
        """
        self.config = config or DaemonConfig()
        self.pid_file_path = self.config.pid_dir / self.config.pid_file
        self._shutdown_handlers: Dict[str, Callable] = {}
        self._is_daemon = False
        self._original_handlers: Dict[int, Any] = {}
        
    def is_running(self) -> bool:
        """Check if daemon is currently running.
        
        Returns:
            True if daemon process is running, False otherwise.
        """
        if not self.pid_file_path.exists():
            return False
            
        try:
            with open(self.pid_file_path, 'r') as f:
                pid = int(f.read().strip())
                
            # Check if process with this PID exists and is our daemon
            if psutil.pid_exists(pid):    
                proc = psutil.Process(pid)
                # Basic check - could be enhanced with process name verification
                return proc.is_running()
                
        except (ValueError, psutil.NoSuchProcess, PermissionError) as e:
            logger.debug(f"Error checking daemon status: {e}")
            
        return False
    
    def get_pid(self) -> Optional[int]:
        """Get the PID of the running daemon.
        
        Returns:
            PID if daemon is running, None otherwise.
        """
        if not self.pid_file_path.exists():
            return None
            
        try:
            with open(self.pid_file_path, 'r') as f:
                pid = int(f.read().strip())
                
            if psutil.pid_exists(pid):
                return pid
                
        except (ValueError, psutil.NoSuchProcess, PermissionError):
            pass
            
        return None
    
    def _create_pid_file(self) -> None:
        """Create PID file for the daemon process."""
        try:
            # Ensure PID directory exists
            self.config.pid_dir.mkdir(parents=True, exist_ok=True)
            
            # Write current PID to file
            with open(self.pid_file_path, 'w') as f:
                f.write(str(os.getpid()))
                
            # Register cleanup on exit
            atexit.register(self._cleanup_pid_file)
            
            logger.info(f"Created PID file: {self.pid_file_path}")
            
        except OSError as e:
            raise DaemonError(f"Failed to create PID file: {e}") from e
    
    def _cleanup_pid_file(self) -> None:
        """Remove PID file on daemon shutdown."""
        try:
            if self.pid_file_path.exists():
                self.pid_file_path.unlink()
                logger.info(f"Removed PID file: {self.pid_file_path}")
        except OSError as e:
            logger.warning(f"Failed to remove PID file: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        
        def signal_handler(signum: int, frame) -> None:
            """Handle shutdown signals."""
            signal_name = signal.Signals(signum).name
            logger.info(f"Received {signal_name}, initiating graceful shutdown...")
            
            # Call registered shutdown handlers
            for name, handler in self._shutdown_handlers.items():
                try:
                    logger.info(f"Calling shutdown handler: {name}")
                    handler()
                except Exception as e:
                    logger.error(f"Error in shutdown handler {name}: {e}")
            
            # Clean exit
            sys.exit(0)
        
        # Register handlers for common shutdown signals
        for sig in [signal.SIGTERM, signal.SIGINT]:
            self._original_handlers[sig] = signal.signal(sig, signal_handler)
            
        # SIGHUP for configuration reload (if supported)
        if hasattr(signal, 'SIGHUP'):
            def reload_handler(signum: int, frame) -> None:
                logger.info("Received SIGHUP, configuration reload not yet implemented")
                
            self._original_handlers[signal.SIGHUP] = signal.signal(
                signal.SIGHUP, reload_handler
            )
    
    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
    
    def register_shutdown_handler(self, name: str, handler: Callable) -> None:
        """Register a function to be called on graceful shutdown.
        
        Args:
            name: Name of the handler for logging purposes.
            handler: Callable to execute on shutdown.
        """
        self._shutdown_handlers[name] = handler
        logger.debug(f"Registered shutdown handler: {name}")
    
    def unregister_shutdown_handler(self, name: str) -> None:
        """Remove a shutdown handler.
        
        Args:
            name: Name of the handler to remove.
        """
        if name in self._shutdown_handlers:
            del self._shutdown_handlers[name]
            logger.debug(f"Unregistered shutdown handler: {name}")
    
    def daemonize(self) -> None:
        """Daemonize the current process using double-fork technique."""
        if self.is_running():
            raise DaemonError("Daemon is already running")
        
        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                # Parent process exits
                sys.exit(0)
                
        except OSError as e:
            raise DaemonError(f"First fork failed: {e}") from e
        
        # Decouple from parent environment
        os.chdir(str(self.config.working_dir))
        os.setsid()
        os.umask(self.config.umask)
        
        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                # Parent process exits
                sys.exit(0)
                
        except OSError as e:
            raise DaemonError(f"Second fork failed: {e}") from e
        
        # Redirect standard file descriptors
        self._redirect_file_descriptors()
        
        # Mark as daemon process
        self._is_daemon = True
        
        # Create PID file and setup signal handlers
        self._create_pid_file()
        self._setup_signal_handlers()
        
        logger.info(f"Daemonized successfully with PID: {os.getpid()}")
    
    def _redirect_file_descriptors(self) -> None:
        """Redirect stdin, stdout, stderr to appropriate files."""
        import stat
        
        # Standard input points to /dev/null
        with open(os.devnull, 'r') as null_in:
            os.dup2(null_in.fileno(), sys.stdin.fileno())
        
        # Standard output and error
        if self.config.log_file:
            log_file = open(self.config.log_file, 'a')
            os.dup2(log_file.fileno(), sys.stdout.fileno())
            os.dup2(log_file.fileno(), sys.stderr.fileno())
        else:
            # Point to /dev/null if no log file specified
            with open(os.devnull, 'w') as null_out:
                os.dup2(null_out.fileno(), sys.stdout.fileno())
                os.dup2(null_out.fileno(), sys.stderr.fileno())
    
    def stop(self, timeout: int = 30) -> bool:
        """Stop the running daemon process.
        
        Args:
            timeout: Maximum time to wait for process to stop.
            
        Returns:
            True if daemon was stopped, False if it wasn't running.
            
        Raises:
            DaemonError: If daemon couldn't be stopped within timeout.
        """
        pid = self.get_pid()
        if not pid:
            logger.info("Daemon is not running")
            return False
        
        try:
            proc = psutil.Process(pid)
            
            # Send SIGTERM for graceful shutdown
            logger.info(f"Sending SIGTERM to daemon (PID: {pid})")
            proc.terminate()
            
            # Wait for process to terminate
            try:
                proc.wait(timeout=timeout)
                logger.info("Daemon stopped gracefully")
                return True
                
            except psutil.TimeoutExpired:
                # Force kill if graceful shutdown failed
                logger.warning(f"Daemon didn't stop within {timeout}s, force killing")
                proc.kill()
                proc.wait(timeout=5)  # Give it a few seconds to die
                logger.info("Daemon force killed")
                return True
                
        except psutil.NoSuchProcess:
            logger.info("Daemon process no longer exists")
            # Clean up stale PID file
            self._cleanup_pid_file()
            return True
            
        except psutil.AccessDenied as e:
            raise DaemonError(f"Permission denied stopping daemon: {e}") from e
        except Exception as e:
            raise DaemonError(f"Error stopping daemon: {e}") from e
    
    def restart(self, timeout: int = 30) -> None:
        """Restart the daemon process.
        
        Args:
            timeout: Maximum time to wait for process to stop.
        """
        logger.info("Restarting daemon...")
        self.stop(timeout)
        # Note: actual restart would need to be handled by external process
        # as the current process will be terminating
        logger.info("Daemon stopped, restart should be handled externally")
    
    def status(self) -> Dict[str, Any]:
        """Get daemon status information.
        
        Returns:
            Dictionary with daemon status details.
        """
        pid = self.get_pid()
        status = {
            "running": pid is not None,
            "pid": pid,
            "pid_file": str(self.pid_file_path),
            "pid_file_exists": self.pid_file_path.exists(),
        }
        
        if pid:
            try:
                proc = psutil.Process(pid)
                status.update({
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "create_time": proc.create_time(),
                    "status": proc.status(),
                })
            except psutil.NoSuchProcess:
                status["running"] = False
                status["pid"] = None
            except psutil.AccessDenied:
                status["access_denied"] = True
        
        return status
    
    def cleanup(self) -> None:
        """Clean up daemon resources."""
        if self._is_daemon:
            self._restore_signal_handlers()
            self._cleanup_pid_file()
        
        # Clear shutdown handlers
        self._shutdown_handlers.clear()
        
        logger.info("Daemon cleanup completed") 