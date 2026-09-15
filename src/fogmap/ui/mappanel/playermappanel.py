import wx
from lxml import etree

from ... import gfx

from .. import board

from .mappanel import MapPanel


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
		self.userViewListener = None
		# Where the GM is pointing, in map pixels, and what colour to draw the
		# arrow.  None whenever the GM is not in Draw mode or has taken the
		# mouse off the map.
		self.pointer = None
		self.pointerColour = wx.Colour(255, 255, 255)

		super(PlayerMapPanel, self).__init__(parent)
	
		self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
		self.Bind(wx.EVT_MOUSEWHEEL, self.onWheel)
		self.Bind(wx.EVT_MOTION, self.onMouseMove)
		self.Bind(wx.EVT_RIGHT_DCLICK, self.onRightDClick)
		self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.onKeyUp)

	def reset(self):
		super(PlayerMapPanel, self).reset()
		# The arrow points at a map pixel, which means nothing over the map
		# coming in.
		self.pointer = None

	def setPointer(self, mapPt, colour=None):
		"""Show the GM's cursor to the players at mapPt, or nowhere at all if
		   it is None.

		   Only the two boxes involved are invalidated.  The cursor moves with
		   every mouse event the GM generates, and repainting the whole player
		   view that often - a full-screen window, often a large one - would
		   cost more than everything else this application does put together."""
		if (colour is not None):
			colour = wx.Colour(colour)
		if ((mapPt == self.pointer) and
			((colour is None) or (colour == self.pointerColour))):
			return
		old = self.pointer
		self.pointer = mapPt
		if (colour is not None):
			self.pointerColour = colour
		if (self.mapImg is None):
			return
		for pt in (old, mapPt):
			if (pt is not None):
				self.RefreshRect(board.pointerRect(self._mapToScreen(pt)))

	def setUserViewListener(self, listener):
		"""Called when the GM moves this view, so the document can be flagged as
		   having changes worth keeping.

		   Deliberately separate from setViewListener: that one also fires when
		   the window is resized and while a document's saved position is being
		   restored, neither of which is the GM changing anything."""
		self.userViewListener = listener

	def _userViewChanged(self):
		if (self.userViewListener != None):
			self.userViewListener()

	def setScale(self, scale, refresh=True):
		self.scale = min(max(scale, PlayerMapPanel.MIN_SCALE), PlayerMapPanel.MAX_SCALE)
		self._fireViewChanged()
		if (refresh):
			self.Refresh()

	def modifyScale(self, increment, refresh=True):
		self.setScale(self.scale + (self.scale * increment), refresh)
		self._userViewChanged()

	def setOffset(self, x, y, refresh=True):
		self.offset = (x, y)
		self._fireViewChanged()
		if (refresh):
			self.Refresh()

	def modifyOffset(self, dx, dy, refresh=True):
		self.setOffset(self.offset[0] + dx, self.offset[1] + dy, refresh)

	def recentre(self):
		self.setOffset(0, 0)
		self._userViewChanged()

	def toggleMirror(self):
		self.mirror = not self.mirror
		self._userViewChanged()
		self.Refresh()

	def getViewportAspect(self):
		"""Width / height of the player window, which the GM overlay locks to."""
		cw, ch = self.GetClientSize()
		if (ch <= 0):
			return None
		return cw / float(ch)

	def getViewportRect(self):
		"""The map-space rectangle currently on screen, as (x, y, w, h).

		   Mirroring flips left and right within the same rectangle, so it does
		   not affect the result."""
		cw, ch = self.GetClientSize()
		if ((self.mapImg is None) or (self.scale <= 0) or (cw <= 0) or (ch <= 0)):
			return None
		w = cw / self.scale
		h = ch / self.scale
		bsz = self.mapImg.GetSize()
		centreX = bsz.width / 2.0 - self.offset[0]
		centreY = bsz.height / 2.0 - self.offset[1]
		return (centreX - w / 2.0, centreY - h / 2.0, w, h)

	def showMapRect(self, rect, user=True):
		"""Zoom and pan so that the given map rectangle fills the window.

		   user is False when the app frames a freshly opened image, which is
		   not a change the GM made and so is nothing to save."""
		x, y, w, h = rect
		cw, ch = self.GetClientSize()
		if ((self.mapImg is None) or (w <= 0) or (h <= 0) or (cw <= 0) or (ch <= 0)):
			return
		bsz = self.mapImg.GetSize()
		self.offset = (bsz.width / 2.0 - (x + w / 2.0),
					   bsz.height / 2.0 - (y + h / 2.0))
		# min() keeps the whole rect visible if its aspect does not match.
		self.setScale(min(cw / float(w), ch / float(h)))
		if (user):
			self._userViewChanged()

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
		self._userViewChanged()

	def zoomAtMapPoint(self, increment, mapPt):
		"""Zoom, keeping one map pixel pinned wherever it currently appears.
		   Used when the GM zooms this view by pointing at the GM's own map."""
		if (self.mapImg is None):
			self.modifyScale(increment)
			return
		self._zoomAbout(increment, mapPt, self._mapToScreen(mapPt))
		self._userViewChanged()

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
		self._userViewChanged()

	def panByMapDelta(self, dx, dy):
		"""Pan by a distance already expressed in map pixels."""
		self.modifyOffset(dx, dy)
		self._userViewChanged()

	def onWheel(self, evt):
		increment = 0.1 if (evt.GetWheelRotation() > 0) else -0.1
		self.zoomAtScreenPoint(increment, evt.GetPosition())

	def onRightDown(self, evt):
		self.beginPan(evt.GetPosition())

	def onRightDClick(self, evt):
		self.recentre()

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
		self._userViewChanged()

	def onKeyUp(self, evt):
		if (evt.ControlDown() and (evt.GetUnicodeKey() == 70)):
			self.toggleMirror()

	def _draw(self, gc, box):
		super(PlayerMapPanel, self)._draw(gc, box)
		self._drawPointer(gc)

	def _drawPointer(self, gc):
		"""Drawn last, over everything, and in this panel's own coordinates:
		   the arrow is a fixed size on screen however far the players' view
		   happens to be zoomed, which is what makes it usable to point with."""
		if ((self.pointer is None) or (self.mapImg is None)):
			return
		board.drawPointer(gc, self._mapToScreen(self.pointer), self.pointerColour)

	def _applyMapTransform(self, gc):
		self._offsetAndScale(gc)

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
			gc.DrawBitmap(self._mapBitmap(),
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

	def _drawGrid(self, gc, box):
		if (self.grid != None):
			gc.PushState()
			self._offsetAndScale(gc)
			# This panel zooms and pans, so the box has to be carried back into
			# map coordinates before the grid can use it.  Mirroring swaps left
			# and right, which min/max sorts out.
			a = self._screenToMap((box[0], box[1]))
			b = self._screenToMap((box[2], box[3]))
			clip = (min(a[0], b[0]), min(a[1], b[1]),
					max(a[0], b[0]), max(a[1], b[1]))
			self.grid.drawGrid(gc, self.map.size[0], self.map.size[1], clip)
			gc.PopState()

	def _alpha(self, mask, box=None):
		return gfx.playerAlpha(mask, box)

	def _mapRectToClient(self, box):
		"""This panel scales and pans, so a box of map pixels lands wherever
		   the current view puts it.  Rounded outwards, plus a pixel of slack
		   for the edge the scaling lands between."""
		a = self._mapToScreen((box[0], box[1]))
		b = self._mapToScreen((box[2], box[3]))
		left = int(min(a[0], b[0])) - 1
		top = int(min(a[1], b[1])) - 1
		right = int(max(a[0], b[0])) + 2
		bottom = int(max(a[1], b[1])) + 2
		return wx.Rect(left, top, right - left, bottom - top)

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
