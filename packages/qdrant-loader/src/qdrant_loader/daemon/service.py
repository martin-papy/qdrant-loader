"""Service Manager for QDrant Loader Daemon.

This module provides service lifecycle management for the various components
that run within the daemon process (API server, background tasks, etc.).
"""

import asyncio
import logging
from typing import Dict, List, Optional, Protocol, runtime_checkable
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service state enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class ServiceInfo:
    """Information about a service."""
    name: str
    state: ServiceState
    error: Optional[str] = None
    start_time: Optional[float] = None
    stop_time: Optional[float] = None


@runtime_checkable
class Service(Protocol):
    """Protocol for daemon services."""
    
    @property
    def name(self) -> str:
        """Service name."""
        ...
    
    async def start(self) -> None:
        """Start the service."""
        ...
    
    async def stop(self) -> None:
        """Stop the service."""
        ...
    
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        ...


class BaseService(ABC):
    """Base class for daemon services."""
    
    def __init__(self, name: str):
        """Initialize base service.
        
        Args:
            name: Service name.
        """
        self._name = name
        self._state = ServiceState.STOPPED
        self._error: Optional[str] = None
        
    @property
    def name(self) -> str:
        """Service name."""
        return self._name
    
    @property
    def state(self) -> ServiceState:
        """Current service state."""
        return self._state
    
    @property
    def error(self) -> Optional[str]:
        """Last error message if any."""
        return self._error
        
    @abstractmethod
    async def _start_impl(self) -> None:
        """Service-specific start implementation."""
        pass
    
    @abstractmethod
    async def _stop_impl(self) -> None:
        """Service-specific stop implementation."""
        pass
    
    async def start(self) -> None:
        """Start the service."""
        if self._state != ServiceState.STOPPED:
            logger.warning(f"Service {self.name} is not in stopped state")
            return
            
        self._state = ServiceState.STARTING
        self._error = None
        
        try:
            logger.info(f"Starting service: {self.name}")
            await self._start_impl()
            self._state = ServiceState.RUNNING
            logger.info(f"Service started: {self.name}")
            
        except Exception as e:
            self._error = str(e)
            self._state = ServiceState.FAILED
            logger.error(f"Failed to start service {self.name}: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the service."""
        if self._state not in [ServiceState.RUNNING, ServiceState.FAILED]:
            logger.warning(f"Service {self.name} is not running")
            return
            
        self._state = ServiceState.STOPPING
        
        try:
            logger.info(f"Stopping service: {self.name}")
            await self._stop_impl()
            self._state = ServiceState.STOPPED
            logger.info(f"Service stopped: {self.name}")
            
        except Exception as e:
            self._error = str(e)
            self._state = ServiceState.FAILED
            logger.error(f"Failed to stop service {self.name}: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        return self._state == ServiceState.RUNNING


class ServiceManager:
    """Manages multiple daemon services."""
    
    def __init__(self):
        """Initialize service manager."""
        self._services: Dict[str, Service] = {}
        self._startup_order: List[str] = []
        self._shutdown_order: List[str] = []
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="service-mgr")
        
    def register_service(self, service: Service, startup_priority: int = 0) -> None:
        """Register a service with the manager.
        
        Args:
            service: Service to register.
            startup_priority: Lower numbers start first. Services with same
                            priority start concurrently.
        """
        if service.name in self._services:
            raise ValueError(f"Service {service.name} already registered")
            
        self._services[service.name] = service
        
        # Insert in startup order based on priority
        inserted = False
        for i, existing_name in enumerate(self._startup_order):
            # For now, simple ordering - could be enhanced with actual priority tracking
            if not inserted:
                self._startup_order.insert(i, service.name)
                inserted = True
                break
                
        if not inserted:
            self._startup_order.append(service.name)
        
        # Shutdown order is reverse of startup
        self._shutdown_order = list(reversed(self._startup_order))
        
        logger.info(f"Registered service: {service.name}")
    
    def unregister_service(self, name: str) -> None:
        """Unregister a service.
        
        Args:
            name: Name of service to unregister.
        """
        if name not in self._services:
            logger.warning(f"Service {name} not registered")
            return
            
        del self._services[name]
        if name in self._startup_order:
            self._startup_order.remove(name)
        if name in self._shutdown_order:
            self._shutdown_order.remove(name)
            
        logger.info(f"Unregistered service: {name}")
    
    async def start_all(self) -> None:
        """Start all registered services in order."""
        logger.info("Starting all services...")
        
        for service_name in self._startup_order:
            service = self._services[service_name]
            try:
                await service.start()
            except Exception as e:
                logger.error(f"Failed to start service {service_name}: {e}")
                # Stop any services that were started before this failure
                await self._stop_started_services(service_name)
                raise
        
        logger.info("All services started successfully")
    
    async def stop_all(self) -> None:
        """Stop all services in reverse order."""
        logger.info("Stopping all services...")
        
        errors = []
        for service_name in self._shutdown_order:
            if service_name not in self._services:
                continue
                
            service = self._services[service_name]
            try:
                await service.stop()
            except Exception as e:
                logger.error(f"Error stopping service {service_name}: {e}")
                errors.append((service_name, e))
        
        if errors:
            error_msg = "; ".join([f"{name}: {err}" for name, err in errors])
            logger.error(f"Errors occurred during shutdown: {error_msg}")
        else:
            logger.info("All services stopped successfully")
    
    async def _stop_started_services(self, failed_service: str) -> None:
        """Stop services that were started before a failure occurred."""
        failed_index = self._startup_order.index(failed_service)
        services_to_stop = self._startup_order[:failed_index]
        
        for service_name in reversed(services_to_stop):
            service = self._services[service_name]
            try:
                await service.stop()
            except Exception as e:
                logger.error(f"Error stopping service {service_name} during cleanup: {e}")
    
    async def restart_service(self, name: str) -> None:
        """Restart a specific service.
        
        Args:
            name: Name of service to restart.
        """
        if name not in self._services:
            raise ValueError(f"Service {name} not registered")
            
        service = self._services[name]
        logger.info(f"Restarting service: {name}")
        
        try:
            await service.stop()
        except Exception as e:
            logger.warning(f"Error stopping service {name}: {e}")
        
        await service.start()
        logger.info(f"Service restarted: {name}")
    
    def get_service_info(self, name: str) -> Optional[ServiceInfo]:
        """Get information about a service.
        
        Args:
            name: Service name.
            
        Returns:
            ServiceInfo if service exists, None otherwise.
        """
        if name not in self._services:
            return None
            
        service = self._services[name]
        
        if hasattr(service, 'state'):
            state = service.state
        else:
            # Infer state for protocol-only services
            state = ServiceState.RUNNING  # Assume running if registered
            
        if hasattr(service, 'error'):
            error = service.error
        else:
            error = None
        
        return ServiceInfo(
            name=name,
            state=state,
            error=error
        )
    
    def get_all_service_info(self) -> Dict[str, ServiceInfo]:
        """Get information about all services.
        
        Returns:
            Dictionary mapping service names to ServiceInfo.
        """
        return {
            name: self.get_service_info(name)
            for name in self._services.keys()
        }
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all services.
        
        Returns:
            Dictionary mapping service names to health status.
        """
        results = {}
        
        for name, service in self._services.items():
            try:
                results[name] = await service.health_check()
            except Exception as e:
                logger.error(f"Health check failed for service {name}: {e}")
                results[name] = False
        
        return results
    
    def cleanup(self) -> None:
        """Clean up service manager resources."""
        self._executor.shutdown(wait=True)
        logger.info("Service manager cleanup completed") 