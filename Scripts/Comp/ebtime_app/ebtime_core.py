"""Original ebtime curve model. Source position, not speed, is stored in the graph."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path

VERSION = '0.2.0'

def mix(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(2)]

def bezier(t, a, b, c, d):
    return mix(mix(mix(a,b,t),mix(b,c,t),t),mix(mix(b,c,t),mix(c,d,t),t),t)

class Curve:
    def __init__(self, nodes):
        self.nodes = copy.deepcopy(nodes)
        self.validate()

    def validate(self):
        if not isinstance(self.nodes,list) or not 2 <= len(self.nodes) <= 64:
            raise ValueError('A curve needs 2–64 points.')
        for n in self.nodes:
            for key in ('p','l','r'):
                if len(n[key]) != 2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and abs(v)<=10 for v in n[key]):
                    raise ValueError('Invalid point or handle.')
        if self.nodes[0]['p'][0] != 0 or self.nodes[-1]['p'][0] != 1:
            raise ValueError('The graph must start at time 0 and finish at time 1.')
        for a,b in zip(self.nodes,self.nodes[1:]):
            if b['p'][0]-a['p'][0] < .0001:
                raise ValueError('Points must be ordered left to right.')
            if not a['p'][0] <= a['r'][0] <= b['l'][0] <= b['p'][0]:
                raise ValueError('Handles must remain inside their time segment.')
        return self

    @classmethod
    def points(cls, points, smooth=False):
        nodes=[{'p':list(p),'l':list(p),'r':list(p)} for p in points]
        for a,b in zip(nodes,nodes[1:]):
            a['r']=mix(a['p'],b['p'],1/3)
            b['l']=mix(a['p'],b['p'],2/3)
            if smooth:
                a['r'][1]=a['p'][1]; b['l'][1]=b['p'][1]
        return cls(nodes)

    @classmethod
    def cubic(cls,x1,y1,x2,y2):
        c=cls.points([(0,0),(1,1)])
        c.nodes[0]['r']=[x1,y1]; c.nodes[1]['l']=[x2,y2]
        return c.validate()

    def segment(self,x):
        x=max(0,min(1,x))
        for i,(a,b) in enumerate(zip(self.nodes,self.nodes[1:])):
            if x<=b['p'][0]:
                lo,hi=0.,1.
                for _ in range(35):
                    t=(lo+hi)/2
                    if bezier(t,a['p'],a['r'],b['l'],b['p'])[0]<x: lo=t
                    else: hi=t
                return i,(lo+hi)/2
        return len(self.nodes)-2,1.

    def value(self,x):
        if x<=0:return self.nodes[0]['p'][1]
        if x>=1:return self.nodes[-1]['p'][1]
        i,t=self.segment(x); a,b=self.nodes[i:i+2]
        return bezier(t,a['p'],a['r'],b['l'],b['p'])[1]

    def split(self,x):
        if len(self.nodes)>=64 or any(abs(n['p'][0]-x)<.015 for n in self.nodes):return None
        i,t=self.segment(x);a,b=self.nodes[i:i+2]
        ab=mix(a['p'],a['r'],t);bc=mix(a['r'],b['l'],t);cd=mix(b['l'],b['p'],t)
        abc=mix(ab,bc,t);bcd=mix(bc,cd,t);p=mix(abc,bcd,t)
        a['r']=ab;b['l']=cd
        self.nodes.insert(i+1,{'p':p,'l':abc,'r':bcd})
        return i+1

    def move(self,index,kind,x,y):
        n=self.nodes[index];y=max(-2,min(5,y))
        if kind=='p':
            gap=min(.015,(self.nodes[min(index+1,len(self.nodes)-1)]['p'][0]-self.nodes[max(index-1,0)]['p'][0])/3)
            x=0 if index==0 else 1 if index==len(self.nodes)-1 else max(self.nodes[index-1]['p'][0]+gap,min(self.nodes[index+1]['p'][0]-gap,x))
            dx,dy=x-n['p'][0],y-n['p'][1]
            for k in ('p','l','r'):n[k]=[n[k][0]+dx,n[k][1]+dy]
        else:n[kind]=[x,y]
        for k in ('p','l','r'):n[k][1]=max(-2,min(5,n[k][1]))
        # Keep every segment's x controls ordered; the graph is always a function of time.
        for a,b in zip(self.nodes,self.nodes[1:]):
            a['r'][0]=max(a['p'][0],min(b['p'][0],a['r'][0]))
            b['l'][0]=max(a['r'][0],min(b['p'][0],b['l'][0]))

    def delete(self,index):
        if index in (0,len(self.nodes)-1):return False
        self.nodes.pop(index)
        a,b=self.nodes[index-1:index+1]
        a['r']=mix(a['p'],b['p'],1/3);b['l']=mix(a['p'],b['p'],2/3)
        return True

    def straight(self,index):
        for j in (index-1,index):
            if 0<=j<len(self.nodes)-1:
                a,b=self.nodes[j:j+2];a['r']=mix(a['p'],b['p'],1/3);b['l']=mix(a['p'],b['p'],2/3)

    def smooth(self,index):
        n=self.nodes[index]
        for j in (index-1,index):
            if 0<=j<len(self.nodes)-1:
                a,b=self.nodes[j:j+2]
                if j==index-1:n['l']=[n['p'][0]-(n['p'][0]-a['p'][0])/3,n['p'][1]]
                else:n['r']=[n['p'][0]+(b['p'][0]-n['p'][0])/3,n['p'][1]]

    def data(self):return copy.deepcopy(self.nodes)

def presets():
    result=[]
    def add(name,cat,detail,c):result.append({'name':name,'category':cat,'detail':detail,'nodes':c.data()})
    p=Curve.points;c=Curve.cubic
    add('Normal','Essentials','Original forward playback.',p([(0,0),(1,1)]))
    for speed in (.75,.5,.25,.1):
        add(f'Slow {int(speed*100)}%','Slow motion',f'Plays at {int(speed*100)}% speed. Uses the beginning of the source range.',p([(0,0),(1,speed)]))
    add('Smooth S','Ramps','Slow start. Fast middle. Soft landing.',c(.42,0,.58,1))
    add('Ease in','Ramps','Builds speed from a gentle start.',c(.42,0,1,1))
    add('Ease out','Ramps','Starts fast, then eases to a stop.',c(0,0,.58,1))
    add('Fast · slow · fast','Ramps','A slow central passage between two fast sections.',p([(0,0),(.2,.4),(.8,.6),(1,1)]))
    add('Slow · fast · slow','Ramps','A quick burst through the middle of the shot.',p([(0,0),(.3,.1),(.7,.9),(1,1)]))
    add('Impact','Ramps','Rush into the action, then stretch the moment.',p([(0,0),(.35,.7),(1,1)]))
    add('Launch','Ramps','A slow setup with a quick exit.',p([(0,0),(.65,.25),(1,1)]))
    add('Silky ramp','Ramps','A flowing fast-to-slow ramp with soft endpoints.',p([(0,0),(.3,.65),(1,1)],True))
    add('Pulse','Ramps','Three bursts of speed, separated by slower passages.',p([(0,0),(.15,.3),(.35,.35),(.5,.65),(.7,.7),(.85,.95),(1,1)]))
    add('Reverse','Reverse','Play the selected source range backwards.',p([(0,1),(1,0)]))
    add('Reverse slow','Reverse','Play backwards at half speed from the source end.',p([(0,1),(1,.5)]))
    add('Boomerang','Reverse','Forward to the end, then back to the beginning.',p([(0,0),(.5,1),(1,0)],True))
    add('Rewind & go','Reverse','Rewind first, then play forwards.',p([(0,1),(.5,0),(1,1)],True))
    add('Triple shuttle','Reverse','Forward. Back. Forward again.',p([(0,0),(1/3,1),(2/3,0),(1,1)],True))
    add('Freeze middle','Freeze','Hold the source midpoint for the entire effect.',p([(0,.5),(1,.5)]))
    add('Hold & go','Freeze','Hold the first frame, then move forwards.',p([(0,0),(.3,0),(1,1)],True))
    add('Land & hold','Freeze','Play forwards and hold the last frame.',p([(0,0),(.7,1),(1,1)],True))
    add('Mid-shot hold','Freeze','Pause in the middle before continuing.',p([(0,0),(.35,.5),(.65,.5),(1,1)],True))
    for speed in (2,4):
        add(f'Fast {speed}×','Essentials','Needs extra source frames beyond the selected range.',p([(0,0),(1,speed)]))
    add('Soft rewind','Reverse','A gentle reverse that slows at both ends.',Curve([{'p':[0,1],'l':[0,1],'r':[.42,1]},{'p':[1,0],'l':[.58,0],'r':[1,0]}]))
    add('Long slow centre','Slow motion','A long, nearly still central section.',p([(0,0),(.15,.45),(.85,.55),(1,1)]))
    add('Double impact','Ramps','Two quick bursts with a slower passage between.',p([(0,0),(.2,.4),(.55,.5),(.75,.9),(1,1)]))
    return result


def frame_keys(curve,start,end,source_start,source_end,amount=1,travel=1):
    if not all(math.isfinite(v) for v in (start,end,source_start,source_end,amount,travel)):
        raise ValueError('Frame values must be finite.')
    if int(start)!=start or int(end)!=end or not 1<=end-start<=99999:
        raise ValueError('Choose a whole-frame render range between 2 and 100,000 frames.')
    if not 0<=amount<=1 or not .01<=travel<=10:raise ValueError('Invalid amount or playback multiplier.')
    curve.validate()
    return {f:source_start+(source_end-source_start)*(((f-start)/(end-start))*(1-amount)+curve.value((f-start)/(end-start))*amount)*travel for f in range(int(start),int(end)+1)}


def load_preset(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('format')!='ebtime-curve-v1':raise ValueError('Choose an ebtime curve file.')
    curve=Curve(data['nodes'])
    return {'name':str(data.get('name','My curve'))[:60],'category':'My presets','detail':'Your saved curve.','nodes':curve.data()}
