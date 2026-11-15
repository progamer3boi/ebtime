"""Run from Resolve → Fusion → Scripts → Comp → ebtime Editor."""
from pathlib import Path
import sys
import traceback


def _ebtime_main():
    # Installer writes an absolute app path here. Source fallback is for manual installs.
    appdir=Path(__file__).resolve().parent/'ebtime_app'
    sys.path.insert(0,str(appdir))
    try:
        from ebtime_bridge import run
        host_comp=globals().get('comp')
        if host_comp is None:
            fusion=globals().get('fu') or globals().get('fusion')
            if fusion is not None:host_comp=fusion.GetCurrentComp()
        run(host_comp,appdir)
    except Exception:
        print('ebtime could not finish. Open the Fusion console for details:')
        traceback.print_exc()
    finally:
        sys.path.remove(str(appdir))

_ebtime_main()
