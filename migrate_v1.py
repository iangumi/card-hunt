
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
old = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else HERE.parent / "card_hunt_local_app"
src = old / "data"
dst = HERE / "data"

if not src.exists():
    raise SystemExit(f"Could not find v1 data folder: {src}")

dst.mkdir(exist_ok=True)
for p in src.rglob("*"):
    rel = p.relative_to(src)
    target = dst / rel
    if p.is_dir():
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"SKIP existing: {target}")
        else:
            shutil.copy2(p, target)
            print(f"COPY: {p} -> {target}")

print("Migration complete.")
