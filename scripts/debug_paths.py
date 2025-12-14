import sys
from pathlib import Path

# Add project root to sys path (one level up from scripts)
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import DOWNLOADS_DIR, BASE_DIR

print(f"BASE_DIR: {BASE_DIR}")
print(f"DOWNLOADS_DIR: {DOWNLOADS_DIR}")

p = Path(DOWNLOADS_DIR)
print(f"Exists: {p.exists()}")
if p.exists():
    print("Files found:")
    for f in p.glob('*'):
        print(f" - {f.name}")
else:
    print("Directory does not exist")
