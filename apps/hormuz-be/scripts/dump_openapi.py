import json
from pathlib import Path

from main import app


target = Path(__file__).resolve().parents[1] / "openapi.json"
target.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"Wrote {target}")

