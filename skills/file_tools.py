from pathlib import Path


OUTPUTS_DIR = Path("outputs")


def save_text(content: str, subdir: str, filename: str) -> Path:
    """Saves text content to outputs/<subdir>/<filename>."""
    target = OUTPUTS_DIR / subdir
    target.mkdir(parents=True, exist_ok=True)
    path = target / filename
    path.write_text(content, encoding="utf-8")
    return path


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def list_outputs(subdir: str) -> list[Path]:
    target = OUTPUTS_DIR / subdir
    return sorted(target.iterdir()) if target.exists() else []
