import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts/Comp/ebtime_app'))
from ebtime_core import Curve,presets,frame_keys,load_preset
from ebtime_bridge import apply_lua,tools_in

class Curves(unittest.TestCase):
    def test_all_presets(self):
        self.assertEqual(len(presets()),28)
        for p in presets():
            c=Curve(p['nodes']);keys=frame_keys(c,100,200,100,200)
            self.assertEqual(len(keys),101)
            self.assertAlmostEqual(keys[100],100+c.value(0)*100)
            self.assertAlmostEqual(keys[200],100+c.value(1)*100)
    def test_known_frames(self):
        for name,ends in [('Normal',(100,200)),('Reverse',(200,100)),('Slow 50%',(100,150)),('Freeze middle',(150,150))]:
            c=Curve(next(p for p in presets() if p['name']==name)['nodes']);keys=frame_keys(c,100,200,100,200)
            self.assertEqual((keys[100],keys[200]),ends)
    def test_split_preserves_shape(self):
        c=Curve.cubic(.42,0,.58,1);before=[c.value(i/100) for i in range(101)]
        c.split(.37);c.validate()
        for i,y in enumerate(before):self.assertAlmostEqual(c.value(i/100),y,places=8)
    def test_drag_stays_valid(self):
        c=Curve.points([(0,0),(.3,.1),(.7,.9),(1,1)])
        rng=random.Random(42)
        for _ in range(300):
            c.move(rng.randrange(4),rng.choice(['p','l','r']),rng.uniform(-1,2),rng.uniform(-3,5));c.validate()
    def test_delete_keeps_endpoints(self):
        c=Curve.points([(0,0),(.5,.5),(1,1)])
        self.assertFalse(c.delete(0));self.assertTrue(c.delete(1));self.assertEqual(len(c.nodes),2);c.validate()
    def test_invalid_inputs(self):
        c=Curve.points([(0,0),(1,1)])
        for a,b in [(0,0),(2,1),(0,100000),(.5,10)]:
            with self.assertRaises(ValueError):frame_keys(c,a,b,0,100)
        with self.assertRaises(ValueError):Curve.cubic(.9,0,.1,1)
        with self.assertRaises(ValueError):frame_keys(c,0,10,float('nan'),100)
    def test_import_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'curve.ebtime';p.write_text(json.dumps({'format':'ebtime-curve-v1','name':'test','nodes':Curve.points([(0,1),(1,0)]).data()}));self.assertEqual(load_preset(p)['name'],'test')
            p.write_text('{}')
            with self.assertRaises(ValueError):load_preset(p)
    def test_amount_zero_is_normal(self):
        c=Curve.points([(0,1),(1,0)])
        self.assertEqual(frame_keys(c,100,200,100,200,0)[100],100)
        self.assertEqual(frame_keys(c,100,200,100,200,0)[200],200)
    def test_bridge_protects_cleanup(self):
        state={'nodes':Curve.points([(0,0),(1,1)]).data(),'source_start':100,'source_end':200,'amount':100,'travel':1,'quality':2}
        code=apply_lua('ebtime "test"',state,100,200)
        self.assertIn('comp:Unlock()',code);self.assertIn('comp:EndUndo(ok)',code);self.assertIn('pcall(function()',code)
        self.assertIn('[100]={ 100',code)
        state['quality']=9
        with self.assertRaises(ValueError):apply_lua('ebtime',state,100,200)

if __name__=='__main__':unittest.main()
