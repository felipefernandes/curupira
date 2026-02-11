
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

class MCPClient:
    """
    A lightweight Model Context Protocol (MCP) Client.
    Connects to a local MCP server via Stdio transport.
    """

    def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """
        Initialize the MCP Client.

        Args:
            command: The executable command to run (e.g., "python", "node").
            args: List of arguments for the command.
            env: Optional dictionary of environment variables.
        """
        self.logger = logging.getLogger(f"MCPClient-{command}")
        self.command = command
        self.args = args
        self.env = env or os.environ.copy()
        self.process = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._reader_task = None

    async def connect(self):
        """Starts the MCP server subprocess and the reader loop."""
        self.logger.info(f"Connecting to MCP Server: {self.command} {self.args}")
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, # Capture stderr for debugging
                env=self.env
            )
            
            # Start reader task
            self._reader_task = asyncio.create_task(self._read_loop())
            
            # Initialize handshake (if needed by specific server implementation, 
            # but standard MCP usually starts ready or expects an 'initialize' request)
            # For now, we'll assume it's ready to accept requests.
            # Ideally we should send 'initialize' implementation.
            await self._initialize()

        except Exception as e:
            self.logger.error(f"Failed to connect to MCP Server: {e}")
            raise

    async def _initialize(self):
        """Sends the initialize request to the server."""
        response = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05", # Example version
            "capabilities": {},
            "clientInfo": {
                "name": "CurupiraBot",
                "version": "1.0.0"
            }
        })
        self.logger.info(f"MCP Server Initialized: {response}")
        
        # Helper: Send 'notifications/initialized' as per spec flow
        await self.send_notification("notifications/initialized", {})

    async def _read_loop(self):
        """Background task to read messages from the server's stdout."""
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                if not line_str:
                    continue
                    
                try:
                    message = json.loads(line_str)
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    self.logger.warning(f"Received invalid JSON from server: {line_str}")
        except Exception as e:
            self.logger.error(f"Error in read loop: {e}")
        finally:
            self.logger.info("MCP Client connection closed.")

    async def _handle_message(self, message: Dict[str, Any]):
        """Handles incoming JSON-RPC messages."""
        if "id" in message:
            # Response to a request
            req_id = message["id"]
            if req_id in self._pending_requests:
                future = self._pending_requests.pop(req_id)
                if "error" in message:
                    future.set_exception(Exception(f"MCP Error: {message['error']}"))
                else:
                    future.set_result(message.get("result"))
        else:
            # Notification or Logging
             self.logger.debug(f"Received notification: {message}")

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Sends a JSON-RPC request and waits for the result."""
        if not self.process:
            raise RuntimeError("MCP Client is not connected.")
            
        self._request_id += 1
        req_id = self._request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        
        future = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = future
        
        payload = json.dumps(request) + "\n"
        self.process.stdin.write(payload.encode())
        await self.process.stdin.drain()
        
        return await future

    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
         """Sends a JSON-RPC notification (no waiting for response)."""
         if not self.process:
            raise RuntimeError("MCP Client is not connected.")
            
         request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
         payload = json.dumps(request) + "\n"
         self.process.stdin.write(payload.encode())
         await self.process.stdin.drain()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Wraps tools/list request."""
        result = await self.send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Wraps tools/call request."""
        result = await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return result

    async def close(self):
        """Terminates the server process."""
        if self._reader_task:
            self._reader_task.cancel()
            
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.logger.info("MCP Server process terminated.")
