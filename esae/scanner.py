"""Bounded repository inventory and immutable source evidence snapshot."""
from pathlib import Path
from dataclasses import dataclass
import fnmatch
import hashlib
import os
import stat

EXTENSIONS = {".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"}
DEFAULT_EXCLUDES = (".git", ".venv", "node_modules", "build", "dist", "vendor", "third_party", "external", "generated", ".local", ".toolchain")


class InputError(ValueError):
    pass


def no_symlink(path: Path) -> Path:
    """Reject symlinks in every existing component, not only the final filename."""
    path = Path(os.path.abspath(path))
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise InputError(f"Symbolic link is not allowed: {part.name}")
    return path


def validate_root(value: str | Path, allowed: tuple[Path, ...]) -> Path:
    root = no_symlink(Path(value).expanduser())
    try:
        root = root.resolve(strict=True)
    except OSError as e:
        raise InputError("Repository path does not exist") from e
    if not root.is_dir() or root == Path(root.anchor):
        raise InputError("Choose a repository directory, not a filesystem root")
    if not any(root == a or root.is_relative_to(a) for a in allowed):
        raise InputError("Repository is outside operator-authorized roots; restart with --allow-root PATH")
    return root


def read_regular(path: Path, limit: int) -> bytes:
    no_symlink(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise InputError(f"Not a bounded regular file: {path.name}")
        with os.fdopen(fd, "rb", closefd=False) as f:
            data = f.read(limit + 1)
        if len(data) > limit:
            raise InputError(f"File grew beyond limit: {path.name}")
        return data
    finally:
        os.close(fd)


@dataclass
class Inventory:
    root: Path
    files: dict[str, str]
    metadata: list[dict]
    directories: list[str]
    excluded: list[dict]
    build_systems: list[str]
    database: Path | None

    def public(self):
        return {"file_count": len(self.files), "lines": sum(x["lines"] for x in self.metadata),
                "nonblank_lines": sum(x["nonblank_lines"] for x in self.metadata),
                "line_count_method": "physical source lines; includes comments; nonblank also reported",
                "files": self.metadata, "directories": self.directories, "excluded": self.excluded,
                "build_systems": self.build_systems, "compilation_database": bool(self.database)}


def inventory(root: Path, excludes=DEFAULT_EXCLUDES, max_files=1000, max_bytes=50_000_000) -> Inventory:
    files, meta, excluded, directories, build_systems = {}, [], [], [], []
    total = visits = 0
    db = None
    for base, dirs, names in os.walk(root, followlinks=False):
        if len(directories)>=5000:raise InputError('Directory traversal limit exceeded')
        relbase = Path(base).relative_to(root)
        directories.append(relbase.as_posix())
        for d in list(dirs):
            p = Path(base) / d
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or any(fnmatch.fnmatch(d, x) or fnmatch.fnmatch(rel, x) for x in excludes):
                dirs.remove(d)
                excluded.append({"path": rel, "reason": "symlink" if p.is_symlink() else "configured_directory"})
        for name in sorted(names):
            visits += 1
            if visits > 20000 or len(directories) > 5000:
                raise InputError("Repository traversal limit exceeded")
            p = Path(base) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                excluded.append({"path": rel, "reason": "symlink"})
                continue
            if name in ("CMakeLists.txt", "Makefile", "makefile", "GNUmakefile"):
                build_systems.append(rel)
            if name == "compile_commands.json" and relbase == Path('.'):
                db = p
            if p.suffix.lower() not in EXTENSIONS:
                continue
            if any(fnmatch.fnmatch(rel, x) or fnmatch.fnmatch(name, x) for x in excludes):
                excluded.append({"path": rel, "reason": "configured_file"})
                continue
            data = read_regular(p, 2_000_000)
            if b'\0' in data:
                excluded.append({"path": rel, "reason": "binary"})
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                excluded.append({"path": rel, "reason": "not_utf8"})
                continue
            total += len(data)
            if total > max_bytes or len(files) >= max_files:
                raise InputError("Source snapshot limit exceeded (1000 files / 50 MB by default)")
            lines = text.splitlines()
            files[rel] = text
            meta.append({"path": rel, "bytes": len(data), "lines": len(lines),
                         "nonblank_lines": sum(bool(x.strip()) for x in lines),
                         "sha256": hashlib.sha256(data).hexdigest()})
    if db is None:
        candidate = root / "build" / "compile_commands.json"
        if candidate.exists():
            no_symlink(candidate)
            db = candidate
    if not files:
        raise InputError("No readable C/C++ source files remain after exclusions")
    return Inventory(root, files, sorted(meta, key=lambda x: x["path"]), sorted(directories), excluded, build_systems, db)


def snapshot(inv: Inventory, destination: Path):
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name, text in inv.files.items():
        p = destination / name
        p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        p.chmod(0o400)
