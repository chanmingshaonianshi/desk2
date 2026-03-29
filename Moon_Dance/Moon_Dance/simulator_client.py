#!/usr/bin/env python3
from main import main as app_main
import sys


if __name__ == "__main__":
    if "--no-gui" not in sys.argv:
        sys.argv.insert(1, "--no-gui")
    app_main()
