#!/bin/zsh
# Copyright 2026 Alessio Mattoccia
set -eu
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  print 'Esegui prima: python3.12 scripts/setup.py'
  exit 1
fi
print 'Apri nel browser: http://127.0.0.1:4196'
print 'Per analizzare un altro repository, usa --allow-root /percorso/repository.'
exec .venv/bin/python -m esae.cli serve "$@"
