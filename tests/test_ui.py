"""Run with PySide6 installed. QT_QPA_PLATFORM=offscreen supports headless checks."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts/Comp/ebtime_app'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from app import Editor

app=QApplication.instance() or QApplication([])
class Interface(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old_appdata=os.environ.get('APPDATA');os.environ['APPDATA']=self.tmp.name;self.output=Path(self.tmp.name)/'response.json'
        self.w=Editor({'first':100,'last':200,'targets':['ebtime','ebtime2'],'target':'ebtime'},str(self.output));self.w.show();app.processEvents()
    def tearDown(self):
        self.w.close();app.processEvents();self.tmp.cleanup()
        if self.old_appdata is None:os.environ.pop('APPDATA',None)
        else:os.environ['APPDATA']=self.old_appdata
    def test_search_and_categories(self):
        self.w.search.setText('reverse');self.assertGreaterEqual(len(self.w.cards),1)
        self.w.search.setText('no-such-preset');self.assertEqual(len(self.w.cards),0)
        self.w.search.clear();self.w.category.setCurrentText('Freeze');self.assertEqual(len(self.w.cards),4)
    def test_drag_point_and_undo(self):
        g=self.w.graph;start=g.screen(g.curve.nodes[1]['p']).toPoint();end=g.screen([1,.75]).toPoint()
        QTest.mousePress(g,Qt.LeftButton,pos=start);QTest.mouseMove(g,end);QTest.mouseRelease(g,Qt.LeftButton,pos=end)
        self.assertAlmostEqual(g.curve.nodes[1]['p'][1],.75,places=2);self.w.undo();self.assertEqual(g.curve.nodes[1]['p'][1],1);self.w.redo();self.assertAlmostEqual(g.curve.nodes[1]['p'][1],.75,places=2)
    def test_add_delete_and_handles(self):
        g=self.w.graph;point=g.screen([.5,.5]).toPoint();QTest.mouseDClick(g,Qt.LeftButton,pos=point)
        self.assertEqual(len(g.curve.nodes),3)
        start=g.screen(g.curve.nodes[1]['r']).toPoint();end=g.screen([.8,.7]).toPoint()
        QTest.mousePress(g,Qt.LeftButton,pos=start);QTest.mouseMove(g,end);QTest.mouseRelease(g,Qt.LeftButton,pos=end);g.curve.validate()
        self.w.point_action('delete');self.assertEqual(len(g.curve.nodes),2)
    def test_speed_view_read_only(self):
        before=self.w.graph.curve.data();self.w.view(True);QTest.mouseDClick(self.w.graph,Qt.LeftButton,pos=QPoint(200,150));self.assertEqual(self.w.graph.curve.data(),before)
    def test_settings_undo(self):
        self.w.travel.setValue(2);self.w.commit_travel();self.w.undo();self.assertEqual(self.w.travel.value(),1)
        self.w.source_end.setValue(300);self.w.commit_source();self.w.undo();self.assertEqual(self.w.source_end.value(),200)
        self.w.quality.setCurrentIndex(0);self.w.undo();self.assertEqual(self.w.quality.currentIndex(),2)
    def test_apply_response(self):
        self.w.apply();state=json.loads(self.output.read_text());self.assertEqual(state['target'],'ebtime');self.assertEqual(state['source_start'],100)
    def test_close_cancels(self):self.w.close();self.assertFalse(self.output.exists())
    def test_small_window_no_overlap(self):
        self.w.resize(1000,690);app.processEvents()
        self.assertGreaterEqual(self.w.graph.height(),220)
        self.assertGreater(self.w.hint.geometry().top(),self.w.graph.geometry().bottom())
        self.w.show_advanced(True);app.processEvents();self.assertGreater(self.w.hint.geometry().top(),self.w.graph.geometry().bottom())
        self.assertTrue(self.w.apply_btn.isVisible())

if __name__=='__main__':unittest.main()
