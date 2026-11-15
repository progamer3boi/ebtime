#!/usr/bin/env python3
"""Install ebtime for the current user. Run with Python 3, with Resolve closed."""
from pathlib import Path
import argparse
import json
import platform
import shutil
import os


def default_root():
    system = platform.system()
    if system == 'Windows':
        return Path(os.environ['APPDATA']) / 'Blackmagic Design/DaVinci Resolve/Support/Fusion'
    if system == 'Darwin':
        return Path.home() / 'Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion'
    return Path.home() / '.local/share/DaVinciResolve/Fusion'


def install(root):
    source = Path(__file__).resolve().parent
    editor = root / 'Scripts/Comp/ebtime Editor.lua'
    effect = root / 'Templates/Edit/Effects/ebtime/ebtime.setting'
    macro = root / 'Macros/ebtime.setting'
    for path in (editor, effect, macro):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + '.bak'))
    shutil.copy2(source / 'Scripts/Comp/ebtime Editor.lua', editor)
    text = (source / 'Templates/Edit/Effects/ebtime/ebtime.setting').read_text()
    # Bake in the installed script location: avoid ambiguous Fusion Scripts: maps.
    lua_path = editor.resolve().as_posix()
    if ']==]' in lua_path:
        raise ValueError('Unsupported install path containing ]==]')
    code = f"comp:RunScript([==[{lua_path}]==])"
    lines = text.splitlines()
    lines = [('       BTNCS_Execute = ' + json.dumps(code, ensure_ascii=False))
             if 'BTNCS_Execute =' in line else line for line in lines]
    text = '\n'.join(lines) + '\n'
    effect.write_text(text)
    macro.write_text(text)
    print(f'Installed ebtime to {root}\nRestart Resolve. See README.md for use and limitations.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fusion-root', type=Path, default=None,
                        help='Override the Resolve user Fusion folder')
    args = parser.parse_args()
    install(args.fusion_root or default_root())
