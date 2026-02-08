import sys
import os
import importlib

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import AgentBrain

# Remove API keys from env to ensure tests rely on passed arguments
# This must be done AFTER importing agent (which imports config -> load_dotenv)
if "GROQ_API_KEY" in os.environ:
    del os.environ["GROQ_API_KEY"]
if "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]

def test_api_key_validation():
    print("Testing API Key Validation...")

    # Case 1: Empty String (explicit)
    # self.api_key = "" or None -> None (since env is gone)
    # Actually: api_key="" -> key="" -> boolean false -> or None -> None
    # Wait: "" or None -> None.
    # So self.api_key becomes None.
    try:
        print("Test 1: Empty string API Key")
        AgentBrain("groq", api_key="") 
        print("FAIL: AgentBrain initialized with empty API key")
    except ValueError as e:
        print(f"SUCCESS: Caught expected error: {e}")
    except Exception as e:
        print(f"FAIL: Caught unexpected error: {e}")

    # Case 2: Whitespace String
    try:
        print("Test 2: Whitespace API Key")
        AgentBrain("groq", api_key="   ")
        print("FAIL: AgentBrain initialized with whitespace API key")
    except ValueError as e:
        print(f"SUCCESS: Caught expected error: {e}")
    except Exception as e:
        print(f"FAIL: Caught unexpected error: {e}")

    # Case 3: None (implicit env var lookup which fails)
    try:
        print("Test 3: None API Key (no env var)")
        AgentBrain("groq", api_key=None)
        print("FAIL: AgentBrain initialized with None API key and no Env Var")
    except ValueError as e:
        print(f"SUCCESS: Caught expected error: {e}")
    except Exception as e:
        print(f"FAIL: Caught unexpected error: {e}")

if __name__ == "__main__":
    test_api_key_validation()
