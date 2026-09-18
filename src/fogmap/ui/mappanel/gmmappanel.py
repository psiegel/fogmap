import math

import wx
from lxml import etree

from ... import gfx

from .. import viewport

from .mappanel import MapPanel


class GMMapPanel(MapPanel):
	# The zoom steps through a ladder of levels rather than a continuous scale,
	# so the wheel, the menu and the toolbar box can never disagree about where
	# on it the view is, and a level is always something with a name.
	ZOOM_LEVELS = (0.1, 0.25, 0.33, 0.5, 0.67, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0)
	DEFAULT_ZOOM = 1.0

	def __init__(self, parent):
		# What the mouse is for.  This panel knows only how to hand an event to
		# a mode and let one draw over the map; the modes themselves, and the
		# toolbar controls that come and go with them, are in ui/modes.py.
		self.modes = ()
		self.mode = None
		# Two things take the mouse off whatever the toolbar says the mode is:
		# holding Alt, which lends it to the viewport overlay for as long as it
		# is down, and a drag, which belongs to whoever started it until it ends.
		self.altMode = None
		self.altHeld = False
		self.dragMode = None
		self.modeListener = None
		self.cursorKey = None
		# Whether the players' visible area is outlined over the map.  It is
		# about the window rather than about any one mode, so it survives
		# switching between them - and Viewport mode, which is that outline,
		# shows one whatever this says.
		self.showViewport = False
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
		self.Bind(wx.EVT_LEAVE_WINDOW, self.onMouseLeave)
		
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
		if (self.mode != None):
			self.mode.onZoomChanged()
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

	def setPlayerPanel(self, panel):
		super(GMMapPanel, self).setPlayerPanel(panel)
		panel.setViewListener(self._onPlayerViewChanged)

	def onKeyDown(self, evt):
		# Alt swaps which mode has the mouse.  Noticing it here as well as on
		# the mouse itself is what brings the overlay up with the key, rather
		# than with the first twitch of the mouse after it.
		self._trackAlt(evt)
		super(GMMapPanel, self).onKeyDown(evt)

	def onKeyUp(self, evt):
		self._trackAlt(evt)
		super(GMMapPanel, self).onKeyUp(evt)

	def _onPlayerViewChanged(self):
		if (self.mode != None):
			self.mode.onPlayerViewChanged()
		# The outline is derived from the player view every time it is drawn, so
		# it is out of date the moment that view moves.
		if (self.viewportShown()):
			self.Refresh(False)

	def canPaint(self):
		"""A plain image has no fog to paint, and nowhere to save it to."""
		return (self.map != None) and self.map.editable

	# --- the player viewport --------------------------------------------------

	def viewportRect(self):
		"""What the players can see, in map pixels, or None if there is no
		   player window to be looking at anything."""
		player = self.playerPanel
		return player.getViewportRect() if (player != None) else None

	def canShowViewport(self):
		"""Nothing to outline without a window to outline it for."""
		return self.playerPanel != None

	def ownsViewport(self):
		"""Whether a mode is drawing the overlay itself, and so showing one
		   whether or not the GM asked for it: Viewport mode on the toolbar, or
		   any mode at all while Alt is borrowing it."""
		for mode in (self.mode, self.currentMode()):
			if ((mode != None) and mode.drawsViewport):
				return True
		return False

	def viewportShown(self):
		"""Whether an outline is on the map just now, either way."""
		return self.canShowViewport() and (self.showViewport or self.ownsViewport())

	def setShowViewport(self, show, user=True):
		"""user is False when a map's saved setting is being restored, which is
		   nothing to flag as a change."""
		show = bool(show)
		if (show == self.showViewport):
			return
		self.showViewport = show
		if (user and (self.playerPanel != None)):
			self.playerPanel._userViewChanged()
		self.Refresh()

	# --- modes ----------------------------------------------------------------

	def setModes(self, modes, altMode=None):
		"""The modes this panel can be put into, in the order the switcher
		   offers them, plus the one Alt borrows the mouse for."""
		self.modes = tuple(modes)
		self.altMode = altMode

	def setModeListener(self, listener):
		"""Called when the mode changes, so the toolbar can follow it with the
		   switcher and with that mode's own controls."""
		self.modeListener = listener

	def defaultMode(self):
		"""The mode a map opens in unless its file says otherwise."""
		return self.modes[0] if self.modes else None

	def modeByKey(self, key):
		for mode in self.modes:
			if (mode.key == key):
				return mode
		return None

	def setMode(self, mode, user=True):
		"""user is False when a map's saved mode is being restored, which is
		   nothing to flag as a change."""
		if ((mode is None) or (not mode.isAvailable())):
			mode = self.defaultMode()
		if (mode is self.mode):
			return
		if (self.mode != None):
			self.mode.leave()
		self.dragMode = None
		self.altHeld = False
		self.mode = mode
		if (mode != None):
			mode.enter()
		self.setModeCursor(None)
		if (self.modeListener != None):
			self.modeListener()
		if (user and (self.playerPanel != None)):
			self.playerPanel._userViewChanged()
		self.Refresh()

	def currentMode(self):
		"""Whichever mode the mouse is actually driving: the one holding an
		   unfinished drag, the Alt override while it is held, or the mode the
		   toolbar says we are in."""
		if (self.dragMode != None):
			return self.dragMode
		if (self.altHeld):
			return self.altMode
		return self.mode

	def _allModes(self):
		"""Every mode there is, the Alt one included: state that goes with the
		   open map has to be dropped whether or not a mode is on screen.  The
		   borrowed mode is usually one of the switcher's own, and is not told
		   anything twice for being lent out as well."""
		if ((self.altMode is None) or (self.altMode in self.modes)):
			return self.modes
		return self.modes + (self.altMode,)

	def _trackAlt(self, evt):
		"""Notice Alt going down or coming up.  It swaps which mode has the
		   mouse, and with it what is drawn over the map, so the panel has to
		   be repainted - but never mid-drag, which belongs to whichever mode
		   started it however the keyboard moves underneath it."""
		if (self.dragMode != None):
			return
		held = (self.altMode != None) and self.altMode.appliesTo(evt)
		if (held == self.altHeld):
			return
		self.altHeld = held
		self.setModeCursor(None)
		# The mode taking over has heard nothing of the mouse for as long as the
		# other one had it, so tell it where the mouse is before it draws.
		mode = self.currentMode()
		if (mode != None):
			mode.onMouseAt(self._mousePos())
		self.Refresh()

	def _mousePos(self):
		"""Where the mouse is now in map pixels, or None if it is not over this
		   panel at all.

		   Taken from the screen rather than from an event, because the mouse
		   changes hands on a key going down or coming up as well as on anything
		   the mouse itself does."""
		pt = self.ScreenToClient(wx.GetMousePosition())
		if (not self.GetClientRect().Contains(pt)):
			return None
		return self._clientToMap(pt)

	def setModeCursor(self, cursor):
		"""Modes say which cursor they want - a wx.CURSOR_ constant, or None
		   for the plain arrow.  Only changes actually reach wx: setting a
		   cursor on every mouse move is not free."""
		if (cursor == self.cursorKey):
			return
		self.cursorKey = cursor
		self.SetCursor(wx.Cursor(cursor if (cursor != None) else wx.CURSOR_ARROW))

	# --- mouse ----------------------------------------------------------------
	# Every handler undoes the zoom once, here, so that modes deal only in map
	# pixels; a button press that a mode claims also hands it the drag.

	def onLeftDown(self, evt):
		self._trackAlt(evt)
		mode = self.currentMode()
		if ((mode != None) and mode.onLeftDown(evt, self._clientToMap(evt.GetPosition()))):
			self.dragMode = mode

	def onRightDown(self, evt):
		self._trackAlt(evt)
		mode = self.currentMode()
		if ((mode != None) and mode.onRightDown(evt, self._clientToMap(evt.GetPosition()))):
			self.dragMode = mode

	def onMouseUp(self, evt):
		mode = self.currentMode()
		if (mode != None):
			mode.onMouseUp(evt, self._clientToMap(evt.GetPosition()))
		self.dragMode = None
		evt.Skip()

	def onRightDClick(self, evt):
		self._trackAlt(evt)
		mode = self.currentMode()
		if ((mode is None) or
			(not mode.onRightDClick(evt, self._clientToMap(evt.GetPosition())))):
			evt.Skip()

	def onWheel(self, evt):
		if (evt.ControlDown() or evt.CmdDown()):
			# Zoom this panel, keeping whatever is under the cursor there.  The
			# GM's own zoom belongs to the window rather than to any one mode.
			self.zoomStep(1 if (evt.GetWheelRotation() > 0) else -1,
						  evt.GetPosition())
			return
		self._trackAlt(evt)
		mode = self.currentMode()
		if ((mode is None) or
			(not mode.onWheel(evt, self._clientToMap(evt.GetPosition())))):
			# Leave the wheel alone so the scrolled panel keeps scrolling.
			evt.Skip()

	def onMouseMove(self, evt):
		self._dropStaleDrag(evt)
		self._trackAlt(evt)
		mode = self.currentMode()
		if (mode != None):
			mode.onMouseMove(evt, self._clientToMap(evt.GetPosition()))

	def _dropStaleDrag(self, evt):
		"""A button let go somewhere this panel never heard about - off the
		   edge of it, with nothing captured - would otherwise leave a drag
		   that nobody ever ends, and with it a mode holding the mouse for
		   good.  The next move with no button down is proof it is over."""
		if ((self.dragMode is None) or evt.LeftIsDown() or evt.RightIsDown()):
			return
		self.dragMode.onMouseUp(evt, self._clientToMap(evt.GetPosition()))
		self.dragMode = None

	def onMouseLeave(self, evt):
		"""The mouse has gone off the map.  A mode showing where it is - the
		   brush outline, the pointer the players are watching - has nothing to
		   show any more.  Never mid-drag: a drag that has wandered off the
		   edge of the panel is still a drag."""
		evt.Skip()
		mode = self.currentMode()
		if ((mode != None) and (self.dragMode is None)):
			mode.onMouseLeave()

	def onCaptureLost(self, evt):
		self.dragMode = None
		for mode in self._allModes():
			mode.onCaptureLost()

	# --- drawing --------------------------------------------------------------

	def _draw(self, gc, box):
		super(GMMapPanel, self)._draw(gc, box)
		# Under whatever the modes draw: a brush outline or the pointer is what
		# the GM is doing, and this is only there to be glanced at.
		self._drawViewport(gc)
		current = self.currentMode()
		# The mode on the toolbar draws whether or not it has the mouse, so that
		# Alt borrowing it for a moment does not take whatever that mode has to
		# show off the screen as well.  It is told it has lost the mouse, so it
		# can drop a cursor - a brush outline, the players' arrow - that would
		# no longer do anything.
		if (self.mode != None):
			self.mode.draw(gc, self.mode is current)
		if ((current != None) and (current is not self.mode)):
			current.draw(gc, True)

	def _drawViewport(self, gc):
		"""A faint outline of what the players can see, for the modes that do
		   not draw one of their own.  There is nothing to take hold of here:
		   the mouse belongs to whatever mode the toolbar is in until Alt asks
		   for it, and then Viewport mode draws its own over the top."""
		if ((not self.showViewport) or self.ownsViewport()):
			return
		rect = self.viewportRect()
		if (rect is None):
			return
		# Drawn in panel coordinates rather than under the zoom, so the outline
		# stays a line however far the map is zoomed out.
		viewport.drawFaint(gc, [v * self.scale for v in rect])

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

	def _applyMapTransform(self, gc):
		self._applyZoom(gc)

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
		for mode in self._allModes():
			mode.onGridChanged()
			
	def reset(self):
		super(GMMapPanel, self).reset()
		for mode in self._allModes():
			mode.reset()
		# Back to the main mode for the incoming map, with no outline over it;
		# whatever it was left showing comes back out of its own settings a
		# moment later.
		self.setMode(self.defaultMode(), user=False)
		self.setShowViewport(False, user=False)
		# Back to 100% likewise.  Set directly rather than through setScale:
		# there is no image to resize the panel around yet, and this is not the
		# GM changing anything.
		self.scale = GMMapPanel.DEFAULT_ZOOM
		
	def readSettings(self, settings):
		for child in settings:
			if (child.tag == "mode"):
				self.setMode(self.modeByKey(child.get("name")), user=False)
			elif (child.tag == "viewport"):
				# The flag files have carried since long before the viewport
				# became a mode of its own, and it still means what it always
				# did: whether the outline is over the map.
				self.setShowViewport(child.get("visible") == "true", user=False)
			elif (child.tag == "zoom"):
				# Snapped to the ladder, so a hand-edited file cannot leave the
				# view at a level nothing in the UI can name.
				self.setScale(self.nearestZoomLevel(float(child.get("scale"))),
							  user=False)
	
	def writeSettings(self, settings):
		if (self.mode != None):
			settings.append(etree.Element("mode", name=self.mode.key))
		settings.append(etree.Element("viewport",
									  visible="true" if (self.showViewport) else "false"))
		settings.append(etree.Element("zoom", scale=str(self.scale)))
