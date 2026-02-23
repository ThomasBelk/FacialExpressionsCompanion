import sys
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)  # points to _internal
    else:
        base = Path(__file__).parent
    return base / relative_path