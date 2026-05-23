"""PyInstaller entry stub.

The real entry point is `worldcanon.main:main`. We can't point PyInstaller at
that file directly because PyInstaller runs the entry script as a top-level
module — that strips the package context and the relative imports in main.py
(`from .api import build_app`) fail at runtime with:

    ImportError: attempted relative import with no known parent package

This wrapper imports the package the normal way, so all relative imports
resolve.
"""
from worldcanon.main import main


if __name__ == "__main__":
    main()
