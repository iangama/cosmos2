"""Send a local Lua command to the running proof and wait for its response."""
import argparse
import json
from websockets.sync.client import connect

def execute(script):
    with connect("ws://127.0.0.1:4682", open_timeout=5, close_timeout=1, ping_interval=None) as connection:
        connection.send(json.dumps({"type": "apiHandshake", "apiVersion": {"major": 1, "minor": 0, "patch": 0}}))
        connection.send(json.dumps({"topic": 1, "type": "luascript", "payload": {"script": script, "return": True}}))
        return json.loads(connection.recv(timeout=15))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("script")
    args = parser.parse_args()
    print(json.dumps(execute(args.script), ensure_ascii=False))
