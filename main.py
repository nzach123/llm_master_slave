import argparse
from core.hub import Spine

def main():
    parser = argparse.ArgumentParser(description="Conductor Spine Controller")
    parser.add_argument("--autonomous", metavar="INTENT", type=str, help="Run autonomous loop with user intent")
    args = parser.parse_args()

    spine = Spine()
    
    if args.autonomous:
        print(f"Starting Spine Autonomous Loop with intent: {args.autonomous}")
        result = spine.run_autonomous_loop(args.autonomous)
    else:
        print("Starting Spine Mock Loop...")
        result = spine.run_mock_loop()
        
    print(f"Loop finished. Result: {result.message}")

if __name__ == "__main__":
    main()