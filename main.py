#!/usr/bin/env python3
"""
IPF - Image Processing Functions
Giriş noktası.

    python main.py
"""

import sys

if __name__ == "__main__":
    try:
        from ipf_gui.app import main
    except ImportError as exc:
        print("Bağımlılık eksik:", exc)
        print("\nKurulum:")
        print("    pip install -r requirements.txt")
        sys.exit(1)

    main()
