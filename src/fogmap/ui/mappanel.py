import math

import wx
import numpy as np
from lxml import etree

from .. import gfx
from .. import data

from . import grid
from . import viewport

class MapPanel(wx.Panel):	
	def __init__(self, parent):
		super(MapPanel, self).__init__(parent, -1)
		self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
		self.SetDoubleBuffered(True)

		self.map = None
		self.grid = None
		self.mapImg = None
		# The map image converted for drawing.  Held across paints because the
		# conversion costs time proportional to the whole map - a sixth of a
		# second on a big one - and it used to be paid on every single repaint,
		# including the ones that only move the brush cursor.  A brush dab
		# patches the box it touched rather than throwing this away.
		self.mapBmp = None
		self.playerPanel = None
		self.viewListener = None
		self._buffer = wx.Bitmap.FromRGBA(1, 1)
		
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_PAINT, self.onPaint)

	def setMap(self, map):
		if (self.map != None):
			self.map.removeUpdateListener(self._updateMap)
		self.map = map
		self.map.addUpdateListener(self._updateMap)
		self.mapBmp = None
		self._updateMap()
		
	def setPlayerPanel(self, panel):
		self.playerPanel = panel
		self.Bind(wx.EVT_KEY_DOWN, self.playerPanel.onKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.playerPanel.onKeyUp)

	def setViewListener(self, listener):
		"""Called whenever this panel's scale, offset or size changes."""
		self.viewListener = listener

	def _fireViewChanged(self):
		if (self.viewListener != None):
			self.viewListener()

	def reset(self):
		self.mapImg = None
		self.mapBmp = None

	def onSize(self, evt):
		w, h = self.GetClientSize()
		self._buffer = wx.Bitmap.FromRGBA(max(w, 1), max(h, 1))
		self._fireViewChanged()
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

		# Draw no more of the map than was invalidated.  The buffer is kept
		# between paints, so whatever falls outside the clip is still there
		# from last time - which is what makes a brush dab cost the size of the
		# brush instead of the size of the map.
		box = self.GetUpdateRegion().GetBox()
		if (box.IsEmpty()):
			return

		gc.PushState()
		gc.Clip(box.x, box.y, box.width, box.height)
		self._draw(gc, (box.x, box.y, box.x + box.width, box.y + box.height))
		gc.PopState()
		
	def _draw(self, gc, box):
		"""box is the part of the panel being repainted, in its own
		   coordinates.  Passed down so the grid can skip what is off-screen
		   rather than relying on the clip to throw it away afterwards."""
		self._drawMap(gc)
		if ((self.map != None) and (self.map.grid.visible)):
			self._drawGrid(gc, box)		

	def onClose(self, evt):
		if (self.map != None):
			self.map.removeUpdateListener(self._updateMap)
		return True

	def _drawMap(self, gc):
		raise Exception("_drawMap called on base MapPanel class.")

	def _drawGrid(self, gc, box):
		raise Exception("_drawGrid called on base MapPanel class.")

	def _alpha(self, mask, box=None):
		"""How this panel turns the fog mask into alpha.  The two windows show
		   the same mask differently, and that is the only difference between
		   them here."""
		raise Exception("_alpha called on base MapPanel class.")

	def _mapRectToClient(self, box):
		"""A box in map pixels as a rectangle in this panel's own coordinates."""
		raise Exception("_mapRectToClient called on base MapPanel class.")

	def _mapBitmap(self):
		"""The drawable map, converted on first use after a change and then
		   kept.  Callers must not hold onto it across a _updateMap."""
		if ((self.mapBmp is None) and (self.mapImg is not None)):
			self.mapBmp = self.mapImg.ConvertToBitmap()
		return self.mapBmp

	def _clipToMap(self, box):
		"""A brush at the edge of the map reaches past it; nothing downstream
		   copes with that, so trim first.  None if nothing is left."""
		w, h = self.map.size
		x0 = max(int(box[0]), 0)
		y0 = max(int(box[1]), 0)
		x1 = min(int(box[2]), w)
		y1 = min(int(box[3]), h)
		if ((x1 <= x0) or (y1 <= y0)):
			return None
		return (x0, y0, x1, y1)

	def _updateMap(self, rect=None):
		"""rect is the box a brush dab touched.  None means rebuild the lot -
		   a new map, a swapped image, a grid change."""
		fresh = (self.mapImg is None)
		if (fresh):
			self.mapImg = gfx.pilToWx(self.map.mapImg)
			self.mapBmp = None
			self._onImageCreated()
		self._updateGrid()
		if (self.mapImg is None):
			return

		box = self._clipToMap(rect) if (rect is not None) else None
		if (fresh or (box is None)):
			self.mapImg.SetAlpha(self._alpha(self.map.mask).tobytes())
			self.mapBmp = None
			self.Refresh(False)
			return

		self._patchMap(box)
		self.RefreshRect(self._mapRectToClient(box))

	def _onImageCreated(self):
		"""Hook for whatever a panel has to do once, when the image appears."""
		pass

	def _patchMap(self, box):
		"""Bring one box of the map up to date with the mask, and nothing else.

		   Both the image and the bitmap built from it are kept in step: the
		   image because a later wholesale rebuild reads from it, the bitmap
		   because that is what actually gets drawn.  The patch is always built
		   from the original image rather than read back off the bitmap, so
		   repeated dabs over the same ground cannot accumulate error."""
		x0, y0, x1, y1 = box
		w = x1 - x0
		h = y1 - y0
		alpha = self._alpha(self.map.mask, box)

		buf = np.frombuffer(self.mapImg.GetAlphaBuffer(), np.uint8)
		buf = buf.reshape(self.mapImg.GetHeight(), self.mapImg.GetWidth())
		buf[y0:y1, x0:x1] = alpha

		if (self.mapBmp is None):
			# Nothing built yet; the next paint reads the image and gets this.
			return
		rgba = np.empty((h, w, 4), np.uint8)
		rgba[:, :, :3] = np.asarray(self.map.mapImg.crop(box))[:, :, :3]
		rgba[:, :, 3] = alpha
		dc = wx.MemoryDC(self.mapBmp)
		gc = wx.GraphicsContext.Create(dc)
		# SOURCE rather than the default OVER: this replaces those pixels
		# outright, alpha included, instead of blending onto what is there.
		gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
		gc.DrawBitmap(wx.Bitmap.FromBufferRGBA(w, h, rgba), x0, y0, w, h)
		del gc
		dc.SelectObject(wx.NullBitmap)

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
		self.userViewListener = None

		super(PlayerMapPanel, self).__init__(parent)
	
		self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
		self.Bind(wx.EVT_MOUSEWHEEL, self.onWheel)
		self.Bind(wx.EVT_MOTION, self.onMouseMove)
		self.Bind(wx.EVT_RIGHT_DCLICK, self.onRightDClick)
		self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.onKeyUp)

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

		
class GMMapPanel(MapPanel):
	# The zoom steps through a ladder of levels rather than a continuous scale,
	# so the wheel, the menu and the toolbar box can never disagree about where
	# on it the view is, and a level is always something with a name.
	ZOOM_LEVELS = (0.1, 0.25, 0.33, 0.5, 0.67, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0)
	DEFAULT_ZOOM = 1.0

	def __init__(self, parent):
		self.brush = None
		# Map pixels, not panel coordinates: the two are the same thing only at
		# 100%, and everything a brush touches is counted in map pixels.
		self.mouse = (0, 0)
		self.lastBrushPt = None
		# Where the brush cursor was last actually painted, which is not the
		# same as where the mouse was a moment ago: several moves can go by
		# between repaints.  Cleaning up after the cursor means invalidating
		# where it really is on screen.
		self.brushDrawnAt = None
		self.axisLock = (False, False)
		self.forwarding = False
		self.forwardAnchor = None
		self.showViewport = False
		self.viewportHandle = None
		self.viewportBase = None
		self.viewportGrabPt = None
		self.viewportHover = None
		self.viewportListener = None
		self.cursorKey = None
		# The map used to be drawn 1:1 and merely scrolled.  It is now drawn
		# through this scale, so the panel is the size of the map at the
		# current zoom and its own coordinates are map pixels times the scale.
		self.scale = GMMapPanel.DEFAULT_ZOOM
		self.scroller = None
		self.zoomListener = None
		
		super(GMMapPanel, self).__init__(parent)

		self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
		self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
		self.Bind(wx.EVT_LEFT_UP, self.onMouseUp)
		self.Bind(wx.EVT_RIGHT_UP, self.onMouseUp)
		self.Bind(wx.EVT_RIGHT_DCLICK, self.onRightDClick)
		self.Bind(wx.EVT_MOUSEWHEEL, self.onWheel)
		self.Bind(wx.EVT_MOTION, self.onMouseMove)
		self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.onCaptureLost)
		
	def setScroller(self, scroller):
		"""The scrolled window this panel sits inside.  Zooming changes the
		   panel's size, which is what that window scrolls over, and holding a
		   point still across a zoom means scrolling it back into place."""
		self.scroller = scroller

	def setZoomListener(self, listener):
		"""Called whenever the zoom changes, so the toolbar can keep up with
		   it however it was changed."""
		self.zoomListener = listener

	def setScale(self, scale, user=True):
		"""user is False when a map's saved zoom is being restored, which is
		   nothing to flag as a change."""
		scale = min(max(float(scale), GMMapPanel.ZOOM_LEVELS[0]),
					GMMapPanel.ZOOM_LEVELS[-1])
		if (scale == self.scale):
			return
		self.scale = scale
		self._applyMinSize()
		# Whatever is on screen was drawn at the old zoom, cursor included.
		self.brushDrawnAt = None
		if (self.zoomListener != None):
			self.zoomListener()
		if (user and (self.playerPanel != None)):
			self.playerPanel._userViewChanged()
		self.Refresh()

	def zoomTo(self, scale, anchor=None, user=True):
		"""Zoom, holding the map point under `anchor` - a point in this panel's
		   own coordinates - where it is on screen.  Without one, the centre of
		   what is on screen holds still, which is what makes zooming from the
		   menu or the toolbar keep the GM where they were looking."""
		if (self.mapImg is None):
			self.setScale(scale, user)
			return
		view = self._viewStart()
		vw, vh = self._visibleSize()
		if (anchor is None):
			anchor = (view[0] + vw / 2.0, view[1] + vh / 2.0)
		mapPt = (anchor[0] / self.scale, anchor[1] / self.scale)
		# Where the anchor sits within the visible area, which is what has to
		# come out the same afterwards.
		rel = (anchor[0] - view[0], anchor[1] - view[1])
		old = self.scale
		self.setScale(scale, user)
		if (self.scale != old):
			self._scrollTo(mapPt[0] * self.scale - rel[0],
						   mapPt[1] * self.scale - rel[1])

	def zoomStep(self, direction, anchor=None):
		self.zoomTo(self.steppedZoom(direction), anchor)

	def steppedZoom(self, direction):
		"""The next level up or down the ladder from wherever the zoom is now.

		   Worked out from the scale rather than an index into the ladder, so a
		   level that is not on it still steps somewhere sensible."""
		levels = GMMapPanel.ZOOM_LEVELS
		if (direction > 0):
			for level in levels:
				if (level > (self.scale + 1e-6)):
					return level
			return levels[-1]
		for level in reversed(levels):
			if (level < (self.scale - 1e-6)):
				return level
		return levels[0]

	def levelAtOrBelow(self, scale):
		"""The largest level on the ladder that is no bigger than scale."""
		best = GMMapPanel.ZOOM_LEVELS[0]
		for level in GMMapPanel.ZOOM_LEVELS:
			if (level <= (scale + 1e-6)):
				best = level
		return best

	def nearestZoomLevel(self, scale):
		return min(GMMapPanel.ZOOM_LEVELS, key=lambda level: abs(level - scale))

	def fitZoomLevel(self):
		"""The largest level that still fits the whole map in the window."""
		if (self.map is None):
			return self.scale
		w, h = self.map.size
		vw, vh = self._visibleSize()
		if ((w <= 0) or (h <= 0) or (vw <= 0) or (vh <= 0)):
			return self.scale
		return self.levelAtOrBelow(min(vw / float(w), vh / float(h)))

	def _viewStart(self):
		"""How far the scrolled window has been scrolled, in pixels."""
		if (self.scroller is None):
			return (0, 0)
		return self.scroller.CalcUnscrolledPosition(0, 0)

	def _visibleSize(self):
		"""How much of the panel can be seen at once."""
		if (self.scroller is None):
			return self.GetClientSize()
		return self.scroller.GetClientSize()

	def _scrollTo(self, x, y):
		if (self.scroller is None):
			return
		# Scroll() counts in scroll units rather than pixels.
		unitX, unitY = self.scroller.GetScrollPixelsPerUnit()
		self.scroller.Scroll(int(round(x / unitX)) if unitX else 0,
							 int(round(y / unitY)) if unitY else 0)

	def _applyMinSize(self):
		"""The panel is the map at the current zoom; the scrolled window sizes
		   itself around that."""
		if (self.mapImg is None):
			return
		bsz = self.mapImg.GetSize()
		self.SetMinSize(wx.Size(max(int(round(bsz.width * self.scale)), 1),
								max(int(round(bsz.height * self.scale)), 1)))
		if (self.scroller != None):
			# Leave the scroll position alone: a zoom puts it back itself, and
			# scrolling to the top on every zoom would throw the view away.
			self.scroller.SetupScrolling(scrollToTop=False, scrollIntoView=False)

	def _clientToMap(self, pt):
		"""A point in this panel's own coordinates as map pixels.  Floored to
		   whole pixels: everything downstream of a brush indexes the mask with
		   them."""
		return (int(math.floor(pt[0] / self.scale)),
				int(math.floor(pt[1] / self.scale)))

	def setBrush(self, brush):
		self.brush = brush
		# Anchors are not comparable between brushes - a hex brush counts in
		# hexes, a freehand one in pixels - so the last one means nothing now.
		self.lastBrushPt = None

	def setPlayerPanel(self, panel):
		super(GMMapPanel, self).setPlayerPanel(panel)
		panel.setViewListener(self._onPlayerViewChanged)

	def _onPlayerViewChanged(self):
		if (self.showViewport):
			self.Refresh(False)

	def setViewportListener(self, listener):
		"""Called when the overlay is switched on or off, so the frame can grey
		   out the brush controls that the overlay disables."""
		self.viewportListener = listener

	def setShowViewport(self, show, user=True):
		"""user is False when a document's saved state is being restored, which
		   is nothing to flag as a change."""
		self.showViewport = show
		self._endViewportDrag()
		self.viewportHover = None
		if (not show):
			self._setCursorFor(None)
		if (self.viewportListener != None):
			self.viewportListener()
		if (user and (self.playerPanel != None)):
			self.playerPanel._userViewChanged()
		self.Refresh()

	def viewportActive(self):
		"""While the overlay is up the mouse drives it, and the brush is off."""
		return self.showViewport and (self.playerPanel is not None)

	def canPaint(self):
		"""A plain image has no fog to paint, and nowhere to save it to."""
		return (self.map != None) and self.map.editable

	VIEWPORT_TOLERANCE = 6
	VIEWPORT_HANDLE_SIZE = 9
	VIEWPORT_MOVE = "move"

	def _viewportRect(self):
		"""The player viewport in map pixels, or None if there is nothing to show."""
		if ((not self.showViewport) or (self.playerPanel is None)):
			return None
		return self.playerPanel.getViewportRect()

	def _viewportTolerance(self):
		"""The grab tolerance is a distance on screen, so how much of the map
		   it covers depends on the zoom."""
		return GMMapPanel.VIEWPORT_TOLERANCE / self.scale

	def _viewportHitTest(self, pos):
		"""pos is in map pixels, which is what the overlay is measured in."""
		rect = self._viewportRect()
		if (rect is None):
			return None
		return viewport.hitTest(rect, pos, self._viewportTolerance())

	def _setCursorFor(self, key):
		if (key == self.cursorKey):
			return
		self.cursorKey = key
		if (key is None):
			self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
		else:
			# Anything that is not a resize handle is a grab.
			self.SetCursor(wx.Cursor(viewport.CURSORS.get(key, wx.CURSOR_HAND)))

	def _grabViewport(self, pos):
		"""Take hold of the overlay: an edge or corner resizes, anywhere else moves."""
		if (not self.viewportActive()):
			return False
		rect = self._viewportRect()
		if (rect is None):
			return False
		handle = viewport.hitTest(rect, pos, self._viewportTolerance())
		self.viewportHandle = handle or GMMapPanel.VIEWPORT_MOVE
		self.viewportBase = rect
		self.viewportGrabPt = pos
		if (not self.HasCapture()):
			self.CaptureMouse()
		return True

	def _endViewportDrag(self):
		self.viewportHandle = None
		self.viewportBase = None
		self.viewportGrabPt = None
		if (self.HasCapture()):
			self.ReleaseMouse()

	def _dragViewport(self, pos):
		if ((self.viewportBase is None) or (self.playerPanel is None)):
			return
		if (self.viewportHandle == GMMapPanel.VIEWPORT_MOVE):
			# Both points are already map pixels, so the rectangle follows the
			# cursor one-for-one at any zoom.
			rect = (self.viewportBase[0] + pos[0] - self.viewportGrabPt[0],
					self.viewportBase[1] + pos[1] - self.viewportGrabPt[1],
					self.viewportBase[2], self.viewportBase[3])
		else:
			aspect = self.playerPanel.getViewportAspect()
			if (aspect is None):
				return
			# Scale limits become width limits, so a drag cannot outrun the zoom range.
			cw = self.playerPanel.GetClientSize()[0]
			rect = viewport.resize(self.viewportBase, self.viewportHandle, pos, aspect,
								   cw / float(PlayerMapPanel.MAX_SCALE),
								   cw / float(PlayerMapPanel.MIN_SCALE))
		self.playerPanel.showMapRect(rect)

	def onCaptureLost(self, evt):
		self.viewportHandle = None
		self.viewportBase = None
		self.viewportGrabPt = None

	def _forwardsToPlayer(self, evt):
		"""While Alt is held the mouse drives the player view instead of the brush."""
		return (self.playerPanel is not None) and evt.AltDown()

	def _setForwarding(self, forwarding):
		if (forwarding == self.forwarding):
			return
		self.forwarding = forwarding
		self._setCursorFor("hand" if forwarding else None)
		self.Refresh()

	def onLeftDown(self, evt):
		pos = self._clientToMap(evt.GetPosition())
		if (self._grabViewport(pos)):
			return
		if (self._forwardsToPlayer(evt)):
			self.forwardAnchor = pos
			return
		if ((self.brush != None) and self.canPaint()):
			self.map.applyBrush(self.brush, pos[0], pos[1])
			self.lastBrushPt = self.brush.anchor(pos[0], pos[1])
			
	def onRightDown(self, evt):
		pos = self._clientToMap(evt.GetPosition())
		if (self._grabViewport(pos)):
			return
		if (self._forwardsToPlayer(evt)):
			self.forwardAnchor = pos
			return
		if ((self.brush != None) and self.canPaint()):
			self.map.unapplyBrush(self.brush, pos[0], pos[1])
			self.lastBrushPt = self.brush.anchor(pos[0], pos[1])

	def onMouseUp(self, evt):
		self.forwardAnchor = None
		if (self.viewportHandle is not None):
			self._endViewportDrag()
		evt.Skip()

	def onRightDClick(self, evt):
		if (self._forwardsToPlayer(evt)):
			self.playerPanel.recentre()
		else:
			evt.Skip()

	def onWheel(self, evt):
		if (evt.ControlDown() or evt.CmdDown()):
			# Zoom this panel, keeping whatever is under the cursor there.
			self.zoomStep(1 if (evt.GetWheelRotation() > 0) else -1,
						  evt.GetPosition())
			return
		if (not self._forwardsToPlayer(evt)):
			# Leave the wheel alone so the scrolled panel keeps scrolling.
			evt.Skip()
			return
		increment = 0.1 if (evt.GetWheelRotation() > 0) else -0.1
		self.playerPanel.zoomAtMapPoint(increment,
										self._clientToMap(evt.GetPosition()))

	def _forwardDrag(self, evt, pos):
		if (evt.LeftIsDown() or evt.RightIsDown()):
			if (self.forwardAnchor is not None):
				# Both points are map pixels already, whatever the zoom.
				self.playerPanel.panByMapDelta(pos[0] - self.forwardAnchor[0],
											   pos[1] - self.forwardAnchor[1])
			self.forwardAnchor = pos
		else:
			self.forwardAnchor = None

	def onMouseMove(self, evt):
		# Everything below works in map pixels, so the zoom is undone once here
		# rather than in each of the things the mouse can be driving.
		pos = self._clientToMap(evt.GetPosition())

		if (self.viewportHandle is not None):
			if (evt.LeftIsDown() or evt.RightIsDown()):
				self._dragViewport(pos)
			else:
				self._endViewportDrag()
			return

		if (self.viewportActive()):
			# The overlay owns the mouse: edges and corners resize, the rest grabs.
			self._setForwarding(False)
			self.forwardAnchor = None
			self.viewportHover = self._viewportHitTest(pos)
			self._setCursorFor(self.viewportHover or GMMapPanel.VIEWPORT_MOVE)
			return

		if (self._forwardsToPlayer(evt)):
			self._setForwarding(True)
			self._forwardDrag(evt, pos)
			return
		self._setForwarding(False)
		self.forwardAnchor = None
		self.viewportHover = None
		self._setCursorFor(None)

		self.axisLock = (evt.ShiftDown(), evt.ControlDown())
		mousePos = pos
		if (not self.axisLock[0] and not self.axisLock[1]):
			self.mouse = mousePos
		elif (self.axisLock[0]):
			self.mouse = (self.mouse[0], mousePos[1])
		elif (self.axisLock[1]):
			self.mouse = (mousePos[0], self.mouse[1])
		
		# Where the brush would next leave its mark.  This comes off the brush
		# rather than off the displayed grid: a grid being switched on says
		# nothing about whether the brush in hand snaps to it, and taking it
		# from the grid meant a freehand brush on a gridded map only painted
		# where it crossed a cell boundary.
		if ((self.brush != None) and self.canPaint()):
			ptBrush = self.brush.anchor(self.mouse[0], self.mouse[1])
			if (ptBrush != self.lastBrushPt):
				if (evt.LeftIsDown()):
					self.map.applyBrush(self.brush, self.mouse[0], self.mouse[1])
				elif (evt.RightIsDown()):
					self.map.unapplyBrush(self.brush, self.mouse[0], self.mouse[1])
				self.lastBrushPt = ptBrush

		# Outside that guard on purpose.  The guard is about where the brush
		# next paints, which a grid snaps to whole cells; the cursor follows
		# the mouse itself and has to keep up with it whether or not a dab was
		# laid down.  Painting invalidates the dab's own box as well, and wx
		# folds the two into one repaint.
		self._refreshBrushCursor()

	def _brushRect(self, pt):
		"""Where a brush at pt - a map point - lands on the panel."""
		return self._mapRectToClient(self.brush.bounds(pt[0], pt[1]))

	def _refreshBrushCursor(self):
		"""Invalidate just the brush cursor: where it is on screen now, and
		   where it is about to be.

		   This used to be a whole-panel Refresh, which on a large map meant
		   rebuilding and blitting every pixel of it to move a small green
		   circle - so merely hovering over the map was as expensive as
		   painting on it."""
		if (self.brush is None):
			return
		rect = self._brushRect(self.mouse)
		if (self.brushDrawnAt is not None):
			if (self.brush.anchor(*self.brushDrawnAt) ==
				self.brush.anchor(*self.mouse)):
				# Same anchor, so what is on screen is already the right shape
				# in the right place.  This is what keeps a brush that snaps to
				# the grid from repainting its way across a cell.
				return
			rect = rect.Union(self._brushRect(self.brushDrawnAt))
		self.RefreshRect(rect.Inflate(2, 2))
			
	def _draw(self, gc, box):
		super(GMMapPanel, self)._draw(gc, box)
		self._drawViewport(gc)
		self._drawBrush(gc)

	def _drawViewport(self, gc):
		rect = self._viewportRect()
		if (rect is not None):
			# Drawn in panel coordinates rather than under the zoom, so the
			# outline stays a line and the handles stay grabbable however far
			# the map is zoomed out.
			viewport.draw(gc, [v * self.scale for v in rect],
						  GMMapPanel.VIEWPORT_HANDLE_SIZE)

	def _drawMap(self, gc):
		w, h = self.GetSize()
		if (self.mapImg != None):
			bsz = self.mapImg.GetSize()
			w = max(int(math.ceil(bsz.width * self.scale)), w)
			h = max(int(math.ceil(bsz.height * self.scale)), h)

		color = wx.Colour(0, 0, 0)
		gc.SetBrush(wx.Brush(color))
		gc.DrawRectangle(0, 0, w, h)

		if (self.mapImg != None):
			bsz = self.mapImg.GetSize()
			color = wx.Colour(255, 255, 255)
			gc.SetBrush(wx.Brush(color))
			gc.PushState()
			self._applyZoom(gc)
			gc.DrawBitmap(self._mapBitmap(),
						  0, 
						  0,				  
						  bsz.width, 
						  bsz.height)		
			gc.PopState()

	def _drawGrid(self, gc, box):
		if (self.grid != None):
			# Base grid.  The grid counts in map pixels, so the box being
			# repainted has to be carried back out of the zoom first.
			bsz = self.mapImg.GetSize()
			gc.PushState()
			self._applyZoom(gc)
			clip = tuple(v / self.scale for v in box)
			self.grid.drawGrid(gc, bsz.width, bsz.height, clip)	
			gc.PopState()

	def _applyZoom(self, gc):
		if (self.scale != 1.0):
			gc.Scale(self.scale, self.scale)

	def _drawBrush(self, gc):
		# Cursor
		self.brushDrawnAt = None
		if ((self.brush != None) and (not self.forwarding) and (not self.showViewport)):
			color = wx.Colour(0, 255, 0, 128)
			gc.SetBrush(wx.Brush(color))
			gc.PushState()
			self._applyZoom(gc)
			# The brush draws itself where it would paint, which is in map
			# pixels - the same place the dab would land.
			self.brush.drawToGc(gc, self.mouse[0], self.mouse[1])
			gc.PopState()
			self.brushDrawnAt = self.mouse
			
	def _alpha(self, mask, box=None):
		return gfx.gmAlpha(mask, box)

	def _mapRectToClient(self, box):
		# This panel is scrolled rather than panned, so a box of map pixels
		# lands at its own position times the zoom.  Rounded outwards, plus a
		# pixel of slack for the edge the scaling lands between.
		left = int(math.floor(box[0] * self.scale)) - 1
		top = int(math.floor(box[1] * self.scale)) - 1
		right = int(math.ceil(box[2] * self.scale)) + 1
		bottom = int(math.ceil(box[3] * self.scale)) + 1
		return wx.Rect(left, top, right - left, bottom - top)

	def _onImageCreated(self):
		# Only when the image appears or changes size: doing this on every dab
		# put a layout pass in the middle of every mouse move.
		self._applyMinSize()

	def _updateGrid(self):
		super(GMMapPanel, self)._updateGrid()
		if (isinstance(self.brush, data.GridBrush)):
			self.brush.setGridSize(self.map.grid.size)
			
	def reset(self):
		super(GMMapPanel, self).reset()
		self.brush = None
		# Back to 100% for the incoming map; whatever zoom it was left at comes
		# back out of its own settings a moment later.  Set directly rather
		# than through setScale: there is no image to resize the panel around
		# yet, and this is not the GM changing anything.
		self.scale = GMMapPanel.DEFAULT_ZOOM
		
	def readSettings(self, settings):
		for child in settings:
			if (child.tag == "viewport"):
				self.setShowViewport(child.get("visible") == "true", user=False)
			elif (child.tag == "zoom"):
				# Snapped to the ladder, so a hand-edited file cannot leave the
				# view at a level nothing in the UI can name.
				self.setScale(self.nearestZoomLevel(float(child.get("scale"))),
							  user=False)
	
	def writeSettings(self, settings):
		settings.append(etree.Element("viewport",
									  visible=str(self.showViewport).lower()))
		settings.append(etree.Element("zoom", scale=str(self.scale)))
