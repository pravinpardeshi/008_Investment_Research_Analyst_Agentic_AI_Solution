from pathlib import Path

from config.settings import UPLOAD_DIR


class FilingSearch:
    def __init__(self):
        self.base_dir = UPLOAD_DIR

    def list_documents(self, company: str | None = None) -> list[dict]:
        results = []
        for subdir in ["annual_reports", "quarterly_reports", "earnings_calls", "presentations"]:
            dir_path = self.base_dir / subdir
            if not dir_path.exists():
                continue
            for f in sorted(dir_path.iterdir()):
                if f.is_file() and company and company.lower() in f.stem.lower():
                    results.append({"filename": f.name, "path": str(f), "category": subdir})
                elif f.is_file() and not company:
                    results.append({"filename": f.name, "path": str(f), "category": subdir})
        return results

    def get_document_path(self, filename: str) -> str | None:
        for subdir in ["annual_reports", "quarterly_reports", "earnings_calls", "presentations"]:
            path = self.base_dir / subdir / filename
            if path.exists():
                return str(path)
        return None
