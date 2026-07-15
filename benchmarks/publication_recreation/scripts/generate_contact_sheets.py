"""Assemble recreated PNGs into reports/contact_sheet.png."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pipeline as P
if __name__ == "__main__":
    print("contact sheet:", P.contact_sheet())
