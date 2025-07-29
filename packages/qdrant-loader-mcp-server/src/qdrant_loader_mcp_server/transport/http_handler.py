"""HTTP Transport Handler for MCP Protocol 2025-06-18."""

import asyncio
import json
import re
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class HTTPTransportHandler:
    """HTTP Transport Handler for MCP Protocol with SSE streaming support."""
    
    def __init__(self, mcp_handler, host: str = "127.0.0.1", port: int = 8080):
        """Initialize HTTP transport handler.
        
        Args:
            mcp_handler: The MCP handler instance to process requests
            host: Host to bind to (default: 127.0.0.1 for security)
            port: Port to bind to (default: 8080)
        """
        self.mcp_handler = mcp_handler
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="QDrant Loader MCP Server",
            description="HTTP transport for Model Context Protocol",
            version="1.0.0"
        )
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._setup_middleware()
        self._setup_routes()
        logger.info(f"HTTP transport handler initialized on {host}:{port}")
    
    def _setup_middleware(self):
        """Setup FastAPI middleware for CORS and security."""
        # Add CORS middleware for browser clients
        self.app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup FastAPI routes for MCP endpoints."""
        
        @self.app.post("/mcp")
        async def handle_mcp_post(request: Request):
            """Handle client-to-server messages via HTTP POST."""
            logger.debug("Received POST request to /mcp")
            return await self._handle_post_request(request)
        
        @self.app.get("/mcp")
        async def handle_mcp_get(request: Request):
            """Handle server-to-client streaming via SSE."""
            logger.debug("Received GET request to /mcp for SSE streaming")
            return await self._handle_get_request(request)
        
        @self.app.options("/mcp")
        async def handle_mcp_options():
            """Handle CORS preflight requests for /mcp endpoint."""
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true"
                }
            )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "transport": "http", "protocol": "mcp"}
    
    async def _handle_post_request(self, request: Request) -> Dict[str, Any]:
        """Process MCP messages from HTTP POST requests.
        
        Args:
            request: FastAPI request object
            
        Returns:
            MCP response dictionary
        """
        try:
            # Security: Validate Origin header (DNS rebinding protection)
            origin = request.headers.get("origin")
            if not self._validate_origin(origin):
                logger.warning(f"Invalid origin header: {origin}")
                raise HTTPException(status_code=403, detail="Invalid origin")
            
            # Protocol version validation (optional with backward compatibility)
            protocol_version = request.headers.get("mcp-protocol-version")
            if not self._validate_protocol_version(protocol_version):
                logger.warning(f"Unsupported protocol version: {protocol_version}")
                # Continue with warning but don't reject for backward compatibility
            
            # Session management
            session_id = request.headers.get("mcp-session-id")
            if not session_id:
                session_id = f"session_{int(time.time() * 1000)}"
                logger.debug(f"Generated new session ID: {session_id}")
            
            # Process MCP request
            mcp_request = await request.json()
            logger.debug(f"Processing MCP request: {mcp_request.get('method', 'unknown')}")
            
            # Add headers context to request processing  
            response = await self.mcp_handler.handle_request(
                mcp_request, 
                headers=dict(request.headers)
            )
            
            # Store response for SSE streaming if needed
            if session_id not in self.sessions:
                self.sessions[session_id] = {"messages": [], "created_at": time.time()}
            
            # Store any server-initiated messages for this session
            # (for future elicitation support)
            
            logger.debug(f"Successfully processed MCP request, returning response")
            return response
            
        except HTTPException:
            # Re-raise HTTPException so FastAPI can handle it properly
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
        except Exception as e:
            logger.error(f"Error processing MCP request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0", 
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _handle_get_request(self, request: Request) -> StreamingResponse:
        """Handle SSE streaming for server-to-client messages.
        
        Args:
            request: FastAPI request object
            
        Returns:
            StreamingResponse with SSE events
        """
        session_id = request.headers.get("mcp-session-id")
        logger.debug(f"Setting up SSE stream for session: {session_id}")
        
        async def event_stream():
            """Generate SSE events for the session."""
            try:
                while True:
                    # Check for new messages in session
                    if session_id and session_id in self.sessions:
                        session = self.sessions[session_id]
                        if session.get("messages"):
                            for message in session["messages"]:
                                logger.debug(f"Sending SSE message: {message}")
                                yield f"data: {json.dumps(message)}\n\n"
                            session["messages"] = []  # Clear sent messages
                    
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                    
                    await asyncio.sleep(1.0)  # Poll interval (1 second)
                    
            except asyncio.CancelledError:
                logger.debug(f"SSE stream cancelled for session: {session_id}")
                raise
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    
    def _validate_origin(self, origin: Optional[str]) -> bool:
        """Validate Origin header to prevent DNS rebinding attacks.
        
        Args:
            origin: Origin header value
            
        Returns:
            True if origin is valid, False otherwise
        """
        if not origin:
            # Allow requests without Origin (non-browser clients)
            return True
        
        # Only allow localhost origins for security
        allowed_origins = [
            "http://localhost",
            "https://localhost", 
            "http://127.0.0.1",
            "https://127.0.0.1"
        ]
        
        # Check if origin starts with any allowed origin
        # (to handle different ports like http://localhost:3000)
        return any(origin.startswith(allowed) for allowed in allowed_origins)
    
    def _validate_protocol_version(self, version: Optional[str]) -> bool:
        """Validate MCP protocol version header.
        
        Args:
            version: Protocol version from header
            
        Returns:
            True if version is supported, False otherwise
        """
        if not version:
            # Allow for backward compatibility
            return True
        
        # Supported protocol versions
        supported_versions = ["2025-06-18", "2025-03-26", "2024-11-05"]
        return version in supported_versions
    
    def add_session_message(self, session_id: str, message: Dict[str, Any]):
        """Add a message to a session for SSE streaming.
        
        Args:
            session_id: Session identifier
            message: Message to add to session queue
        """
        if session_id in self.sessions:
            self.sessions[session_id]["messages"].append(message)
            logger.debug(f"Added message to session {session_id}: {message}")
    
    def cleanup_sessions(self, max_age_seconds: int = 3600):
        """Clean up old sessions.
        
        Args:
            max_age_seconds: Maximum age of sessions in seconds (default: 1 hour)
        """
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session.get("created_at", 0) > max_age_seconds
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.debug(f"Cleaned up expired session: {session_id}")
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions") 