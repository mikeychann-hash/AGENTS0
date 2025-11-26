from pathlib import Path
from typing import Dict


def safe_write(path: Path, content: str, base_dir: Path) -> Dict[str, str]:
    """Write to a file under base_dir to avoid escaping the sandbox."""
    resolved = (base_dir / path).resolve()
    if base_dir not in resolved.parents and resolved != base_dir:
        return {"status": "blocked", "detail": "path escapes sandbox"}
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return {"status": "ok", "detail": str(resolved)}


def safe_read(path: Path, base_dir: Path) -> Dict[str, str]:
    resolved = (base_dir / path).resolve()
    if base_dir not in resolved.parents and resolved != base_dir:
        return {"status": "blocked", "detail": "path escapes sandbox"}
    if not resolved.exists():
        return {"status": "missing", "detail": str(resolved)}
    return {"status": "ok", "detail": resolved.read_text(encoding="utf-8")}
