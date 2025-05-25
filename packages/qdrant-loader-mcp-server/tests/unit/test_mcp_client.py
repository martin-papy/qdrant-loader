"""Test script for MCP server compatibility with Cursor client."""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any

import pytest
import pytest_asyncio

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MCPTestClient:
    """Test client for MCP server."""

    def __init__(self):
        """Initialize the test client."""
        self.process: asyncio.subprocess.Process | None = None
        self.stdin: asyncio.StreamWriter | None = None
        self.stdout: asyncio.StreamReader | None = None
        self.stderr: asyncio.StreamReader | None = None
        self._startup_timeout = 5  # seconds
        self._request_timeout = 5  # seconds
        self._stderr_buffer: list[str] = []
        self._ready_event = asyncio.Event()
        self._shutdown_event = asyncio.Event()

    async def _read_stderr(self):
        """Read stderr asynchronously."""
        if not self.stderr:
            return

        logger.debug("Starting stderr reading")
        while not self._shutdown_event.is_set():
            try:
                line = await self.stderr.readline()
                if not line:
                    logger.debug("No more stderr output")
                    break
                line_str = line.decode().strip()
                self._stderr_buffer.append(line_str)
                logger.debug(f"Process stderr: {line_str}")
                # Check for server ready message in stderr
                if "Server ready to handle requests" in line_str:
                    logger.debug("Found server ready message in stderr")
                    self._ready_event.set()
            except Exception as e:
                logger.error(f"Error reading stderr: {e}")
                break
        logger.debug("Exiting stderr reading")

    async def start(self):
        """Start the MCP server process."""
        logger.debug("Starting MCP server process...")
        try:
            # Start the process with pipes for all streams
            logger.debug("Creating subprocess...")
            cmd = [sys.executable, "-m", "src.main"]
            logger.debug(f"Command: {' '.join(cmd)}")

            # Set up environment for coverage
            env = os.environ.copy()
            env["PYTHONPATH"] = "."
            env["COVERAGE_PROCESS_START"] = ".coveragerc"

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Store the streams
            self.stdin = self.process.stdin
            self.stdout = self.process.stdout
            self.stderr = self.process.stderr

            logger.debug(f"MCP server process started with PID: {self.process.pid}")

            # Start stderr reading task
            logger.debug("Starting stderr reading task...")
            asyncio.create_task(self._read_stderr())
            logger.debug("Started stderr reading task")

            # Wait for process to be ready
            logger.debug("Waiting for process to be ready...")
            try:
                await asyncio.wait_for(
                    self._ready_event.wait(), timeout=self._startup_timeout
                )
                logger.debug("Process is ready")
            except TimeoutError:
                stderr_output = "\n".join(self._stderr_buffer)
                logger.error(
                    f"Process startup timed out. Stderr output: {stderr_output}"
                )
                raise TimeoutError(
                    f"Process failed to start within timeout period. Stderr: {stderr_output}"
                )

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            logger.debug(f"Stopping MCP server process with PID: {self.process.pid}")
            try:
                # Set shutdown event to stop reading tasks
                self._shutdown_event.set()

                # Try graceful termination first
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2)
                    logger.debug("MCP server process terminated gracefully")
                except TimeoutError:
                    # Force kill if graceful termination fails
                    logger.debug("Graceful termination failed, forcing kill")
                    self.process.kill()
                    await self.process.wait()
                    logger.debug("MCP server process killed")
            except ProcessLookupError:
                logger.debug("Process already terminated")
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
            finally:
                # Clean up streams
                if self.stdin:
                    self.stdin.close()
                if self.stdout:
                    self.stdout.feed_eof()
                if self.stderr:
                    self.stderr.feed_eof()
                self.process = None
                self.stdin = None
                self.stdout = None
                self.stderr = None
                self._stderr_buffer = []
                self._ready_event.clear()
                self._shutdown_event.clear()

    async def send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a request to the MCP server and get the response.

        Args:
            request: The request to send

        Returns:
            Dict[str, Any]: The response from the server

        Raises:
            RuntimeError: If the process is not running or stdin is not available
            TimeoutError: If the request times out
            json.JSONDecodeError: If response cannot be parsed as JSON
        """
        if not self.process or not self.stdin:
            raise RuntimeError("Process is not running")

        try:
            # Send request with newline
            request_str = json.dumps(request) + "\n"
            request_bytes = request_str.encode()
            logger.debug(f"Sending request bytes: {request_bytes}")
            self.stdin.write(request_bytes)
            await self.stdin.drain()
            logger.debug(f"Sent request: {request_str.strip()}")

            # Wait for response
            start_time = time.time()
            while time.time() - start_time < self._request_timeout:
                if not self.stdout:
                    raise RuntimeError("stdout is not available")

                # Read a line non-blockingly
                line = await self.stdout.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue

                line_str = line.decode().strip()
                if not line_str:
                    continue

                logger.debug(f"Received line: {line_str}")
                try:
                    response = json.loads(line_str)
                    logger.debug(f"Received response: {json.dumps(response)}")
                    return response
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response: {e}")
                    continue

            raise TimeoutError("Request timed out - no response received")

        except Exception as e:
            logger.error(f"Error sending request: {e}")
            raise


@pytest_asyncio.fixture
async def client():
    """Create and manage MCP test client."""
    client = MCPTestClient()
    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_initialize(client: MCPTestClient):
    """Test the initialize request."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"supportsListOfferings": True},
        },
    }

    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert response["result"]["serverInfo"]["name"] == "Qdrant Loader MCP Server"
    assert response["result"]["capabilities"]["supportsListOfferings"] is True


@pytest.mark.asyncio
async def test_list_offerings(client: MCPTestClient):
    """Test the ListOfferings request."""
    request = {"jsonrpc": "2.0", "id": 2, "method": "ListOfferings", "params": {}}

    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert "offerings" in response["result"]
    assert len(response["result"]["offerings"]) == 1
    offering = response["result"]["offerings"][0]
    assert offering["id"] == "qdrant-loader"
    assert offering["name"] == "Qdrant Loader"
    assert offering["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_invalid_request(client: MCPTestClient):
    """Test an invalid request."""
    request = {"jsonrpc": "2.0", "id": 3, "method": "InvalidMethod", "params": {}}

    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "error" in response
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]
    assert "InvalidMethod" in response["error"]["data"]


@pytest.mark.asyncio
async def test_malformed_request(client: MCPTestClient):
    """Test a malformed request."""
    # Missing jsonrpc
    request = {"id": 4, "method": "search", "params": {}}
    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]

    # Wrong jsonrpc version
    request = {"jsonrpc": "1.0", "id": 5, "method": "search", "params": {}}
    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]

    # Missing method
    request = {"jsonrpc": "2.0", "id": 6, "params": {}}
    response = await client.send_request(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "error" in response
    assert response["error"]["code"] == -32600
    assert "Invalid Request" in response["error"]["message"]


@pytest.mark.asyncio
async def test_notification(client: MCPTestClient):
    """Test a notification request."""
    request = {"jsonrpc": "2.0", "method": "notify", "params": {"event": "test"}}
    response = await client.send_request(request)
    assert response == {}


async def main():
    """Run all tests."""
    client = MCPTestClient()
    try:
        await client.start()

        # Test initialize
        await test_initialize(client)

        # Test ListOfferings
        await test_list_offerings(client)

        # Test invalid request
        await test_invalid_request(client)

        # Test malformed request
        await test_malformed_request(client)
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
