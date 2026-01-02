import argparse
import sys
import logging
from tools.analyzer import CodebaseAnalyzer

def setup_cli_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

def main():
    parser = argparse.ArgumentParser(description="Analyze the codebase and generate an architectural report.")
    parser.add_argument("--output", "-o", type=str, help="Path to save the markdown report (optional)")
    parser.add_argument("--silent", "-s", action="store_true", help="Do not print the report to stdout")
    
    args = parser.parse_args()
    
    if not args.silent:
        setup_cli_logging()
    
    try:
        analyzer = CodebaseAnalyzer()
        report = analyzer.analyze()
        
        if not args.silent:
            print("\n" + "="*50)
            print("CODEBASE ANALYSIS REPORT")
            print("="*50 + "\n")
            print(report)
            print("\n" + "="*50 + "\n")
            
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"Report saved to: {args.output}")
            
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
