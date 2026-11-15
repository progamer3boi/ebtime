"""ebtime visual editor — @epicbloxfx. Run directly to explore without Resolve."""
from __future__ import annotations
import argparse
import copy
import json
import math
import os
from pathlib import Path
import sys

from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,
 QHBoxLayout,QGridLayout,QScrollArea,QLineEdit,QComboBox,QDoubleSpinBox,QSpinBox,QSlider,
 QCheckBox,QFileDialog,QInputDialog,QMessageBox,QSizePolicy,QButtonGroup)
from ebtime_core import Curve, presets, frame_keys, load_preset, VERSION

BG='#101216'; PANEL='#181b21'; FIELD='#22262e'; TEXT='#edf0f4'; MUTED='#939aa8'; LINE='#30353f'
ACCENTS={'Mint':'#9de4c4','Lavender':'#c5b4f4','Amber':'#edc784'}

def color(s):return QColor(s)

def path_for(curve,rect,low=0,high=1,amount=1,travel=1,speed=False,speed_factor=1):
    path=QPainterPath()
    for j in range(241):
        x=j/240
        if speed:
            a=max(0,x-.001);b=min(1,x+.001)
            y=((curve.value(b)-curve.value(a))/(b-a)*amount+1-amount)*travel*speed_factor
        else:y=(x*(1-amount)+curve.value(x)*amount)*travel
        pt=QPointF(rect.left()+x*rect.width(),rect.bottom()-(y-low)/(high-low)*rect.height())
        if j==0:path.moveTo(pt)
        else:path.lineTo(pt)
    return path

class PresetCard(QPushButton):
    def __init__(self,preset,accent,parent=None):
        super().__init__(parent);self.preset=preset;self.accent=accent;self.selected=False
        self.setMinimumSize(116,105);self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor);self.setToolTip(preset['detail'])
        self.setAccessibleName(preset['name']+' preset')
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(color(self.accent if self.selected else LINE),1.3 if self.selected else 1))
        p.setBrush(color('#242e2c' if self.selected else PANEL));p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),8,8)
        r=QRectF(14,12,self.width()-28,54)
        p.setPen(QPen(color('#343b44'),1));p.drawLine(r.bottomLeft(),r.bottomRight())
        c=Curve(self.preset['nodes']);values=[c.value(i/100) for i in range(101)]
        lo=min(0,min(values));hi=max(1,max(values));p.setPen(QPen(color(self.accent if self.selected else '#a3afbf'),2))
        p.drawPath(path_for(c,r,lo,hi))
        p.setFont(QFont('Segoe UI',9));p.setPen(color(TEXT));p.drawText(QRectF(12,73,self.width()-24,23),Qt.AlignLeft|Qt.AlignVCenter,self.preset['name'])

class Graph(QWidget):
    edited=Signal();gesture=Signal();selection=Signal();cursor=Signal(float,float)
    def __init__(self):
        super().__init__();self.curve=Curve.points([(0,0),(1,1)]);self.accent=ACCENTS['Mint']
        self.amount=1;self.travel=1;self.speed_factor=1;self.speed=False;self.selected=0;self.drag=None;self.hover=None
        self.low=-.12;self.high=1.12;self.snap=True;self.guides=True;self.playhead=None
        self.setMinimumSize(360,220);self.setMouseTracking(True);self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName('Time graph. Drag points or handles. Double-click to add a point. Delete removes a selected interior point.')
    def rect_graph(self):return QRectF(62,28,max(1,self.width()-90),max(1,self.height()-82))
    def fit(self):
        vals=[self.curve.value(i/200)*self.travel for i in range(201)]
        vals += [n[k][1] for n in self.curve.nodes for k in ('p','l','r')]
        lo=min(0,min(vals));hi=max(1,max(vals));pad=(hi-lo)*.12
        self.low=lo-pad;self.high=hi+pad;self.update()
    def screen(self,point):
        r=self.rect_graph();return QPointF(r.left()+point[0]*r.width(),r.bottom()-(point[1]-self.low)/(self.high-self.low)*r.height())
    def model(self,pos):
        r=self.rect_graph();return [(pos.x()-r.left())/r.width(),self.low+(r.bottom()-pos.y())/r.height()*(self.high-self.low)]
    def handles(self):
        if self.speed:return []
        result=[]
        for i,n in enumerate(self.curve.nodes):result.append((i,'p',self.screen(n['p'])))
        if self.selected is not None and self.selected<len(self.curve.nodes):
            i=self.selected;n=self.curve.nodes[i]
            if i>0:result.append((i,'l',self.screen(n['l'])))
            if i<len(self.curve.nodes)-1:result.append((i,'r',self.screen(n['r'])))
        return result
    def hit(self,pos):
        for i,k,p in reversed(self.handles()):
            if math.hypot(p.x()-pos.x(),p.y()-pos.y())<12:return i,k
        return None
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.fillRect(self.rect(),color('#14171c'));r=self.rect_graph()
        lo,hi=self.low,self.high
        if self.speed:
            speeds=[]
            for j in range(201):
                x=j/200;a=max(0,x-.001);b=min(1,x+.001)
                speeds.append(((self.curve.value(b)-self.curve.value(a))/(b-a)*self.amount+1-self.amount)*self.travel*self.speed_factor)
            lo=min(-.3,min(speeds)-.3);hi=max(1.3,max(speeds)+.3)
        p.setFont(QFont('Segoe UI',9))
        for j in range(5):
            x=r.left()+r.width()*j/4
            p.setPen(QPen(color('#292e37'),1));p.drawLine(QPointF(x,r.top()),QPointF(x,r.bottom()))
            p.setPen(color(MUTED));p.drawText(QRectF(x-24,r.bottom()+10,48,22),Qt.AlignCenter,f'{j*25}%')
        raw=(hi-lo)/5;power=10**math.floor(math.log10(raw));step=min((v*power for v in (1,2,2.5,5,10)),key=lambda v:abs(v-raw))
        tick=math.ceil(lo/step)*step
        while tick<=hi:
            y=r.bottom()-(tick-lo)/(hi-lo)*r.height()
            p.setPen(QPen(color('#292e37'),1));p.drawLine(QPointF(r.left(),y),QPointF(r.right(),y))
            p.setPen(color(MUTED));p.drawText(QRectF(0,y-10,51,20),Qt.AlignRight|Qt.AlignVCenter,f'{tick:.1f}×' if self.speed else f'{tick*100:.0f}%')
            tick+=step
        p.drawText(QRectF(r.left(),2,r.width(),18),Qt.AlignLeft|Qt.AlignVCenter,'PLAYBACK SPEED' if self.speed else 'SOURCE POSITION')
        p.drawText(QRectF(r.left(),self.height()-22,r.width(),18),Qt.AlignCenter,'OUTPUT TIME')
        p.save();p.setClipRect(r.adjusted(-7,-7,7,7))
        if self.guides and not self.speed:
            p.setPen(QPen(color('#48505d'),1,Qt.DashLine));p.drawLine(self.screen([0,0]),self.screen([1,1]))
        effective=path_for(self.curve,r,lo,hi,self.amount,self.travel,self.speed,self.speed_factor)
        if not self.speed:
            fill=QPainterPath(effective);fill.lineTo(r.right(),r.bottom());fill.lineTo(r.left(),r.bottom());fill.closeSubpath()
            tint=color(self.accent);tint.setAlpha(13);p.fillPath(fill,tint)
        if not self.speed and (self.amount!=1 or self.travel!=1):
            p.setPen(QPen(color('#6e7786'),1,Qt.DashLine));p.drawPath(path_for(self.curve,r,self.low,self.high))
        p.setPen(QPen(color(self.accent),2.6));p.drawPath(effective)
        if not self.speed:
            if self.selected is not None and self.selected<len(self.curve.nodes):
                n=self.curve.nodes[self.selected];p.setPen(QPen(color('#73877d'),1,Qt.DashLine))
                if self.selected>0:p.drawLine(self.screen(n['p']),self.screen(n['l']))
                if self.selected<len(self.curve.nodes)-1:p.drawLine(self.screen(n['p']),self.screen(n['r']))
            for i,k,pos in self.handles():
                if k=='p':
                    p.setBrush(color(self.accent if i==self.selected else BG));p.setPen(QPen(color(self.accent),2));p.drawEllipse(pos,5.5,5.5)
                else:
                    p.setBrush(color(PANEL));p.setPen(QPen(color(self.accent),1.5));p.drawRect(QRectF(pos.x()-4,pos.y()-4,8,8))
        if self.playhead is not None:
            x=r.left()+self.playhead*r.width();p.setPen(QPen(color('#f3f4f6'),1));p.drawLine(QPointF(x,r.top()),QPointF(x,r.bottom()))
            if not self.speed:
                y=(self.playhead*(1-self.amount)+self.curve.value(self.playhead)*self.amount)*self.travel
                pos=self.screen([self.playhead,y]);p.setBrush(color(self.accent));p.drawEllipse(pos,5,5)
        p.restore()
    def mousePressEvent(self,e):
        if e.button()!=Qt.LeftButton or self.speed:return
        self.setFocus();hit=self.hit(e.position())
        if hit:
            self.selected=hit[0];self.drag=hit;self.gesture.emit();self.selection.emit();self.update()
    def mouseMoveEvent(self,e):
        x,y=self.model(e.position());self.cursor.emit(x,y)
        if self.drag:
            i,k=self.drag
            if self.snap and not (e.modifiers()&Qt.AltModifier):
                x=round(x/0.025)*.025;y=round(y/0.025)*.025
            self.curve.move(i,k,x,y);self.edited.emit();self.update()
        else:self.setCursor(Qt.OpenHandCursor if self.hit(e.position()) else Qt.CrossCursor if not self.speed else Qt.ArrowCursor)
    def mouseReleaseEvent(self,e):self.drag=None
    def mouseDoubleClickEvent(self,e):
        if self.speed:return
        x,y=self.model(e.position())
        if 0<x<1:
            self.gesture.emit();idx=self.curve.split(x)
            if idx is not None:self.selected=idx;self.edited.emit();self.selection.emit();self.update()
    def keyPressEvent(self,e):
        if e.key() in (Qt.Key_Delete,Qt.Key_Backspace) and self.selected is not None:
            self.gesture.emit()
            if self.curve.delete(self.selected):self.selected=None;self.edited.emit();self.selection.emit();self.update()
        elif e.key()==Qt.Key_F:self.fit()
        else:super().keyPressEvent(e)

class Editor(QMainWindow):
    def __init__(self,session=None,response=None):
        super().__init__();self.session=session or {};self.response=response;self.accent=ACCENTS['Mint']
        self.library=presets();self.cards=[];self.history=[];self.future=[];self.loading=False;self.modified=False
        self.current_name='Smooth S';self.detail='Slow start. Fast middle. Soft landing.'
        self.userdir=Path(os.environ.get('APPDATA',str(Path.home()/'.config')))/'ebtime';self.savedir=self.userdir/'presets'
        self.settings_path=self.userdir/'preferences.json';self.first=self.session.get('first',0);self.last=self.session.get('last',100)
        self.setWindowTitle('ebtime — @epicbloxfx');self.resize(1220,820);self.setMinimumSize(1000,690)
        self.setStyleSheet(self.styles())
        root=QWidget();self.setCentralWidget(root);outer=QVBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        header=QFrame();header.setObjectName('header');hl=QHBoxLayout(header);hl.setContentsMargins(24,18,24,18)
        brand=QLabel('ebtime');brand.setObjectName('brand');hl.addWidget(brand)
        by=QLabel('BY @EPICBLOXFX  /  YOUTUBE');by.setObjectName('muted');hl.addWidget(by);hl.addStretch()
        badge=QLabel('RESOLVE SESSION' if response else 'CURVE DESIGNER');badge.setObjectName('badge');hl.addWidget(badge)
        self.theme=QComboBox();self.theme.addItems(ACCENTS);self.theme.setToolTip('Accent colour');self.theme.currentTextChanged.connect(self.set_theme);hl.addWidget(self.theme)
        outer.addWidget(header)
        body=QHBoxLayout();body.setContentsMargins(0,0,0,0);body.setSpacing(0);outer.addLayout(body,1)
        side=QFrame();side.setObjectName('sidebar');side.setFixedWidth(302);sl=QVBoxLayout(side);sl.setContentsMargins(18,22,18,14);sl.setSpacing(12)
        self.label(sl,'Find your timing','section');self.label(sl,'Choose a shape. Make it yours.','muted')
        self.search=QLineEdit();self.search.setPlaceholderText('Search presets…');self.search.setClearButtonEnabled(True);self.search.textChanged.connect(self.populate);sl.addWidget(self.search)
        self.category=QComboBox();self.category.addItems(['All presets','Essentials','Slow motion','Ramps','Reverse','Freeze','My presets']);self.category.currentTextChanged.connect(self.populate);sl.addWidget(self.category)
        self.scroller=QScrollArea();self.scroller.setWidgetResizable(True);self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.scroller.setFrameShape(QFrame.NoFrame)
        self.cardroot=QWidget();self.grid=QGridLayout(self.cardroot);self.grid.setContentsMargins(0,0,4,0);self.grid.setSpacing(8);self.scroller.setWidget(self.cardroot);sl.addWidget(self.scroller,1)
        row=QHBoxLayout();self.button(row,'Import',self.import_curve);self.button(row,'Save preset',self.save_preset);sl.addLayout(row)
        body.addWidget(side)
        shell=QVBoxLayout();shell.setContentsMargins(25,20,25,18);shell.setSpacing(14);body.addLayout(shell,1)
        self.content=QWidget();self.content.setMinimumHeight(645);right=QVBoxLayout(self.content);right.setContentsMargins(0,0,4,0);right.setSpacing(12)
        self.content_scroll=QScrollArea();self.content_scroll.setWidgetResizable(True);self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.content_scroll.setFrameShape(QFrame.NoFrame);self.content_scroll.setWidget(self.content);shell.addWidget(self.content_scroll,1)
        title=QHBoxLayout();self.title=self.label(title,self.current_name,'title');title.addStretch()
        self.undo_btn=self.button(title,'Undo',self.undo);self.redo_btn=self.button(title,'Redo',self.redo);right.addLayout(title)
        self.subtitle=self.label(right,self.detail,'muted');self.subtitle.setWordWrap(True)
        toolbar=QHBoxLayout();self.position_btn=QPushButton('Position');self.speed_btn=QPushButton('Speed');self.position_btn.setCheckable(True);self.speed_btn.setCheckable(True)
        self.view_group=QButtonGroup(self);self.view_group.addButton(self.position_btn);self.view_group.addButton(self.speed_btn);self.position_btn.setChecked(True)
        toolbar.addWidget(self.position_btn);toolbar.addWidget(self.speed_btn);self.position_btn.clicked.connect(lambda:self.view(False));self.speed_btn.clicked.connect(lambda:self.view(True))
        toolbar.addStretch();self.button(toolbar,'Fit graph',self.fit);self.play_btn=self.button(toolbar,'Preview curve',self.play);right.addLayout(toolbar)
        self.graph=Graph();self.graph.gesture.connect(self.push_history);self.graph.edited.connect(self.on_edit);self.graph.selection.connect(self.sync_point);self.graph.cursor.connect(self.cursor_readout)
        right.addWidget(self.graph,1)
        self.hint=self.label(right,'Drag a point or square handle. Double-click the curve to add a point.','muted')
        self.hint.setWordWrap(True)
        controls=QHBoxLayout();self.label(controls,'Point','muted');self.point_x=self.number(0,0,100,1);self.point_y=self.number(0,-200,500,1)
        self.point_x.setSuffix('% time');self.point_y.setSuffix('% source');controls.addWidget(self.point_x);controls.addWidget(self.point_y)
        self.point_x.editingFinished.connect(self.edit_point);self.point_y.editingFinished.connect(self.edit_point)
        self.button(controls,'Smooth',lambda:self.point_action('smooth'));self.button(controls,'Straight',lambda:self.point_action('straight'));self.delete_btn=self.button(controls,'Delete',lambda:self.point_action('delete'));controls.addStretch();right.addLayout(controls)
        options=QHBoxLayout();self.snap=QCheckBox('Snap to grid');self.snap.setChecked(True);self.snap.toggled.connect(self.set_snap);options.addWidget(self.snap)
        self.guides=QCheckBox('Show original timing');self.guides.setChecked(True);self.guides.toggled.connect(self.set_guides);options.addWidget(self.guides);options.addStretch();self.readout=self.label(options,'','muted');right.addLayout(options)
        self.stats=self.label(right,'','stats');self.stats.setWordWrap(True)
        tune=QHBoxLayout();self.label(tune,'Curve strength','muted');self.amount=QSlider(Qt.Horizontal);self.amount.setRange(0,100);self.amount.setValue(100);tune.addWidget(self.amount,1);self.amount_label=self.label(tune,'100%','muted')
        self.label(tune,'Playback multiplier','muted');self.travel=self.number(1,.01,10,.05);self.travel.setSuffix('×');tune.addWidget(self.travel);right.addLayout(tune)
        self.amount.sliderPressed.connect(self.push_history);self.amount.actionTriggered.connect(lambda action:self.push_history() if not self.amount.isSliderDown() else None);self.amount.valueChanged.connect(self.tune);self.travel.editingFinished.connect(self.commit_travel)
        self.advanced_btn=QPushButton('▸  Advanced');self.advanced_btn.setCheckable(True);self.advanced_btn.toggled.connect(self.show_advanced);right.addWidget(self.advanced_btn,0,Qt.AlignLeft)
        self.advanced=QFrame();al=QVBoxLayout(self.advanced);al.setContentsMargins(0,0,0,0)
        targetrow=QHBoxLayout();self.label(targetrow,'Effect instance','muted');self.target=QComboBox();self.target.addItems(self.session.get('targets',['Curve designer']));self.target.setCurrentText(self.session.get('target','Curve designer'));targetrow.addWidget(self.target,1);al.addLayout(targetrow)
        frames=QHBoxLayout();self.label(frames,'Source frames','muted');self.source_start=self.number(self.first,-1000000,1000000,1);self.source_end=self.number(self.last,-1000000,1000000,1)
        frames.addWidget(self.source_start);frames.addWidget(self.source_end);self.label(frames,'Interpolation','muted');self.quality=QComboBox();self.quality.addItems(['Nearest frame','Frame blend','Optical flow']);self.quality.setCurrentIndex(2);frames.addWidget(self.quality);al.addLayout(frames)
        self.source_values=(self.first,self.last);self.source_start.editingFinished.connect(self.commit_source);self.source_end.editingFinished.connect(self.commit_source)
        self.label(al,'Source frames use Fusion coordinates. Out-of-range footage may hold the edge frame.','muted').setWordWrap(True)
        self.advanced.hide();right.addWidget(self.advanced)
        footer=QHBoxLayout();self.status=self.label(footer,f'Output: frames {self.first}–{self.last}  ·  {VERSION} preview','muted');self.status.setWordWrap(True);footer.addStretch()
        self.button(footer,'Reset',self.reset);self.apply_btn=self.button(footer,'Apply to clip' if response else 'Export curve',self.apply,primary=True);shell.addLayout(footer)
        self.last_quality=2;self.quality.currentIndexChanged.connect(self.commit_quality)
        self.timer=QTimer(self);self.timer.setInterval(16);self.timer.timeout.connect(self.tick);self.phase=0
        QShortcut(QKeySequence.Undo,self,activated=self.undo);QShortcut(QKeySequence.Redo,self,activated=self.redo)
        QShortcut(QKeySequence('Ctrl+S'),self,activated=self.save_preset)
        self.load_saved();self.populate();self.choose(next(p for p in self.library if p['name']=='Smooth S'),remember=False)
        self.load_preferences();self.history=[];self.future=[];self.sync_history()
        saved=self.session.get('state')
        if saved:
            try:self.restore(saved)
            except (ValueError,KeyError,TypeError):pass
    @staticmethod
    def styles():
        return f'''
        QWidget {{background:{BG};color:{TEXT};font-family:"Segoe UI";font-size:12px;}}
        QFrame#header {{border-bottom:1px solid {LINE};}}
        QFrame#sidebar {{background:{PANEL};border-right:1px solid {LINE};}}
        QFrame#sidebar QWidget {{background:transparent;}}
        QLabel#brand {{font-size:30px;font-weight:700;letter-spacing:-1px;}}
        QLabel#title {{font-size:24px;font-weight:600;}}
        QLabel#section {{font-size:17px;font-weight:600;}}
        QLabel#muted {{color:{MUTED};}}
        QLabel#badge {{color:#a8b8ad;font-size:10px;padding:6px 9px;border:1px solid {LINE};border-radius:5px;}}
        QLabel#stats {{background:{PANEL};border:1px solid {LINE};border-radius:6px;padding:10px;color:#c6ced9;}}
        QPushButton {{background:{FIELD};border:1px solid {LINE};border-radius:5px;padding:7px 12px;}}
        QPushButton:hover {{background:#303640;border-color:#697384;}}
        QPushButton:pressed {{background:#3b434f;}}
        QPushButton:checked {{background:#313b36;border-color:#809a8a;}}
        QPushButton:disabled {{color:#555d69;background:{PANEL};}}
        QPushButton#primary {{background:#9de4c4;color:#14231c;border:0;font-weight:600;padding:10px 20px;}}
        QPushButton#primary:hover {{background:#b5f2d7;}}
        QLineEdit,QComboBox,QDoubleSpinBox {{background:{FIELD};border:1px solid {LINE};border-radius:5px;padding:7px;selection-background-color:#526d61;}}
        QLineEdit:focus,QComboBox:focus,QDoubleSpinBox:focus {{border-color:#91b6a2;}}
        QComboBox QAbstractItemView {{background:{PANEL};selection-background-color:#34483e;}}
        QScrollArea {{background:transparent;border:0;}}
        QScrollBar:vertical {{background:{PANEL};width:7px;border:0;}}
        QScrollBar::handle:vertical {{background:#404854;border-radius:3px;min-height:24px;}}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;}}
        QSlider::groove:horizontal {{height:4px;background:#353c47;border-radius:2px;}}
        QSlider::handle:horizontal {{width:13px;margin:-5px 0;background:#a9d8c0;border-radius:6px;}}
        QCheckBox {{spacing:6px;color:{MUTED};}}
        QToolTip {{background:{FIELD};color:{TEXT};border:1px solid {LINE};padding:6px;}}
        '''
    @staticmethod
    def label(layout,text,kind=None):
        w=QLabel(text)
        if kind:w.setObjectName(kind)
        layout.addWidget(w);return w
    @staticmethod
    def button(layout,text,callback,primary=False):
        b=QPushButton(text);b.setCursor(Qt.PointingHandCursor);b.clicked.connect(callback)
        if primary:b.setObjectName('primary')
        layout.addWidget(b);return b
    @staticmethod
    def number(value,low,high,step):
        w=QDoubleSpinBox();w.setRange(low,high);w.setDecimals(2);w.setSingleStep(step);w.setValue(value);w.setMinimumWidth(95);return w
    def populate(self,*args):
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.cards=[];query=self.search.text().strip().lower();category=self.category.currentText()
        matches=[p for p in self.library if (category=='All presets' or p['category']==category) and query in (p['name']+' '+p['detail']).lower()]
        for i,p in enumerate(matches):
            card=PresetCard(p,self.accent);card.selected=p['name']==self.current_name and not self.modified;card.clicked.connect(lambda checked=False,p=p:self.choose(p));self.grid.addWidget(card,i//2,i%2);self.cards.append(card)
        if not matches:self.grid.addWidget(QLabel('No presets found.'),0,0,1,2)
        self.grid.setRowStretch((len(matches)+1)//2,1)
    def state(self):
        return {'nodes':self.graph.curve.data(),'name':self.current_name,'detail':self.detail,'amount':self.amount.value(),'travel':self.travel.value(),'source_start':self.source_start.value(),'source_end':self.source_end.value(),'quality':self.quality.currentIndex(),'modified':self.modified,'target':self.target.currentText()}
    def restore(self,state):
        self.loading=True
        try:
            self.graph.curve=Curve(state['nodes']);self.current_name=state['name'];self.detail=state.get('detail','Your custom timing.')
            self.amount.setValue(state.get('amount',100));self.travel.setValue(state.get('travel',1));self.source_start.setValue(state.get('source_start',self.first));self.source_end.setValue(state.get('source_end',self.last));self.quality.setCurrentIndex(state.get('quality',2));self.modified=state.get('modified',False);self.graph.selected=0
            if state.get('target') in self.session.get('targets',[]):self.target.setCurrentText(state['target'])
        finally:self.loading=False
        self.source_values=(self.source_start.value(),self.source_end.value());self.last_quality=self.quality.currentIndex()
        self.title.setText(self.current_name+(' · edited' if self.modified else ''));self.subtitle.setText(self.detail);self.tune();self.graph.fit();self.sync_point();self.populate()
    def push_history(self):
        if self.loading:return
        self.history.append(self.state());self.history=self.history[-100:];self.future=[];self.sync_history()
    def sync_history(self):self.undo_btn.setEnabled(bool(self.history));self.redo_btn.setEnabled(bool(self.future))
    def undo(self):
        if not self.history:return
        self.future.append(self.state());self.restore(self.history.pop());self.sync_history()
    def redo(self):
        if not self.future:return
        self.history.append(self.state());self.restore(self.future.pop());self.sync_history()
    def choose(self,preset,remember=True):
        if remember:self.push_history()
        self.graph.curve=Curve(preset['nodes']);self.current_name=preset['name'];self.detail=preset['detail'];self.modified=False;self.graph.selected=0
        self.loading=True;self.amount.setValue(100);self.travel.setValue(1);self.loading=False
        self.title.setText(self.current_name);self.subtitle.setText(self.detail);self.tune();self.graph.fit();self.sync_point()
        for card in self.cards:card.selected=card.preset['name']==self.current_name;card.update()
    def on_edit(self):
        self.modified=True;self.title.setText(self.current_name+' · edited');self.sync_point();self.update_stats()
        for c in self.cards:c.selected=False;c.update()
    def sync_point(self):
        i=self.graph.selected;valid=i is not None and i<len(self.graph.curve.nodes)
        for w in (self.point_x,self.point_y,self.delete_btn):w.setEnabled(valid and not self.graph.speed)
        if valid:
            p=self.graph.curve.nodes[i]['p'];self.point_x.setValue(p[0]*100);self.point_y.setValue(p[1]*100)
            self.point_x.setEnabled(i not in (0,len(self.graph.curve.nodes)-1) and not self.graph.speed)
            self.delete_btn.setEnabled(i not in (0,len(self.graph.curve.nodes)-1) and not self.graph.speed)
    def edit_point(self):
        if self.graph.selected is None:return
        p=self.graph.curve.nodes[self.graph.selected]['p']
        if abs(self.point_x.value()/100-p[0])<.0001 and abs(self.point_y.value()/100-p[1])<.0001:return
        self.push_history();self.graph.curve.move(self.graph.selected,'p',self.point_x.value()/100,self.point_y.value()/100);self.on_edit();self.graph.update()
    def point_action(self,action):
        if self.graph.selected is None or self.graph.speed:return
        self.push_history();getattr(self.graph.curve,action)(self.graph.selected)
        if action=='delete':self.graph.selected=None
        self.on_edit();self.graph.update()
    def tune(self,*args):
        if self.loading:return
        self.graph.amount=self.amount.value()/100;self.graph.travel=self.travel.value();self.amount_label.setText(f'{self.amount.value()}%');self.graph.update();self.update_stats()
    def record_previous(self,**changes):
        if self.loading:return
        state=self.state();state.update(changes);self.history.append(state);self.history=self.history[-100:];self.future=[];self.sync_history()
    def commit_travel(self):
        if self.travel.value()!=self.graph.travel:self.record_previous(travel=self.graph.travel)
        self.tune();self.graph.fit()
    def commit_source(self):
        values=(self.source_start.value(),self.source_end.value())
        if values!=self.source_values:self.record_previous(source_start=self.source_values[0],source_end=self.source_values[1]);self.source_values=values
        self.update_stats()
    def commit_quality(self,index):
        if self.loading:return
        if index!=self.last_quality:self.record_previous(quality=self.last_quality);self.last_quality=index
        self.update_stats()
    def update_stats(self):
        s=self.source_start.value();e=self.source_end.value();duration=max(1,self.last-self.first);self.graph.speed_factor=(e-s)/duration;c=self.graph.curve;a=self.amount.value()/100;t=self.travel.value()
        ys=[(x/200*(1-a)+c.value(x/200)*a)*t for x in range(201)]
        speeds=[(ys[i+1]-ys[i])*200*(e-s)/duration for i in range(200)]
        text=f'{len(c.nodes)} points   ·   Speed {min(speeds):.2f}× to {max(speeds):.2f}×'
        if min(ys)<0 or max(ys)>1:text+='   ·   Needs source handles'
        elif self.quality.currentIndex()==2:text+='   ·   Optical flow'
        self.stats.setText(text);self.graph.update()
    def cursor_readout(self,x,y):
        self.readout.setText(f'{max(0,min(1,x))*100:.0f}% time  /  {y*100:.0f}% source' if not self.graph.speed else 'Speed view · read only')
    def view(self,speed):
        self.graph.speed=speed;self.graph.update();self.sync_point();self.hint.setText('Speed is the slope of your position graph. Switch to Position to edit.' if speed else 'Drag a point or square handle. Double-click the curve to add a point. Alt bypasses snapping.')
    def fit(self):self.graph.fit()
    def set_snap(self,on):self.graph.snap=on
    def set_guides(self,on):self.graph.guides=on;self.graph.update()
    def show_advanced(self,on):
        self.advanced.setVisible(on);self.advanced_btn.setText(('▾' if on else '▸')+'  Advanced');self.content.setMinimumHeight(790 if on else 645)
        if on:QTimer.singleShot(0,lambda:self.content_scroll.ensureWidgetVisible(self.advanced,0,10))
    def reset(self):self.choose(self.library[0])
    def play(self):
        if self.timer.isActive():self.stop_preview();return
        self.phase=0;self.play_btn.setText('Pause');self.timer.start()
    def tick(self):
        self.phase+=.006
        if self.phase>1:self.phase=0
        self.graph.playhead=self.phase;self.graph.update()
    def stop_preview(self):self.timer.stop();self.graph.playhead=None;self.graph.update();self.play_btn.setText('Preview curve')
    def load_saved(self):
        if not self.savedir.exists():return
        for p in sorted(self.savedir.glob('*.ebtime')):
            try:self.library.append(load_preset(p))
            except (ValueError,KeyError,TypeError,OSError):pass
    def save_preset(self):
        name,ok=QInputDialog.getText(self,'Save your curve','Preset name',text=self.current_name)
        if not ok or not name.strip():return
        data={'format':'ebtime-curve-v1','name':name.strip()[:60],'nodes':self.graph.curve.data()}
        try:
            self.savedir.mkdir(parents=True,exist_ok=True)
            import uuid
            path=self.savedir/(uuid.uuid4().hex+'.ebtime');path.write_text(json.dumps(data,indent=2),encoding='utf-8')
            self.library.append(load_preset(path));self.category.setCurrentText('My presets');self.populate();self.status.setText('Preset saved on this computer.')
        except OSError as exc:QMessageBox.warning(self,'Could not save',str(exc))
    def import_curve(self):
        path,_=QFileDialog.getOpenFileName(self,'Import ebtime curve','','ebtime curves (*.ebtime)')
        if path:
            try:p=load_preset(path);self.choose(p);self.status.setText('Curve imported. Save preset to keep it in your library.')
            except (ValueError,KeyError,TypeError,OSError) as exc:QMessageBox.warning(self,'Could not import',str(exc))
    def apply(self):
        try:
            state=self.state();frame_keys(self.graph.curve,self.first,self.last,state['source_start'],state['source_end'],state['amount']/100,state['travel'])
            if self.response:
                target=Path(self.response);temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(state),encoding='utf-8');temporary.replace(target);self.close()
            else:
                path,_=QFileDialog.getSaveFileName(self,'Export curve',self.current_name+'.ebtime','ebtime curves (*.ebtime)')
                if path:Path(path).write_text(json.dumps({'format':'ebtime-curve-v1','name':self.current_name,'nodes':self.graph.curve.data()},indent=2),encoding='utf-8');self.status.setText('Curve exported. Open ebtime from Resolve to apply it.')
        except (ValueError,OSError) as exc:QMessageBox.warning(self,'Check your curve',str(exc))
    def set_theme(self,name):
        self.accent=ACCENTS.get(name,ACCENTS['Mint'])
        if hasattr(self,'graph'):
            self.graph.accent=self.accent;self.graph.update()
            for c in self.cards:c.accent=self.accent;c.update()
            self.apply_btn.setStyleSheet(f'background:{self.accent};color:#14231c;')
    def load_preferences(self):
        try:
            p=json.loads(self.settings_path.read_text(encoding='utf-8'));self.theme.setCurrentText(p.get('theme','Mint'));self.snap.setChecked(p.get('snap',True));self.guides.setChecked(p.get('guides',True))
        except (OSError,ValueError,TypeError):pass
    def closeEvent(self,event):
        try:
            self.userdir.mkdir(parents=True,exist_ok=True);self.settings_path.write_text(json.dumps({'theme':self.theme.currentText(),'snap':self.snap.isChecked(),'guides':self.guides.isChecked()}),encoding='utf-8')
        except OSError:pass
        self.timer.stop();event.accept()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--session');parser.add_argument('--response');args=parser.parse_args()
    session=json.loads(Path(args.session).read_text(encoding='utf-8')) if args.session else None
    app=QApplication(sys.argv);app.setApplicationName('ebtime');app.setOrganizationName('epicbloxfx');app.setFont(QFont('Segoe UI',10))
    win=Editor(session,args.response);win.show();return app.exec()

if __name__=='__main__':sys.exit(main())
