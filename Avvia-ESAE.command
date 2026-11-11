#!/bin/zsh
# Copyright 2026 Alessio Mattoccia
set -eu
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  print 'Run setup first: python3.12 scripts/setup.py'
  exit 1
fi
print 'Open in your browser: http://127.0.0.1:4196'
print 'To analyze a different repository, use --allow-root /path/to/repository.'
exec .venv/bin/python -m esae.cli serve "$@"
