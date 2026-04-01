#!/usr/bin/env python3
import os
from main import main as app_main
import sys


if __name__ == "__main__":
    os.environ.setdefault("API_KEY", "myh")
    if "--no-gui" not in sys.argv:
        sys.argv.insert(1, "--no-gui")
    app_main()
