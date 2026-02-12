
import sys
import json
import logging

# Configure logging to file since stdout is used for communication
logging.basicConfig(filename='dummy_server.log', level=logging.DEBUG)

def main():
    logging.info("Dummy MCP Server Started")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            logging.debug(f"Received: {line}")
            request = json.loads(line)
            
            response = handle_request(request)
            if response:
                logging.debug(f"Sending: {json.dumps(response)}")
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
        except Exception as e:
            logging.error(f"Error: {e}")

def handle_request(request):
    method = request.get("method")
    msg_id = request.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "DummyServer", "version": "1.0"}
            }
        }
        
    elif method == "notifications/initialized":
        return None # No response needed for notifications

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "dummy_echo",
                        "description": "Echoes back the input",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"}
                            },
                            "required": ["message"]
                        }
                    },
                     {
                        "name": "dummy_add",
                        "description": "Adds two numbers",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "integer"},
                                "b": {"type": "integer"}
                            },
                            "required": ["a", "b"]
                        }
                    }
                ]
            }
        }
        
    elif method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        
        result = {}
        if name == "dummy_echo":
            result = {"content": [{"type": "text", "text": f"Echo: {args.get('message')}"}]}
        elif name == "dummy_add":
            val = args.get("a", 0) + args.get("b", 0)
            result = {"content": [{"type": "text", "text": str(val)}]}
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": "Method not found"}
            }
            
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }
        
    return None

if __name__ == "__main__":
    main()
