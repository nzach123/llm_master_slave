from core.hub import Spine

def main():
    spine = Spine()
    print("Starting Spine Mock Loop...")
    result = spine.run_mock_loop()
    print(f"Loop finished. Result: {result.message}")

if __name__ == "__main__":
    main()
