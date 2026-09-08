#!/usr/bin/env python3
"""Entrypoint script for LinkedIn Network Analyzer."""

import sys
from pathlib import Path

# Ensure the project root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import main

if __name__ == "__main__":
    main()
