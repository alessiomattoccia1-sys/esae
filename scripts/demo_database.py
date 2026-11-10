# Copyright 2026 Alessio Mattoccia
"""Generate a portable compilation database for ONLY the owned demo, without building."""
import json
from pathlib import Path
def create(root: Path):
    files=sorted((root/'src').glob('*.c'))+sorted((root/'src').glob('*.cpp'))
    entries=[]
    for file in files:
        rel=file.relative_to(root).as_posix();cpp=file.suffix=='.cpp'
        entries.append({'directory':'.','file':rel,'arguments':['clang++' if cpp else 'clang','-std=c++17' if cpp else '-std=c11','-Iinclude','-c',rel]})
    (root/'compile_commands.json').write_text(json.dumps(entries,indent=2)+'\n')
if __name__=='__main__': create(Path(__file__).resolve().parents[1]/'demo')
