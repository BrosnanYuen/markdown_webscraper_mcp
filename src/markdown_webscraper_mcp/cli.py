from __future__ import annotations

import argparse

from .config import load_config
from .server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run markdown_webscraper_mcp server")
    parser.add_argument("--config", required=True, help="Path to config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    run_server(config)


if __name__ == "__main__":
    main()
