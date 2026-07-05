"""DogCalC entry point — run with: python main.py  or  python -m src.main"""

import sys
import os

# Ensure project root is on sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.app import run


def main():
    run()


if __name__ == "__main__":
    main()
