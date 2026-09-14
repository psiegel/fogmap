import wx
import numpy as np
from lxml import etree

import gfx
import data

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
	def __init__(self, parent):
		self.brush = None
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
		
		super(GMMapPanel, self).__init__(parent)

		self.Bind(wx.EVT_LEFT_DOWN, self.onLeftDown)
		self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
		self.Bind(wx.EVT_LEFT_UP, self.onMouseUp)
		self.Bind(wx.EVT_RIGHT_UP, self.onMouseUp)
		self.Bind(wx.EVT_RIGHT_DCLICK, self.onRightDClick)
		self.Bind(wx.EVT_MOUSEWHEEL, self.onWheel)
		self.Bind(wx.EVT_MOTION, self.onMouseMove)
		self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.onCaptureLost)
		
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

	def _viewportHitTest(self, pos):
		rect = self._viewportRect()
		if (rect is None):
			return None
		return viewport.hitTest(rect, pos, GMMapPanel.VIEWPORT_TOLERANCE)

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
		handle = viewport.hitTest(rect, pos, GMMapPanel.VIEWPORT_TOLERANCE)
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
			# The rectangle follows the cursor one-for-one; the GM panel is 1:1.
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
		if (self._grabViewport(evt.GetPosition())):
			return
		if (self._forwardsToPlayer(evt)):
			self.forwardAnchor = evt.GetPosition()
			return
		if ((self.brush != None) and self.canPaint()):
			pos = evt.GetPosition()
			self.map.applyBrush(self.brush, pos[0], pos[1])
			self.lastBrushPt = self.brush.anchor(pos[0], pos[1])
			
	def onRightDown(self, evt):
		if (self._grabViewport(evt.GetPosition())):
			return
		if (self._forwardsToPlayer(evt)):
			self.forwardAnchor = evt.GetPosition()
			return
		if ((self.brush != None) and self.canPaint()):
			pos = evt.GetPosition()
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
		if (self.viewportHandle is not None):
			if (evt.LeftIsDown() or evt.RightIsDown()):
				self._dragViewport(evt.GetPosition())
			else:
				self._endViewportDrag()
			return

		if (self.viewportActive()):
			# The overlay owns the mouse: edges and corners resize, the rest grabs.
			self._setForwarding(False)
			self.forwardAnchor = None
			self.viewportHover = self._viewportHitTest(evt.GetPosition())
			self._setCursorFor(self.viewportHover or GMMapPanel.VIEWPORT_MOVE)
			return

		if (self._forwardsToPlayer(evt)):
			self._setForwarding(True)
			self._forwardDrag(evt)
			return
		self._setForwarding(False)
		self.forwardAnchor = None
		self.viewportHover = None
		self._setCursorFor(None)

		self.axisLock = (evt.ShiftDown(), evt.ControlDown())
		mousePos = evt.GetPosition()
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
		x0, y0, x1, y1 = self.brush.bounds(pt[0], pt[1])
		return wx.Rect(x0, y0, x1 - x0, y1 - y0)

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
			viewport.draw(gc, rect, GMMapPanel.VIEWPORT_HANDLE_SIZE)

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
			gc.DrawBitmap(self._mapBitmap(),
						  0, 
						  0,				  
						  bsz.width, 
						  bsz.height)		

	def _drawGrid(self, gc, box):
		if (self.grid != None):
			# Base grid.  This panel draws 1:1, so the box is already in map
			# coordinates.
			bsz = self.mapImg.GetSize()
			self.grid.drawGrid(gc, bsz.width, bsz.height, box)	
			
	def _drawBrush(self, gc):
		# Cursor
		self.brushDrawnAt = None
		if ((self.brush != None) and (not self.forwarding) and (not self.showViewport)):
			color = wx.Colour(0, 255, 0, 128)
			gc.SetBrush(wx.Brush(color))
			self.brush.drawToGc(gc, self.mouse[0], self.mouse[1])
			self.brushDrawnAt = self.mouse
			
	def _alpha(self, mask, box=None):
		return gfx.gmAlpha(mask, box)

	def _mapRectToClient(self, box):
		# This panel draws the map 1:1 and is itself scrolled, so its own
		# coordinates are map pixels.
		return wx.Rect(box[0], box[1], box[2] - box[0], box[3] - box[1])

	def _onImageCreated(self):
		# Only when the image appears or changes size: doing this on every dab
		# put a layout pass in the middle of every mouse move.
		self.SetMinSize(self.mapImg.GetSize())

	def _updateGrid(self):
		super(GMMapPanel, self)._updateGrid()
		if (isinstance(self.brush, data.GridBrush)):
			self.brush.setGridSize(self.map.grid.size)
			
	def reset(self):
		super(GMMapPanel, self).reset()
		self.brush = None
		
	def readSettings(self, settings):
		for child in settings:
			if (child.tag == "viewport"):
				self.setShowViewport(child.get("visible") == "true", user=False)
	
	def writeSettings(self, settings):
		settings.append(etree.Element("viewport",
									  visible=str(self.showViewport).lower()))
