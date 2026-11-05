"""Operator-selected executables, bounded execution, no shell or network."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import platform
import signal
import subprocess
import sys
import time
import math

@dataclass
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    duration: float
    error: str | None = None

def run_tool(command: list[str], work: Path, timeout=45, sandbox=True, output_limit=2_000_000, read_roots=()) -> ProcessResult:
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    command = [str(x) for x in command]
    executable = Path(command[0])
    if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
        return ProcessResult(-1, '', '', 0, 'Configured executable missing or not executable')
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work), 'TMPDIR': str(work), 'LANG': 'C', 'LC_ALL': 'C', 'OTEL_SDK_DISABLED': 'true'}
    invocation = [sys.executable, '-I', str(Path(__file__).with_name('safeexec.py')), str(math.ceil(timeout + 5)), *command]
    if sandbox and platform.system() == 'Darwin':
        readable = [str(work.parent), *(str(p) for p in read_roots), str(executable.parent.parent), str(Path(sys.executable).parent.parent), str(Path(sys.executable).resolve().parent.parent),
                    '/usr', '/bin', '/sbin', '/System', '/Library/Developer', '/Library/Apple', '/opt/homebrew', '/dev', '/private/var/db/dyld']
        # macOS 27 dyld also opens the root directory itself. This literal is
        # not a subpath grant: files beneath / remain denied unless listed below.
        profile = '(version 1)\n(deny default)\n(allow process*)\n(allow sysctl-read)\n(allow mach-lookup)\n(allow file-read-metadata)\n(allow file-read* (literal "/"))\n'
        profile += '(allow file-read* ' + ' '.join('(subpath ' + json.dumps(x) + ')' for x in readable) + ')\n'
        profile += '(allow file-write* (subpath ' + json.dumps(str(work)) + ') (literal "/dev/null"))\n'
        profile += '(allow file-read* (literal ' + json.dumps(str(Path(__file__).with_name('safeexec.py'))) + '))\n'
        p = work / 'sandbox.sb'; p.write_text(profile)
        invocation = ['/usr/bin/sandbox-exec', '-f', str(p), *invocation]
    started = time.monotonic(); error = None
    outpath, errpath = work / 'stdout.log', work / 'stderr.log'
    with outpath.open('wb') as out, errpath.open('wb') as err:
        try:
            child = subprocess.Popen(invocation, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True, shell=False)
        except OSError as e:
            return ProcessResult(-1, '', str(e), 0, 'Process could not start')
        try:
            while child.poll() is None:
                if time.monotonic() - started > timeout:
                    error = 'Process timeout; process group terminated'
                elif outpath.stat().st_size + errpath.stat().st_size > output_limit:
                    error = 'Process output limit exceeded; process group terminated'
                if error:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    break
                time.sleep(.05)
            child.wait(timeout=5)
        except BaseException:
            # Ctrl+C/termination of the explicit local job must not orphan a
            # native analyzer. This does not relax any analyzer boundary.
            if child.poll() is None:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            child.wait(timeout=5)
            raise
    stdout = outpath.read_bytes()[:output_limit].decode('utf-8', errors='replace')
    stderr = errpath.read_bytes()[:output_limit].decode('utf-8', errors='replace')
    if not error and outpath.stat().st_size + errpath.stat().st_size > output_limit: error = 'Process output limit exceeded'
    return ProcessResult(child.returncode, stdout, stderr, round(time.monotonic() - started, 3), error)
