import json
from pathlib import Path

from config.settings import BASE_DIR


class Reflections:
    def __init__(self):
        self.file_path = BASE_DIR / "data" / "reflections.json"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        if self.file_path.exists():
            return json.loads(self.file_path.read_text())
        return []

    def save(self, reflection: dict):
        reflections = self.load()
        reflections.append(reflection)
        self.file_path.write_text(json.dumps(reflections, indent=2))
