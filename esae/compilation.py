# Copyright 2026 Alessio Mattoccia
"""Parse compilation databases as data. Never execute a compiler/build command.

Only source language, standard, macros and in-snapshot include directories survive.
Compiler programs, outputs and all other flags are ignored or rejected explicitly.
"""
import json
import re
import shlex
from pathlib import Path
from .scanner import Inventory, InputError, no_symlink, read_regular

FORBIDDEN = ("@", "-fplugin", "-load", "-Xclang", "-Xpreprocessor", "-vfsoverlay", "-ivfsoverlay", "-include", "-imacros", "-resource-dir", "-fmodule", "--config", "-config", "-isysroot", "--sysroot", "-specs", "--gcc-toolchain", "-B")


def sanitize_arguments(args: list[str], directory: Path, inv: Inventory, snap: Path):
    if not args or not all(isinstance(a, str) and len(a) < 8192 and '\0' not in a for a in args):
        raise InputError("Invalid compilation arguments")
    safe, ignored = [], []
    i = 1  # compiler path is data, never used
    while i < len(args):
        a = args[i]
        if any(a.startswith(x) for x in FORBIDDEN):
            raise InputError(f"Unsafe compilation flag rejected: {a[:80]}")
        if a in ("-I", "-iquote", "-isystem") or a.startswith('-I'):
            flag = a if a in ("-I", "-iquote", "-isystem") else '-I'
            value = args[i + 1] if a == flag else a[2:]
            i += 2 if a == flag else 1
            include = no_symlink(directory / value).resolve()
            if not include.is_relative_to(inv.root) or not include.is_dir():
                raise InputError("Include directory outside repository or missing; not authorized")
            relative = include.relative_to(inv.root)
            mapped = snap / relative
            # Empty include directories are intentionally represented as absent.
            if mapped.is_dir():
                safe += [flag, str(mapped)]
            else:
                ignored.append("include directory contains no captured sources: " + relative.as_posix())
            continue
        if a in ('-D', '-U') or a.startswith(('-D', '-U')):
            flag = a[:2]
            value = args[i + 1] if a == flag else a[2:]
            i += 2 if a == flag else 1
            if not re.fullmatch(r'[A-Za-z_]\w*(?:=[^\r\n]{0,500})?', value):
                raise InputError("Invalid macro in compilation database")
            safe.append(flag + value)
            continue
        if a.startswith('-std=') and re.fullmatch(r'-std=(?:gnu\+\+|c\+\+|gnu|c)\d{2,3}', a):
            safe.append(a)
        elif a == '-x':
            if i + 1 >= len(args) or args[i + 1] not in ('c', 'c++'):
                raise InputError("Unsupported source language")
            safe += [a, args[i + 1]]
            i += 1
        elif a in ('-o', '-MF', '-MT', '-MQ'):
            i += 1  # discard output filenames; no file is opened
        elif a not in ('-c',) and not a.endswith(('.c', '.cpp', '.cc', '.cxx')):
            ignored.append(a[:120])
        i += 1
    return safe, ignored


def prepare_database(inv: Inventory, snap: Path, out: Path, system_flags=()):
    entries, errors, ignored = [], [], []
    if inv.database:
        raw = json.loads(read_regular(inv.database, 4_000_000))
        if not isinstance(raw, list) or len(raw) > 2000:
            raise InputError("Compilation database must be a list of at most 2000 entries")
        seen = set()
        for item in raw:
            if not isinstance(item, dict):
                errors.append("Invalid compilation database entry")
                continue
            try:
                directory = no_symlink(inv.root / item.get('directory', '.')).resolve(strict=True)
                if not directory.is_relative_to(inv.root):
                    raise InputError("Compilation working directory is outside repository")
                original = no_symlink(directory / item['file']).resolve(strict=True)
                rel = original.relative_to(inv.root).as_posix()
                if rel not in inv.files or original.suffix.lower() not in ('.c', '.cpp', '.cc', '.cxx'):
                    raise InputError("Compilation file is not an inventoried translation unit")
                if rel in seen:
                    errors.append(f"{rel}: additional build configuration omitted (first configuration only)")
                    continue
                args = item.get('arguments')
                if args is None:
                    args = shlex.split(item['command'])
                args, notes = sanitize_arguments(args, directory, inv, snap)
                ignored.extend({"file": rel, "ignored": x} for x in notes)
                entries.append({"directory": str(snap), "file": str(snap / rel),
                                "arguments": ['clang++' if original.suffix != '.c' else 'clang', *system_flags, *args, '-c', str(snap / rel)]})
                seen.add(rel)
            except (KeyError, ValueError, OSError, IndexError, TypeError) as e:
                errors.append(f"Entry rejected: {str(e)[:200]}")
        covered = {Path(e['file']).relative_to(snap).as_posix() for e in entries}
        for rel in inv.files:
            if Path(rel).suffix in ('.c', '.cpp', '.cc', '.cxx') and rel not in covered:
                errors.append(f"{rel}: no accepted compilation configuration; not analyzed by clang-tidy")
    else:
        errors.append("No compile_commands.json: clang-tidy uses explicit standalone C11/C++17 fallback; target flags are not reconstructed")
        for rel in inv.files:
            if Path(rel).suffix in ('.c', '.cpp', '.cc', '.cxx'):
                lang = 'c11' if rel.endswith('.c') else 'c++17'
                includes = ['-I', str(snap)]
                if (snap / 'include').is_dir():
                    includes += ['-I', str(snap / 'include')]
                entries.append({"directory": str(snap), "file": str(snap / rel),
                                "arguments": ['clang', *system_flags, '-std=' + lang, *includes, '-c', str(snap / rel)]})
    out.mkdir(exist_ok=True, parents=True)
    (out / 'compile_commands.json').write_text(json.dumps(entries, indent=2))
    return entries, errors, ignored
