"""StructView — working 2D/3D hybrid. Items before super().__init__()."""

import numpy as np
from math import sin, cos, pi
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QMouseEvent, QWheelEvent, QKeyEvent


class StructView(QGraphicsView):

    def __init__(self, document=None, parent=None):
        self.document = document
        self.tool_manager = None
        self.analysis_result = None
        self.show_deformed = False
        self.deformed_scale = 50.0

        # 3D orbit camera
        self._theta = -pi / 6
        self._phi = 0.3
        self._radius = 20.0
        self._target = np.array([0., 0., 0.])
        self._up = np.array([0., 1., 0.])
        self._vp_w = 800
        self._vp_h = 600

        # Pre-draw scene BEFORE super().__init__
        self._scene = QGraphicsScene()
        self._scene.setSceneRect(-10000, -10000, 20000, 20000)
        self._draw_scene()
        super().__init__(self._scene, parent)

        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor(15, 15, 25))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._status_callback = None
        self._last_mouse = None

    @property
    def camera_pos(self):
        x = self._target[0] + self._radius * cos(self._phi) * cos(self._theta)
        y = self._target[1] + self._radius * sin(self._phi)
        z = self._target[2] + self._radius * cos(self._phi) * sin(self._theta)
        return np.array([x, y, z])

    def _world_to_screen(self, wx, wy, wz):
        eye = self.camera_pos
        fwd = self._target - eye; fwd /= np.linalg.norm(fwd)
        rt = np.cross(fwd, self._up); rt /= np.linalg.norm(rt)
        cu = np.cross(rt, fwd)
        p = np.array([wx, wy, wz]) - eye
        sz = np.dot(p, fwd)
        if sz < 0.01: return None
        vw = max(self._vp_w, 1); vh = max(self._vp_h, 1)
        sc = vw / (2.0 * max(self._radius, 0.1) * 0.05)
        return QPointF(vw/2 + np.dot(p,rt)*sc, vh/2 - np.dot(p,cu)*sc)

    def _draw_scene(self):
        self._scene.clear()
        self._scene.addLine(-20,0,20,0,QPen(QColor(255,50,50),2))
        self._scene.addLine(0,-20,0,20,QPen(QColor(255,50,50),2))
        if not self.document: return
        self._draw_grid()
        self._draw_model()

    def _draw_grid(self):
        pen = QPen(QColor(30, 35, 45), 0.5)
        n, s = 15, 1.0
        for i in range(-n, n+1):
            for a1,b1,a2,b2 in [(i*s,-n*s,i*s,n*s),(-n*s,i*s,n*s,i*s)]:
                p1=self._world_to_screen(a1,0,b1); p2=self._world_to_screen(a2,0,b2)
                if p1 and p2: self._scene.addLine(p1.x(),p1.y(),p2.x(),p2.y(),pen)

    def _draw_model(self):
        if not self.document: return
        from src.model.entities.node import SupportType
        wp=QPen(QColor(255,255,255),2); wb=QBrush(QColor(255,255,255))
        gp=QPen(QColor(50,255,50),2.5); gb=QBrush(QColor(50,255,50))
        yp=QPen(QColor(255,255,0),3); yb=QBrush(QColor(255,255,0))
        mp=QPen(QColor(80,180,255),2); r=4

        for n in self.document.nodes.values():
            p=self._world_to_screen(n.x,n.y,n.z)
            if not p: continue
            issel=(n.id==self.document.selected_node_id)
            pen=yp if issel else (gp if n.is_supported else wp)
            brush=yb if issel else (gb if n.is_supported else wb)
            self._scene.addEllipse(p.x()-r,p.y()-r,r*2,r*2,pen,brush)

        for m in self.document.members.values():
            n1=self.document.nodes[m.start_node_id]; n2=self.document.nodes[m.end_node_id]
            p1=self._world_to_screen(n1.x,n1.y,n1.z); p2=self._world_to_screen(n2.x,n2.y,n2.z)
            if not p1 or not p2: continue
            issel=(m.id==self.document.selected_member_id)
            self._scene.addLine(p1.x(),p1.y(),p2.x(),p2.y(),yp if issel else mp)

    def refresh_view(self):
        self._vp_w = self.viewport().width() or self._vp_w
        self._vp_h = self.viewport().height() or self._vp_h
        self._draw_scene()

    def fit_to_model(self):
        doc=self.document
        if not doc or doc.node_count==0: return
        xs=[n.x for n in doc.nodes.values()]; ys=[n.y for n in doc.nodes.values()]
        zs=[n.z for n in doc.nodes.values()]
        self._target=np.array([(max(xs)+min(xs))/2,(max(ys)+min(ys))/2,(max(zs)+min(zs))/2])
        self._radius=max(max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs),1.0)*1.8
        self.refresh_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._vp_w=self.viewport().width(); self._vp_h=self.viewport().height()
        if self._vp_w>0: self.refresh_view()

    def _screen_to_world(self, scene_pos):
        vw=max(self._vp_w,1)
        sc=self._radius*0.05*2/vw
        return QPointF(self._target[0]+(scene_pos.x()-vw/2)*sc,
                       self._target[2]-(scene_pos.y()-self._vp_h/2)*sc)

    def mousePressEvent(self, event: QMouseEvent):
        self._last_mouse=event.pos()
        if self.tool_manager and self.tool_manager.active_tool:
            w=self._screen_to_world(self.mapToScene(event.pos()))
            self.tool_manager.active_tool.mouse_press(event,w)
            self.refresh_view(); return
        if event.button()==Qt.MouseButton.MiddleButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            w=self._screen_to_world(self.mapToScene(event.pos()))
            self.tool_manager.active_tool.mouse_move(event,w)
            self._last_mouse=event.pos(); return
        if self._last_mouse is None: self._last_mouse=event.pos(); return
        dx=event.pos().x()-self._last_mouse.x(); dy=event.pos().y()-self._last_mouse.y()
        if event.buttons()&Qt.MouseButton.MiddleButton:
            if event.modifiers()&Qt.KeyboardModifier.ShiftModifier:
                self._target+=np.array([-dx*0.02,dy*0.02,0.])
            else:
                self._theta-=dx*0.005; self._phi+=dy*0.005
                self._phi=max(-pi/2+0.01,min(pi/2-0.01,self._phi))
            self.refresh_view()
        self._last_mouse=event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            w=self._screen_to_world(self.mapToScene(event.pos()))
            self.tool_manager.active_tool.mouse_release(event,w)
            self.refresh_view(); return
        self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event: QWheelEvent):
        self._radius*=1.0-event.angleDelta().y()*0.001
        self._radius=max(1.0,min(200.0,self._radius))
        self.refresh_view()

    def keyPressEvent(self, event: QKeyEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.key_press(event); return
