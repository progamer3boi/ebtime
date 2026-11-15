#!/usr/bin/env python3
"""Install ebtime for the current user. Close Resolve first. Python 3.10+ required."""
from pathlib import Path
import argparse
import json
import platform
import shutil
import os
import subprocess
import sys
import venv


def default_root():
    if platform.system()=='Windows':return Path(os.environ['APPDATA'])/'Blackmagic Design/DaVinci Resolve/Support/Fusion'
    if platform.system()=='Darwin':return Path.home()/'Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion'
    return Path.home()/'.local/share/DaVinciResolve/Fusion'


def install(root,skip_dependencies=False):
    root=Path(root).resolve();source=Path(__file__).resolve().parent
    if sys.version_info<(3,10):raise RuntimeError('Use Python 3.10 or newer (python.org, not the Microsoft Store stub).')
    envdir=root/'ebtime/runtime'
    python=envdir/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not skip_dependencies:
        if not python.exists():
            print('Creating an isolated ebtime Python runtime…',flush=True);venv.EnvBuilder(with_pip=True).create(envdir)
        print('Installing the Qt editor. The first install needs internet and may take a few minutes…',flush=True)
        subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check','PySide6>=6.6,<7'],check=True)
        subprocess.run([str(python),'-c','from PySide6.QtWidgets import QApplication; print("Qt runtime ready")'],check=True)
    else:python=Path(sys.executable)
    def write(path,text):
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():shutil.copy2(path,path.with_suffix(path.suffix+'.bak'))
        path.write_text(text,encoding='utf-8')
    appdir=root/'Scripts/Comp/ebtime_app'
    for p in (source/'Scripts/Comp/ebtime_app').glob('*.py'):write(appdir/p.name,p.read_text(encoding='utf-8'))
    write(appdir/'runtime.json',json.dumps({'python':str(python)},indent=2))
    entry=root/'Scripts/Comp/ebtime Editor.py'
    entry_text=(source/'Scripts/Comp/ebtime Editor.py').read_text(encoding='utf-8')
    entry_text=entry_text.replace("Path(__file__).resolve().parent/'ebtime_app'",'Path('+repr(str(appdir))+')')
    write(entry,entry_text)
    script_path=entry.as_posix()
    if ']==]' in script_path:raise ValueError('Unsupported install path containing ]==]')
    command=f'comp:RunScript([==[{script_path}]==])'
    write(root/'Scripts/Comp/ebtime Editor.lua','-- ebtime by @epicbloxfx\n'+command+'\n')
    text=(source/'Templates/Edit/Effects/ebtime/ebtime.setting').read_text(encoding='utf-8')
    text='\n'.join('       BTNCS_Execute = '+json.dumps(command,ensure_ascii=False) if 'BTNCS_Execute =' in line else line for line in text.splitlines())+'\n'
    write(root/'Templates/Edit/Effects/ebtime/ebtime.setting',text);write(root/'Macros/ebtime.setting',text)
    print(f'\nebtime installed: {root}\nRestart Resolve. Select ebtime in Fusion and choose Open Editor.\nUse the Python script in Fusion > Scripts > Comp if the button cannot launch.\nBranding: @epicbloxfx on YouTube',flush=True)
    return python,appdir


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fusion-root',type=Path);p.add_argument('--skip-dependencies',action='store_true',help='For development only: use current Python without installing Qt');p.add_argument('--designer',action='store_true',help='Open the installed standalone curve designer');args=p.parse_args()
    python,appdir=install(args.fusion_root or default_root(),args.skip_dependencies)
    if args.designer:subprocess.run([str(python),str(appdir/'app.py')],check=True)

if __name__=='__main__':main()
