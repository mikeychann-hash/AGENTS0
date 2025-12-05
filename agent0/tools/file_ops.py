#!/usr/bin/env python3
"""
Agent0 Filesystem Operations Tool.

Provides safe filesystem operations for agents:
- Read/Write/Append files
- List directories
- Copy/Move/Delete
- Search and glob
- File metadata
- Sandboxed execution

All operations respect a base_dir sandbox to prevent escaping.

Usage:
    from agent0.tools.file_ops import FileSystem

    fs = FileSystem(base_dir="/workspace")
    fs.write("output.txt", "Hello World")
    content = fs.read("output.txt")
    files = fs.list_dir(".")
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """File metadata."""
    path: str
    name: str
    size: int
    is_file: bool
    is_dir: bool
    modified: datetime
    created: datetime
    extension: str
    permissions: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "is_file": self.is_file,
            "is_dir": self.is_dir,
            "modified": self.modified.isoformat(),
            "created": self.created.isoformat(),
            "extension": self.extension,
            "permissions": self.permissions,
        }


class FileSystem:
    """
    Sandboxed filesystem operations.

    All paths are resolved relative to base_dir and cannot escape it.
    """

    def __init__(
        self,
        base_dir: Union[str, Path] = ".",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        allowed_extensions: Optional[List[str]] = None,
    ):
        self.base_dir = Path(base_dir).resolve()
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve path within sandbox."""
        resolved = (self.base_dir / path).resolve()
        # Security check
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise PermissionError(f"Path escapes sandbox: {path}")
        return resolved

    def _check_extension(self, path: Path) -> None:
        """Check if extension is allowed."""
        if self.allowed_extensions:
            ext = path.suffix.lower()
            if ext and ext not in self.allowed_extensions:
                raise PermissionError(f"Extension not allowed: {ext}")

    # Basic Operations

    def read(self, path: Union[str, Path], encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file contents."""
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"status": "error", "error": "File not found", "path": str(path)}
            if not resolved.is_file():
                return {"status": "error", "error": "Not a file", "path": str(path)}
            if resolved.stat().st_size > self.max_file_size:
                return {"status": "error", "error": "File too large", "path": str(path)}

            content = resolved.read_text(encoding=encoding)
            return {
                "status": "ok",
                "content": content,
                "path": str(resolved.relative_to(self.base_dir)),
                "size": len(content),
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def read_bytes(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read file as bytes (base64 encoded in result)."""
        import base64
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"status": "error", "error": "File not found"}
            if resolved.stat().st_size > self.max_file_size:
                return {"status": "error", "error": "File too large"}

            content = resolved.read_bytes()
            return {
                "status": "ok",
                "content_base64": base64.b64encode(content).decode(),
                "size": len(content),
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def write(
        self,
        path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
    ) -> Dict[str, Any]:
        """Write content to file."""
        try:
            resolved = self._resolve_path(path)
            self._check_extension(resolved)

            if len(content.encode(encoding)) > self.max_file_size:
                return {"status": "error", "error": "Content too large"}

            if create_dirs:
                resolved.parent.mkdir(parents=True, exist_ok=True)

            resolved.write_text(content, encoding=encoding)
            return {
                "status": "ok",
                "path": str(resolved.relative_to(self.base_dir)),
                "size": len(content),
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def append(
        self,
        path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Append content to file."""
        try:
            resolved = self._resolve_path(path)
            self._check_extension(resolved)

            with open(resolved, "a", encoding=encoding) as f:
                f.write(content)

            return {
                "status": "ok",
                "path": str(resolved.relative_to(self.base_dir)),
                "appended": len(content),
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def delete(self, path: Union[str, Path], recursive: bool = False) -> Dict[str, Any]:
        """Delete file or directory."""
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"status": "error", "error": "Path not found"}

            if resolved.is_dir():
                if recursive:
                    shutil.rmtree(resolved)
                else:
                    resolved.rmdir()
            else:
                resolved.unlink()

            return {"status": "ok", "deleted": str(path)}
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except OSError as e:
            return {"status": "error", "error": str(e)}

    def copy(
        self,
        src: Union[str, Path],
        dst: Union[str, Path],
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """Copy file or directory."""
        try:
            src_resolved = self._resolve_path(src)
            dst_resolved = self._resolve_path(dst)

            if not src_resolved.exists():
                return {"status": "error", "error": "Source not found"}

            if src_resolved.is_dir():
                if recursive:
                    shutil.copytree(src_resolved, dst_resolved)
                else:
                    return {"status": "error", "error": "Source is directory, use recursive=True"}
            else:
                dst_resolved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_resolved, dst_resolved)

            return {"status": "ok", "src": str(src), "dst": str(dst)}
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> Dict[str, Any]:
        """Move/rename file or directory."""
        try:
            src_resolved = self._resolve_path(src)
            dst_resolved = self._resolve_path(dst)

            if not src_resolved.exists():
                return {"status": "error", "error": "Source not found"}

            dst_resolved.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_resolved), str(dst_resolved))

            return {"status": "ok", "src": str(src), "dst": str(dst)}
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # Directory Operations

    def list_dir(
        self,
        path: Union[str, Path] = ".",
        recursive: bool = False,
        pattern: Optional[str] = None,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """List directory contents."""
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"status": "error", "error": "Directory not found"}
            if not resolved.is_dir():
                return {"status": "error", "error": "Not a directory"}

            files = []
            dirs = []

            if recursive:
                items = resolved.rglob("*")
            else:
                items = resolved.iterdir()

            for item in items:
                name = item.name
                if not include_hidden and name.startswith("."):
                    continue
                if pattern and not fnmatch.fnmatch(name, pattern):
                    continue

                rel_path = str(item.relative_to(self.base_dir))
                if item.is_file():
                    files.append(rel_path)
                elif item.is_dir():
                    dirs.append(rel_path)

            return {
                "status": "ok",
                "path": str(resolved.relative_to(self.base_dir)),
                "files": sorted(files),
                "dirs": sorted(dirs),
                "total": len(files) + len(dirs),
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def mkdir(self, path: Union[str, Path], parents: bool = True) -> Dict[str, Any]:
        """Create directory."""
        try:
            resolved = self._resolve_path(path)
            resolved.mkdir(parents=parents, exist_ok=True)
            return {
                "status": "ok",
                "path": str(resolved.relative_to(self.base_dir)),
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def exists(self, path: Union[str, Path]) -> bool:
        """Check if path exists."""
        try:
            resolved = self._resolve_path(path)
            return resolved.exists()
        except PermissionError:
            return False

    def is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        try:
            resolved = self._resolve_path(path)
            return resolved.is_file()
        except PermissionError:
            return False

    def is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        try:
            resolved = self._resolve_path(path)
            return resolved.is_dir()
        except PermissionError:
            return False

    # Search Operations

    def search(
        self,
        pattern: str,
        path: Union[str, Path] = ".",
        content_pattern: Optional[str] = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """
        Search for files by name pattern and optionally content.

        Args:
            pattern: Glob pattern for filenames (e.g., "*.py")
            path: Directory to search in
            content_pattern: Optional string to search within files
            max_results: Maximum number of results
        """
        try:
            resolved = self._resolve_path(path)
            if not resolved.is_dir():
                return {"status": "error", "error": "Not a directory"}

            results = []
            for item in resolved.rglob(pattern):
                if len(results) >= max_results:
                    break

                if not item.is_file():
                    continue

                rel_path = str(item.relative_to(self.base_dir))

                if content_pattern:
                    try:
                        content = item.read_text(encoding="utf-8", errors="ignore")
                        if content_pattern in content:
                            # Find line numbers
                            lines = []
                            for i, line in enumerate(content.split("\n"), 1):
                                if content_pattern in line:
                                    lines.append(i)
                            results.append({
                                "path": rel_path,
                                "matches": lines[:10],  # First 10 matches
                            })
                    except Exception:
                        continue
                else:
                    results.append({"path": rel_path})

            return {
                "status": "ok",
                "query": pattern,
                "content_query": content_pattern,
                "results": results,
                "count": len(results),
                "truncated": len(results) >= max_results,
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def glob(self, pattern: str, path: Union[str, Path] = ".") -> List[str]:
        """Find files matching glob pattern."""
        try:
            resolved = self._resolve_path(path)
            return [
                str(p.relative_to(self.base_dir))
                for p in resolved.glob(pattern)
            ]
        except PermissionError:
            return []

    # File Info

    def info(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Get file/directory information."""
        try:
            resolved = self._resolve_path(path)
            if not resolved.exists():
                return {"status": "error", "error": "Path not found"}

            stat = resolved.stat()
            info = FileInfo(
                path=str(resolved.relative_to(self.base_dir)),
                name=resolved.name,
                size=stat.st_size,
                is_file=resolved.is_file(),
                is_dir=resolved.is_dir(),
                modified=datetime.fromtimestamp(stat.st_mtime),
                created=datetime.fromtimestamp(stat.st_ctime),
                extension=resolved.suffix,
                permissions=oct(stat.st_mode)[-3:],
            )

            return {"status": "ok", "info": info.to_dict()}
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def checksum(self, path: Union[str, Path], algorithm: str = "sha256") -> Dict[str, Any]:
        """Calculate file checksum."""
        try:
            resolved = self._resolve_path(path)
            if not resolved.is_file():
                return {"status": "error", "error": "Not a file"}

            hasher = hashlib.new(algorithm)
            with open(resolved, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)

            return {
                "status": "ok",
                "algorithm": algorithm,
                "checksum": hasher.hexdigest(),
            }
        except PermissionError as e:
            return {"status": "blocked", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # JSON Operations

    def read_json(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read JSON file."""
        result = self.read(path)
        if result["status"] != "ok":
            return result
        try:
            data = json.loads(result["content"])
            return {"status": "ok", "data": data}
        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"Invalid JSON: {e}"}

    def write_json(
        self,
        path: Union[str, Path],
        data: Any,
        indent: int = 2,
    ) -> Dict[str, Any]:
        """Write JSON file."""
        try:
            content = json.dumps(data, indent=indent, default=str)
            return self.write(path, content)
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Legacy compatibility functions
def safe_write(path: Path, content: str, base_dir: Path) -> Dict[str, str]:
    """Write to a file under base_dir to avoid escaping the sandbox."""
    fs = FileSystem(base_dir=base_dir)
    result = fs.write(path, content)
    if result["status"] == "ok":
        return {"status": "ok", "detail": result["path"]}
    return {"status": result["status"], "detail": result.get("error", "")}


def safe_read(path: Path, base_dir: Path) -> Dict[str, str]:
    """Read a file under base_dir."""
    fs = FileSystem(base_dir=base_dir)
    result = fs.read(path)
    if result["status"] == "ok":
        return {"status": "ok", "detail": result["content"]}
    elif result["status"] == "error" and "not found" in result.get("error", "").lower():
        return {"status": "missing", "detail": str(path)}
    return {"status": result["status"], "detail": result.get("error", "")}
