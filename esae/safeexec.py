"""Isolated resource setup; no repository-controlled code is imported."""
import os
import resource
import sys
cpu = max(1, min(int(sys.argv[1]), 600))
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
resource.setrlimit(resource.RLIMIT_FSIZE, (8_000_000, 8_000_000))
resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
os.execve(sys.argv[2], sys.argv[2:], dict(os.environ))
