-- ebtime 0.1.0 | Fusion UIManager editor. No third-party retimer required.
local fusion = fu or fusion
local comp = comp or (fusion and fusion:GetCurrentComp())
if not comp then print('ebtime: open a Fusion composition first.'); return end
local ui = fusion.UIManager
if not ui or not bmd or not bmd.UIDispatcher then
 print('ebtime: this Resolve installation does not expose Fusion UIManager. Use a Resolve/Fusion edition with scripting UI support.'); return
end
local disp = bmd.UIDispatcher(ui)
local function P(name, category, description, points, smooth)
 return {name=name, category=category, description=description, points=points, smooth=smooth}
end
local presets = {
 P('Normal / reset','Beginner','Original forward playback.',{{0,0},{1,1}}),
 P('Slow motion 50%','Slow motion','Half speed. Consumes half the selected source range.',{{0,0},{1,.5}}),
 P('Slow motion 25%','Slow motion','Quarter speed. Optical flow interpolates missing frames.',{{0,0},{1,.25}}),
 P('Slow motion 10%','Slow motion','Extreme slow motion. Clean high-frame-rate footage works best.',{{0,0},{1,.1}}),
 P('Fast 2x','Beginner','Double speed. Needs twice the source handles.',{{0,0},{1,2}}),
 P('Fast 4x','Beginner','Four times speed. Needs extra source handles.',{{0,0},{1,4}}),
 P('Reverse','Reverse','Plays the selected source range backwards.',{{0,1},{1,0}}),
 P('Reverse slow 50%','Reverse','Reverse from the end at half speed.',{{0,1},{1,.5}}),
 P('Freeze middle','Freeze','Holds the middle source frame throughout.',{{0,.5},{1,.5}}),
 P('Freeze then go','Freeze','Holds first frame, then moves forward.',{{0,0},{.3,0},{1,1}},true),
 P('Go then freeze','Freeze','Moves forward, then holds the final frame.',{{0,0},{.7,1},{1,1}},true),
 P('Mid-shot freeze','Freeze','Stops in the middle before continuing.',{{0,0},{.35,.5},{.65,.5},{1,1}},true),
 P('Ease in','Curves','Starts slowly and accelerates. Source-position graph is convex.',nil),
 P('Ease out','Curves','Starts quickly and decelerates.',nil),
 P('Smooth S curve','Curves','Slow start, fast middle, slow finish.',nil),
 P('Fast-slow-fast','Ramps','Quick edges with a slow middle passage.',{{0,0},{.2,.4},{.8,.6},{1,1}}),
 P('Slow-fast-slow','Ramps','Slow edges with a fast central burst.',{{0,0},{.3,.1},{.7,.9},{1,1}}),
 P('Impact slowdown','Ramps','Rushes into an impact then slows down.',{{0,0},{.35,.7},{1,1}}),
 P('Launch ramp','Ramps','Slow setup followed by a fast exit.',{{0,0},{.65,.25},{1,1}}),
 P('Boomerang','Reverse','Forward to the end, then backwards.',{{0,0},{.5,1},{1,0}},true),
 P('Reverse then forward','Reverse','Backwards to the beginning, then forwards.',{{0,1},{.5,0},{1,1}},true),
 P('Triple shuttle','Reverse','Forward, backward, forward.',{{0,0},{.333,1},{.667,0},{1,1}},true),
 P('Stutter steps','Advanced','Eight frame holds with hard time jumps.',{{0,0},{1,1}}),
 P('Pulse ramp','Advanced','Alternates fast passages and slow passages.',{{0,0},{.15,.3},{.35,.35},{.5,.65},{.7,.7},{.85,.95},{1,1}}),
 P('Custom Bezier','Advanced','Edit the four Bezier controls. X controls timing; Y controls source position.',nil)
}
local targets = {}
local function scan(list)
 for _,t in pairs(list or {}) do
  local a=t:GetAttrs()
  if a.TOOLS_RegID=='MacroOperator' or a.TOOLS_RegID=='GroupOperator' then
   local kids=t:GetChildrenList() or {}
   local rt
   for _,k in pairs(kids) do if k.Name=='EBTime_Retime' then rt=k end end
   if rt then targets[#targets+1]={name=t.Name,tool=rt} else scan(kids) end
  elseif t.Name=='EBTime_Retime' then
   targets[#targets+1]={name=t.Name,tool=t}
  end
 end
end
scan(comp:GetToolList(false))
if #targets==0 then print('ebtime: drag ebtime into this composition, then open the editor.'); return end
local attrs=comp:GetAttrs()
local first=attrs.COMPN_RenderStart or 0
local last=attrs.COMPN_RenderEnd or first+100
local function spin(id,value,min,max)
 return ui.DoubleSpinBox{ID=id,Value=value,Minimum=min,Maximum=max,SingleStep=.05,Decimals=3}
end
local win=disp:AddWindow({ID='EBTimeEditor',WindowTitle='ebtime | Retiming editor',Geometry={180,100,960,740}},
 ui.VGroup{Spacing=10,
  ui.Label{Text='ebtime',StyleSheet='font-size:28px; font-weight:bold; color:#80e8db;'},
  ui.HGroup{ui.Label{Text='Effect instance',Weight=0},ui.ComboBox{ID='Target'}},
  ui.HGroup{
   ui.VGroup{Weight=.34,ui.Label{Text='PRESET LIBRARY'},ui.ComboBox{ID='Category'},ui.Tree{ID='Library',HeaderHidden=true,ColumnCount=1}},
   ui.VGroup{Weight=.66,
    ui.Label{ID='Title',Text='Normal / reset',StyleSheet='font-size:19px;'},
    ui.Label{ID='Description',WordWrap=true},
    ui.TextEdit{ID='Graph',ReadOnly=true,Font={Family='monospace',PixelSize=13},Weight=1},
    ui.Label{Text='Horizontal: output time  |  Vertical: source position\nRising = forward; flat = freeze; falling = reverse.',WordWrap=true},
    ui.Label{ID='Stats',WordWrap=true},
   }
  },
  ui.HGroup{ui.Label{Text='Source start (frame)'},spin('Start',first,-1000000,1000000),ui.Label{Text='Source end (frame)'},spin('End',last,-1000000,1000000)},
  ui.HGroup{ui.Label{Text='Curve amount'},spin('Amount',1,0,1),ui.Label{Text='Source travel'},spin('Travel',1,.001,10)},
  ui.Label{Text='Bezier controls — enabled for Ease in / Ease out / S curve / Custom Bezier'},
  ui.HGroup{ui.Label{Text='X1'},spin('X1',.25,0,1),ui.Label{Text='Y1'},spin('Y1',.1,-2,3),ui.Label{Text='X2'},spin('X2',.75,0,1),ui.Label{Text='Y2'},spin('Y2',.9,-2,3)},
  ui.HGroup{ui.Label{Text='Interpolation'},ui.ComboBox{ID='Quality'},ui.Label{Text='Output range: composition render range',Weight=1}},
  ui.Label{ID='Status',Text='Select a preset, inspect the graph, then Apply. Apply replaces this effect’s time animation.',WordWrap=true},
  ui.HGroup{ui.Button{ID='Reset',Text='Reset controls'},ui.Button{ID='Close',Text='Close'},ui.Button{ID='Apply',Text='Apply to effect'}}
 })
local it=win:GetItems()
for _,t in ipairs(targets) do it.Target:AddItem(t.name) end
local active=comp.ActiveTool
for i,t in ipairs(targets) do if active and active.Name==t.name then it.Target.CurrentIndex=i-1 end end
for _,s in ipairs({'All','Beginner','Slow motion','Curves','Ramps','Reverse','Freeze','Advanced'}) do it.Category:AddItem(s) end
for _,s in ipairs({'Nearest frame','Frame blend','Optical flow'}) do it.Quality:AddItem(s) end
it.Quality.CurrentIndex=2
local current=1
local busy=false
local function cubic(t,a,b) return 3*(1-t)^2*t*a+3*(1-t)*t*t*b+t^3 end
local function curve(x)
 local p=presets[current]
 local y
 if not p.points then
  local lo,hi=0,1
  for _=1,28 do local mid=(lo+hi)/2; if cubic(mid,it.X1.Value,it.X2.Value)<x then lo=mid else hi=mid end end
  y=cubic((lo+hi)/2,it.Y1.Value,it.Y2.Value)
 elseif p.name=='Stutter steps' then y=math.min(7,math.floor(x*8))/7
 else
  local a,b=p.points[1],p.points[#p.points]
  for j=2,#p.points do if x<=p.points[j][1] then a,b=p.points[j-1],p.points[j]; break end end
  local u=math.max(0,math.min(1,(x-a[1])/(b[1]-a[1])))
  if p.smooth then u=u*u*(3-2*u) end
  y=a[2]+(b[2]-a[2])*u
 end
 return (x+(y-x)*it.Amount.Value)*it.Travel.Value
end
local function refresh()
 if busy then return end
 local p=presets[current]
 it.Title.Text=p.name; it.Description.Text=p.description
 local custom=not p.points
 for _,id in ipairs({'X1','Y1','X2','Y2'}) do it[id].Enabled=custom end
 local width,height=56,15
 local samples,low,high={},0,1
 for col=0,width-1 do local y=curve(col/(width-1)); samples[col]=y; low=math.min(low,y);high=math.max(high,y) end
 local lines={string.format('Source position   %.2f',high)}
 for row=0,height-1 do
  local s=''
  for col=0,width-1 do
   local r=math.floor((high-samples[col])/(high-low)*(height-1)+.5)
   s=s..(r==row and '*' or (row==height-1 and '-' or (col==0 and '|' or ' ')))
  end
  lines[#lines+1]=s
 end
 lines[#lines+1]=string.format('%.2f                         Output time ->',low)
 it.Graph.PlainText=table.concat(lines,'\n')
 local duration=math.max(1,last-first)
 local minSpeed,maxSpeed=math.huge,-math.huge
 for j=1,200 do
  local speed=(curve(j/200)-curve((j-1)/200))*200*(it.End.Value-it.Start.Value)/duration
  minSpeed=math.min(minSpeed,speed);maxSpeed=math.max(maxSpeed,speed)
 end
 it.Stats.Text=string.format('Sampled speed: %.2fx to %.2fx | Source frames: %.1f to %.1f',minSpeed,maxSpeed,it.Start.Value+low*(it.End.Value-it.Start.Value),it.Start.Value+high*(it.End.Value-it.Start.Value))
end
local function selectPreset(index)
 current=index; busy=true
 local values={.25,.1,.75,.9}
 if presets[index].name=='Ease in' then values={.42,0,1,1}
 elseif presets[index].name=='Ease out' then values={0,0,.58,1}
 elseif presets[index].name=='Smooth S curve' then values={.65,0,.35,1} end
 for j,id in ipairs({'X1','Y1','X2','Y2'}) do it[id].Value=values[j] end
 busy=false;refresh()
end
local function populate()
 it.Library:Clear()
 local filter=it.Category.CurrentText
 for i,p in ipairs(presets) do
  if filter=='All' or filter==p.category then
   local row=it.Library:NewItem();row.Text[0]=p.name; it.Library:AddTopLevelItem(row)
  end
 end
end
function win.On.Library.CurrentItemChanged(ev)
 if ev.item then for index,p in ipairs(presets) do if p.name==ev.item.Text[0] then selectPreset(index);break end end end
end
function win.On.Category.CurrentIndexChanged() populate() end
for _,id in ipairs({'Start','End','Amount','Travel','X1','Y1','X2','Y2'}) do win.On[id].ValueChanged=refresh end
function win.On.Reset.Clicked()
 busy=true;it.Start.Value=first;it.End.Value=last;it.Amount.Value=1;it.Travel.Value=1;it.Quality.CurrentIndex=2;busy=false;selectPreset(1)
end
function win.On.Apply.Clicked()
 local target=targets[it.Target.CurrentIndex+1]
 if not target then return end
 if last<=first then it.Status.Text='Set a composition render range of at least two frames.';return end
 local count=math.floor(last-first)+1
 if count>100000 then it.Status.Text='Render range exceeds 100,000 frames. Shorten it before applying.';return end
 comp:StartUndo('ebtime: '..presets[current].name)
 comp:Lock()
 local ok,err=pcall(function()
  local spline=comp:BezierSpline()
  local keys={}
  for frame=first,last do
   keys[frame]={it.Start.Value+(it.End.Value-it.Start.Value)*curve((frame-first)/(last-first)),Flags={Linear=true}}
  end
  target.tool.SourceTime:SetExpression(nil)
  target.tool.SourceTime=spline
  spline:SetKeyFrames(keys,true)
  target.tool.InterpolateBetweenFrames=it.Quality.CurrentIndex
  target.tool.ClampEdges=1
 end)
 comp:Unlock();comp:EndUndo(ok)
 if ok then it.Status.Text='Applied '..presets[current].name..' to '..target.name..'. Preview the clip; Undo restores the previous timing.'
 else it.Status.Text='Apply failed: '..tostring(err)..'. Use Undo if any controls changed.' end
end
function win.On.EBTimeEditor.Close() disp:ExitLoop() end
function win.On.Close.Clicked() disp:ExitLoop() end
populate();selectPreset(1);win:Show();disp:RunLoop();win:Hide()
