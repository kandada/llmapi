import uvicorn
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

from routers.main import create_app


def run(host: str = "0.0.0.0", port: int = 3000, reload: bool = False):
    uvicorn.run(
        "llmapi.main:app",
        host=host,
        port=port,
        reload=reload,
    )


def main():
    parser = argparse.ArgumentParser(prog="llmapi", description="LLMAPI - OpenAI-compatible API Gateway")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Start the LLMAPI server")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    run_parser.add_argument("-p", "--port", type=int, default=3000, help="Port to bind (default: 3000)")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    if args.command == "run":
        run(host=args.host, port=args.port, reload=args.reload)
    else:
        parser.print_help()


app = create_app()

if __name__ == "__main__":
    run()
