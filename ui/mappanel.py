import wx
from lxml import etree

import gfx
import data

from . import grid

class MapPanel(wx.Panel):	
	def __init__(self, parent):
		super(MapPanel, self).__init__(parent, -1)
		self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
		self.SetDoubleBuffered(True)

		self.map = None
		self.grid = None
		self.mapImg = None
		self.playerPanel = None
		self._buffer = wx.Bitmap.FromRGBA(1, 1)
		
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_PAINT, self.onPaint)

	def setMap(self, map):
		if (self.map != None):
			self.map.removeUpdateListener(self._updateMap)
		self.map = map
		self.map.addUpdateListener(self._updateMap)
		self._updateMap()
		
	def setPlayerPanel(self, panel):
		self.playerPanel = panel
		self.Bind(wx.EVT_KEY_DOWN, self.playerPanel.onKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.playerPanel.onKeyUp)

	def reset(self):
		self.mapImg = None

	def onSize(self, evt):
		w, h = self.GetClientSize()
		self._buffer = wx.Bitmap.FromRGBA(max(w, 1), max(h, 1))
		self.Refresh()
		
	def onPaint(self, evt):
		dc = wx.BufferedPaintDC(self, self._buffer)
		try:
			gc = wx.GraphicsContext.Create(dc)
		except NotImplementedError:
			dc.DrawText("This build of wxPython does not support the wx.GraphicsContext "
						"family of classes.",
						25, 25)
			return	

		gc.PushState()									
		self._draw(gc)
		gc.PopState()
		
	def _draw(self, gc):
		self._drawMap(gc)
		if ((self.map != None) and (self.map.grid.visible)):
			self._drawGrid(gc)		

	def onClose(self, evt):
		if (self.map != None):
			self.map.removeUpdateListener(self._updateMap)
		return True

	def _drawMap(self, gc):
		raise Exception("_drawMap called on base MapPanel class.")

	def _drawGrid(self, gc):
		raise Exception("_drawGrid called on base MapPanel class.")

	def _updateMap(self):
		if (self.mapImg == None):
			self.mapImg = gfx.pilToWx(self.map.mapImg)
		self._updateGrid()
		
	def _updateGrid(self):
		self.grid = None
		if (self.map.grid.type == data.Grid.GRID_SQUARE):
			self.grid = grid.SquareGrid(self.map.grid.size)
		elif (self.map.grid.type == data.Grid.GRID_HEX):
			self.grid = grid.HexGrid(self.map.grid.size)
			
	def readSettings(self, settings):
		raise Exception("getSettings called on base MapPanel class.")
	
	def writeSettings(self, settings):
		raise Exception("getSettings called on base MapPanel class.")


class PlayerMapPanel(MapPanel):
	MOVE_KEYS = (wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_UP, wx.WXK_DOWN)
	MIN_SCALE = 0.05
	MAX_SCALE = 20.0

	def __init__(self, parent):
		self.scale = 1.0
		self.offset = (0, 0)
		self.panAnchor = None
		self.mirror = False
		self.playerPanel = None
		
		super(PlayerMapPanel, self).__init__(parent)
	
		self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
		self.Bind(wx.EVT_MOUSEWHEEL, self.onWheel)
		self.Bind(wx.EVT_MOTION, self.onMouseMove)
		self.Bind(wx.EVT_RIGHT_DCLICK, self.onRightDClick)
		self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.onKeyUp)

	def setScale(self, scale, refresh=True):
		self.scale = min(max(scale, PlayerMapPanel.MIN_SCALE), PlayerMapPanel.MAX_SCALE)
		if (refresh):
			self.Refresh()

	def modifyScale(self, increment, refresh=True):
		self.setScale(self.scale + (self.scale * increment), refresh)

	def setOffset(self, x, y, refresh=True):
		self.offset = (x, y)
		if (refresh):
			self.Refresh()

	def modifyOffset(self, dx, dy, refresh=True):
		self.setOffset(self.offset[0] + dx, self.offset[1] + dy, refresh)

	def toggleMirror(self):
		self.mirror = not self.mirror
		self.Refresh()

	def _scaleXY(self, scale=None):
		"""Horizontal scale is negated while mirrored, so screen deltas still map
		   back to the part of the image the cursor is actually over."""
		scale = self.scale if (scale is None) else scale
		return (-scale if self.mirror else scale, scale)

	def _mapToScreen(self, mapPt, scale=None, offset=None):
		scale = self.scale if (scale is None) else scale
		offset = self.offset if (offset is None) else offset
		cw, ch = self.GetClientSize()
		bsz = self.mapImg.GetSize()
		sx, sy = self._scaleXY(scale)
		return (cw / 2.0 + sx * (mapPt[0] - bsz.width / 2.0 + offset[0]),
				ch / 2.0 + sy * (mapPt[1] - bsz.height / 2.0 + offset[1]))

	def _screenToMap(self, screenPt, scale=None, offset=None):
		scale = self.scale if (scale is None) else scale
		offset = self.offset if (offset is None) else offset
		cw, ch = self.GetClientSize()
		bsz = self.mapImg.GetSize()
		sx, sy = self._scaleXY(scale)
		return ((screenPt[0] - cw / 2.0) / sx + bsz.width / 2.0 - offset[0],
				(screenPt[1] - ch / 2.0) / sy + bsz.height / 2.0 - offset[1])

	def _offsetPinning(self, mapPt, screenPt, scale):
		"""The offset that lands mapPt exactly on screenPt at the given scale."""
		cw, ch = self.GetClientSize()
		bsz = self.mapImg.GetSize()
		sx, sy = self._scaleXY(scale)
		return ((screenPt[0] - cw / 2.0) / sx - mapPt[0] + bsz.width / 2.0,
				(screenPt[1] - ch / 2.0) / sy - mapPt[1] + bsz.height / 2.0)

	def _zoomAbout(self, increment, mapPt, screenPt):
		newScale = min(max(self.scale + (self.scale * increment),
						   PlayerMapPanel.MIN_SCALE), PlayerMapPanel.MAX_SCALE)
		if (newScale == self.scale):
			return
		self.offset = self._offsetPinning(mapPt, screenPt, newScale)
		self.setScale(newScale)

	def zoomAtScreenPoint(self, increment, screenPt):
		"""Zoom, keeping whatever sits under screenPt pinned in place."""
		if (self.mapImg is None):
			self.modifyScale(increment)
			return
		self._zoomAbout(increment, self._screenToMap(screenPt), screenPt)

	def zoomAtMapPoint(self, increment, mapPt):
		"""Zoom, keeping one map pixel pinned wherever it currently appears.
		   Used when the GM zooms this view by pointing at the GM's own map."""
		if (self.mapImg is None):
			self.modifyScale(increment)
			return
		self._zoomAbout(increment, mapPt, self._mapToScreen(mapPt))

	def beginPan(self, screenPt):
		self.panAnchor = screenPt

	def endPan(self):
		self.panAnchor = None

	def dragPanTo(self, screenPt):
		"""Drag the map so that it tracks the cursor one-for-one."""
		if (self.panAnchor is None):
			self.beginPan(screenPt)
			return
		sx, sy = self._scaleXY()
		self.modifyOffset((screenPt[0] - self.panAnchor[0]) / sx,
						  (screenPt[1] - self.panAnchor[1]) / sy)
		self.panAnchor = screenPt

	def panByMapDelta(self, dx, dy):
		"""Pan by a distance already expressed in map pixels."""
		self.modifyOffset(dx, dy)

	def onWheel(self, evt):
		increment = 0.1 if (evt.GetWheelRotation() > 0) else -0.1
		self.zoomAtScreenPoint(increment, evt.GetPosition())

	def onRightDown(self, evt):
		self.beginPan(evt.GetPosition())

	def onRightDClick(self, evt):
		self.setOffset(0, 0)

	def onMouseMove(self, evt):
		if (evt.RightIsDown()):
			self.dragPanTo(evt.GetPosition())
		else:
			self.endPan()

	def onKeyDown(self, evt):
		key = evt.GetKeyCode()		
		if (key in PlayerMapPanel.MOVE_KEYS):
			self.onMoveKeyDown(key, evt)
		elif (key == wx.WXK_PAGEUP):
			self.modifyScale(0.1)
		elif (key == wx.WXK_PAGEDOWN):
			self.modifyScale(-0.1)

	def onMoveKeyDown(self, key, evt):
		moveIncrement = (1, 1)
		if (not evt.ShiftDown()):
			if (self.grid != None):
				moveIncrement = self.grid.getGridUnitSize()
		elif (self.grid is None):
			moveIncrement = (10, 10)
		if (key == wx.WXK_LEFT):
			self.modifyOffset(moveIncrement[0], 0)
		elif (key == wx.WXK_RIGHT):
			self.modifyOffset(-moveIncrement[0], 0)
		elif (key == wx.WXK_UP):
			self.modifyOffset(0, moveIncrement[1])
		elif (key == wx.WXK_DOWN):
			self.modifyOffset(0, -moveIncrement[1])

	def onKeyUp(self, evt):
		if (evt.ControlDown() and (evt.GetUnicodeKey() == 70)):
			self.toggleMirror()

	def _offsetAndScale(self, gc):
		bsz = self.mapImg.GetSize()
		clientRect = self.GetClientRect()
		
		gc.Translate(clientRect.width/2, clientRect.height/2)
		if (self.mirror):
			gc.Scale(-self.scale, self.scale)
		else:
			gc.Scale(self.scale, self.scale)
		gc.Translate(-bsz.width/2, -bsz.height/2)
		if (self.offset != (0, 0)):
			gc.Translate(*self.offset)		

	def _drawMap(self, gc):
		w, h = self.GetClientSize()
		
		gc.SetBrush(wx.Brush("black"))
		gc.DrawRectangle(0, 0, w, h)
		
		if (self.mapImg != None):
			gc.PushState()
			self._offsetAndScale(gc)
			color = wx.Colour(255, 255, 255)
			gc.SetBrush(wx.Brush(color))
			bsz = self.mapImg.GetSize()
			gc.DrawBitmap(self.mapImg.ConvertToBitmap(),
						  0, 
						  0,				  
						  bsz.width, 
						  bsz.height)
			gc.PopState()
			
		#font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
		#font.SetWeight(wx.BOLD)
		#gc.SetFont(font)
		#textBgBrush = gc.CreateBrush(wx.Brush(wx.Color(255, 255, 255)))
		#gc.DrawText("Zoom: %f" % self.scale, 10, 10, textBgBrush)
		#gc.DrawText("Offset: (%d, %d)" % self.offset, 10, 20, textBgBrush)

	def _drawGrid(self, gc):
		if (self.grid != None):
			gc.PushState()
			self._offsetAndScale(gc)
			self.grid.drawGrid(gc, self.map.size[0], self.map.size[1])
			gc.PopState()

	def _updateMap(self):
		super(PlayerMapPanel, self)._updateMap()
		if (self.mapImg != None):
			self.mapImg.SetAlpha(self.map.mask.tobytes())
			self.Refresh(False)
			
	def readSettings(self, settings):
		for child in settings:
			if (child.tag == "scale"):
				self.setScale(float(child.text))
			elif (child.tag == "offset"):
				x = float(child.get("x"))
				y = float(child.get("y"))
				self.setOffset(x, y)
	
	def writeSettings(self, settings):
		scale = etree.Element("scale")
		scale.text = str(self.scale)
		settings.append(scale)
		
		offset = etree.Element("offset", x=str(self.offset[0]), y=str(self.offset[1]))
		settings.append(offset)

		
class GMMapPanel(MapPanel):
	def __init__(self, parent):
		self.brush = None
		self.mouse = (0, 0)
		self.lastBrushPt = (0, 0)
		self.axisLock = (False, False)
		self.forwarding = False
		self.forwardAnchor = None
		
		super(GMMapPanel, self).__init__(parent)

		self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
		self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
		self.Bind(wx.EVT_LEFT_UP, self.onMouseUp)
		self.Bind(wx.EVT_RIGHT_UP, self.onMouseUp)
		self.Bind(wx.EVT_RIGHT_DCLICK, self.onRightDClick)
		self.Bind(wx.EVT_MOUSEWHEEL, self.onWheel)
		self.Bind(wx.EVT_MOTION, self.onMouseMove)
		
	def setBrush(self, brush):
		self.brush = brush

	def _forwardsToPlayer(self, evt):
		"""While Alt is held the mouse drives the player view instead of the brush."""
		return (self.playerPanel is not None) and evt.AltDown()

	def _setForwarding(self, forwarding):
		if (forwarding == self.forwarding):
			return
		self.forwarding = forwarding
		self.SetCursor(wx.Cursor(wx.CURSOR_HAND if forwarding else wx.CURSOR_ARROW))
		self.Refresh()

	def onLeftDown(self, evt):
		if (self._forwardsToPlayer(evt)):
			self.forwardAnchor = evt.GetPosition()
			return
		if (self.brush != None):
			pos = evt.GetPosition()
			self.map.applyBrush(self.brush, pos[0], pos[1])
			
	def onRightDown(self, evt):
		if (self._forwardsToPlayer(evt)):
			self.forwardAnchor = evt.GetPosition()
			return
		if (self.brush != None):
			pos = evt.GetPosition()
			self.map.unapplyBrush(self.brush, pos[0], pos[1])

	def onMouseUp(self, evt):
		self.forwardAnchor = None
		evt.Skip()

	def onRightDClick(self, evt):
		if (self._forwardsToPlayer(evt)):
			self.playerPanel.setOffset(0, 0)
		else:
			evt.Skip()

	def onWheel(self, evt):
		if (not self._forwardsToPlayer(evt)):
			# Leave the wheel alone so the scrolled panel keeps scrolling.
			evt.Skip()
			return
		increment = 0.1 if (evt.GetWheelRotation() > 0) else -0.1
		# This panel draws the map 1:1, so its client coords are map pixels.
		pos = evt.GetPosition()
		self.playerPanel.zoomAtMapPoint(increment, (pos[0], pos[1]))

	def _forwardDrag(self, evt):
		pos = evt.GetPosition()
		if (evt.LeftIsDown() or evt.RightIsDown()):
			if (self.forwardAnchor is not None):
				# 1:1 panel, so this delta is already in map pixels.
				self.playerPanel.panByMapDelta(pos[0] - self.forwardAnchor[0],
											   pos[1] - self.forwardAnchor[1])
			self.forwardAnchor = pos
		else:
			self.forwardAnchor = None

	def onMouseMove(self, evt):
		if (self._forwardsToPlayer(evt)):
			self._setForwarding(True)
			self._forwardDrag(evt)
			return
		self._setForwarding(False)
		self.forwardAnchor = None
		self.axisLock = (evt.ShiftDown(), evt.ControlDown())
		mousePos = evt.GetPosition()
		if (not self.axisLock[0] and not self.axisLock[1]):
			self.mouse = mousePos
		elif (self.axisLock[0]):
			self.mouse = (self.mouse[0], mousePos[1])
		elif (self.axisLock[1]):
			self.mouse = (mousePos[0], self.mouse[1])
		
		ptBrush = self.mouse
		if (self.grid != None):
			ptBrush = self.grid.getGridCoords(ptBrush)
						
		if ((self.brush != None) and (ptBrush != self.lastBrushPt)):
			if (evt.LeftIsDown()):
				self.map.applyBrush(self.brush, self.mouse[0], self.mouse[1])
			elif (evt.RightIsDown()):
				self.map.unapplyBrush(self.brush, self.mouse[0], self.mouse[1])
			else:
				self.Refresh()
			self.lastBrushPt = ptBrush
			
	def _draw(self, gc):
		super(GMMapPanel, self)._draw(gc)
		self._drawBrush(gc)

	def _drawMap(self, gc):
		w, h = self.GetSize()
		if (self.mapImg != None):
			bsz = self.mapImg.GetSize()
			w = max(bsz.width, w)
			h = max(bsz.height, h)

		color = wx.Colour(0, 0, 0)
		gc.SetBrush(wx.Brush(color))
		gc.DrawRectangle(0, 0, w, h)

		if (self.mapImg != None):
			bsz = self.mapImg.GetSize()
			color = wx.Colour(255, 255, 255)
			gc.SetBrush(wx.Brush(color))
			gc.DrawBitmap(self.mapImg.ConvertToBitmap(),
						  0, 
						  0,				  
						  bsz.width, 
						  bsz.height)		

	def _drawGrid(self, gc):
		if (self.grid != None):
			# Base grid
			bsz = self.mapImg.GetSize()
			self.grid.drawGrid(gc, bsz.width, bsz.height)	
			
	def _drawBrush(self, gc):
		# Cursor
		if ((self.brush != None) and (not self.forwarding)):
			color = wx.Colour(0, 255, 0, 128)
			gc.SetBrush(wx.Brush(color))
			self.brush.drawToGc(gc, self.mouse[0], self.mouse[1])
			
	def _updateMap(self):
		super(GMMapPanel, self)._updateMap()
		if (self.mapImg != None):
			self.SetMinSize(self.mapImg.GetSize())
			self.mapImg.SetAlpha(self.map.alphaMask.tobytes())
			self.Refresh()
				
	def _updateGrid(self):
		super(GMMapPanel, self)._updateGrid()
		if (isinstance(self.brush, data.GridBrush)):
			self.brush.setGridSize(self.map.grid.size)
			
	def reset(self):
		super(GMMapPanel, self).reset()
		self.brush = None
		
	def readSettings(self, settings):
		pass
	
	def writeSettings(self, settings):
		pass
