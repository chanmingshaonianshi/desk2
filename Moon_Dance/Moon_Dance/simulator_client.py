#!/usr/bin/env python3
import os
import sys
from main import main as app_main

DEFAULT_API_URL = "https://www.myhjmycjh.tech/api/v2/ingest"

if __name__ == "__main__":
    os.environ.setdefault("API_KEY", "myh")
    os.environ.setdefault("API_SERVER_URL", DEFAULT_API_URL)
    if "--no-gui" not in sys.argv:
        sys.argv.insert(1, "--no-gui")
    if "--api-url" not in sys.argv:
        sys.argv.extend(["--api-url", DEFAULT_API_URL])
    if "--no-mq" not in sys.argv:
        sys.argv.append("--no-mq")
    if "--insecure" not in sys.argv:
        sys.argv.append("--insecure")
    app_main()
