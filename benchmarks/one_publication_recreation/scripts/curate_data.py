"""Curate raw CC0 penguin data into reproducible per-panel processed tables."""
import json
import _lib

if __name__ == "__main__":
    log = _lib.curate()
    print("Curation complete:")
    print(json.dumps(log, indent=2))
