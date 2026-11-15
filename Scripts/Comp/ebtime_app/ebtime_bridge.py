"""Resolve-side bridge. Qt runs in a separate Python process, never inside Resolve."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import tempfile
from ebtime_core import Curve, frame_keys


def lua_quote(value):
    # JSON string escapes used here are valid in Lua; ensure_ascii=False avoids \u escapes.
    return json.dumps(str(value),ensure_ascii=False)


def tools_in(comp):
    found=[]
    def values(obj):return obj.values() if isinstance(obj,dict) else obj or []
    def scan(tools):
        for tool in values(tools):
            attrs=tool.GetAttrs() or {};reg=attrs.get('TOOLS_RegID','');name=attrs.get('TOOLS_Name','')
            if reg in ('MacroOperator','GroupOperator'):
                kids=tool.GetChildrenList() or {}
                if any((k.GetAttrs() or {}).get('TOOLS_Name')=='EBTime_Retime' for k in values(kids)):
                    found.append((name,tool))
            elif name=='EBTime_Retime':found.append((name,tool))
    scan(comp.GetToolList(False))
    return found


def apply_lua(target,state,first,last):
    curve=Curve(state['nodes'])
    keys=frame_keys(curve,first,last,state['source_start'],state['source_end'],state['amount']/100,state['travel'])
    quality=int(state.get('quality',2))
    if quality not in (0,1,2):raise ValueError('Invalid interpolation mode.')
    values=','.join(f'[{f}]={{ {v:.12g}, Flags={{Linear=true}} }}' for f,v in keys.items())
    serialized=json.dumps(state,ensure_ascii=False,separators=(',',':'))
    return f'''
local group=comp:FindTool({lua_quote(target)})
if not group then error('ebtime: effect no longer exists. Reopen the editor.') end
local rt=nil
if group.Name=='EBTime_Retime' then rt=group else
 for _,child in pairs(group:GetChildrenList() or {{}}) do
  if child.Name=='EBTime_Retime' then rt=child;break end
 end
end
if not rt then error('ebtime: could not find the time stretcher.') end
comp:StartUndo('ebtime: apply curve')
comp:Lock()
local ok,err=pcall(function()
 local spline=comp:BezierSpline()
 spline:SetKeyFrames({{{values}}},true)
 rt.SourceTime:SetExpression(nil)
 rt.SourceTime=spline
 rt.InterpolateBetweenFrames={quality}
 rt.ClampEdges=1
 group:SetData('ebtime.State',{lua_quote(serialized)})
end)
comp:Unlock()
comp:EndUndo(ok)
if not ok then error(err) end
'''


def run(comp,appdir):
    if comp is None:raise RuntimeError('Open a Fusion composition and select ebtime first.')
    appdir=Path(appdir)
    config=json.loads((appdir/'runtime.json').read_text(encoding='utf-8'))
    python=Path(config['python'])
    if not python.is_file():raise RuntimeError('ebtime Python runtime is missing. Run Install Windows.cmd again.')
    found=tools_in(comp)
    if not found:raise RuntimeError('Add the ebtime effect to this composition first.')
    active=comp.ActiveTool
    active_name=(active.GetAttrs() or {}).get('TOOLS_Name','') if active else ''
    target=next((name for name,_ in found if name==active_name),found[0][0])
    attrs=comp.GetAttrs() or {};first=int(attrs.get('COMPN_RenderStart',0));last=int(attrs.get('COMPN_RenderEnd',100))
    session={'first':first,'last':last,'targets':[name for name,_ in found],'target':target}
    group=next(t for n,t in found if n==target)
    saved=group.GetData('ebtime.State')
    if saved:
        try:session['state']=json.loads(saved)
        except (ValueError,TypeError):pass
    # Unique temp folder: stale results and concurrent sessions cannot cross-apply.
    with tempfile.TemporaryDirectory(prefix='ebtime-') as tmp:
        request=Path(tmp)/'session.json';response=Path(tmp)/'response.json';log=Path(tmp)/'editor.log'
        request.write_text(json.dumps(session),encoding='utf-8')
        kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        env=os.environ.copy()
        # Resolve sets Qt variables for its own Qt runtime. They must not leak into Qt6.
        for key in ('QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','PYTHONHOME','PYTHONPATH'):env.pop(key,None)
        with log.open('w',encoding='utf-8') as output:
            result=subprocess.run([str(python),str(appdir/'app.py'),'--session',str(request),'--response',str(response)],stdout=output,stderr=subprocess.STDOUT,env=env,**kwargs)
        if result.returncode:
            raise RuntimeError('Editor could not open. Re-run the installer.\n'+log.read_text(encoding='utf-8',errors='replace')[-3000:])
        if not response.exists():return False
        state=json.loads(response.read_text(encoding='utf-8'))
        target=state.get('target',target)
        if target not in session['targets']:raise ValueError('Choose an effect from this composition.')
        comp.Execute(apply_lua(target,state,first,last))
        print('ebtime: curve applied. Use Resolve Undo to restore the previous timing.')
        return True
