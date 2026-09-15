"""What the mouse does over the GM map, and what the toolbar offers while it
   is doing it.

   The left-most control on the toolbar picks the mode.  The panel routes its
   mouse events to whichever one is current and lets it draw over the map; the
   toolbar shows that mode's own controls and hides the rest.

   PlayerDriveMode is the odd one out: it is not on the switcher, because it
   lasts only as long as Alt is held.  The panel hands it the mouse for that
   long and then gives it straight back.
"""
import wx

from .. import data

from . import viewport

# Room to breathe between a mode's own toolbar controls.
BORDER = 4


def addLabel(parent, sizer, text):
	sizer.Add(wx.StaticText(parent, -1, text), 0,
			  wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, BORDER)


class InputMode(object):
	# key    - what a map file stores, so a map comes back in the mode it was
	#          left in whatever order the switcher happens to be in.
	# label  - what the switcher and the View menu call it.
	# hotkey - accelerator for that menu item, or None.
	# help   - the one-line description the menu shows.
	key = None
	label = None
	hotkey = None
	help = ""

	def __init__(self, frame):
		self.frame = frame

	@property
	def panel(self):
		return self.frame.panel

	@property
	def playerPanel(self):
		panel = self.panel
		return panel.playerPanel if (panel is not None) else None

	# --- toolbar --------------------------------------------------------------

	def buildControls(self, parent, sizer):
		"""Add this mode's own controls to its page of the toolbar book.  A
		   mode with nothing of its own to offer need not override this."""
		pass

	def updateControls(self):
		"""Bring those controls into line with the open document."""
		pass

	def isAvailable(self):
		"""Whether the mode can be entered at all just now."""
		return True

	# --- lifecycle ------------------------------------------------------------

	def enter(self):
		"""The mode has just been switched to."""
		pass

	def leave(self):
		"""The mode has just been switched away from."""
		pass

	def reset(self):
		"""The map is being swapped out from under every mode."""
		pass

	def onGridChanged(self):
		pass

	def onZoomChanged(self):
		"""The GM's own zoom has changed, so whatever the mode last drew is
		   no longer where it was."""
		pass

	def onPlayerViewChanged(self):
		pass

	def onCaptureLost(self):
		pass

	# --- input ----------------------------------------------------------------
	# pos is the mouse in map pixels: the panel undoes its own zoom once, before
	# any of this, rather than in each of the things the mouse can be driving.
	# A handler returns True if it dealt with the event, and a button press that
	# says True keeps the drag that follows, whatever the keyboard does meanwhile.

	def onLeftDown(self, evt, pos):
		return False

	def onRightDown(self, evt, pos):
		return False

	def onMouseUp(self, evt, pos):
		return False

	def onMouseMove(self, evt, pos):
		return False

	def onWheel(self, evt, pos):
		return False

	def onRightDClick(self, evt, pos):
		return False

	def draw(self, gc, active):
		"""Whatever the mode overlays on the map.

		   active is False when something else has the mouse for the moment -
		   Alt driving the player view - so that a mode can go on showing what
		   it is about without showing a cursor that would do nothing."""
		pass


class FogMode(InputMode):
	"""The main mode: paint the fog away with the left button, back with the
	   right, using the brush picked from this mode's own toolbar controls."""

	key = "fog"
	label = "Fog"
	hotkey = "CTRL+SHIFT+1"
	help = "Reveal and re-hide the map with the brush."

	BRUSH_TYPES = ("None", "Round", "Square", "Grid")

	def __init__(self, frame):
		super(FogMode, self).__init__(frame)
		self.brush = None
		self.brushType = None
		self.brushSize = None
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

	# --- toolbar --------------------------------------------------------------

	def buildControls(self, parent, sizer):
		addLabel(parent, sizer, "Brush Type: ")
		self.brushType = wx.Choice(parent, -1, choices=list(FogMode.BRUSH_TYPES))
		self.brushType.SetStringSelection("None")
		self.brushType.Bind(wx.EVT_CHOICE, self.onBrushTypeChanged)
		sizer.Add(self.brushType, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, BORDER * 2)

		addLabel(parent, sizer, "Brush Size: ")
		self.brushSize = wx.Slider(parent, -1, 1, 1, 100, size=(100, -1),
								   style=wx.SL_HORIZONTAL)
		self.brushSize.Bind(wx.EVT_SLIDER, self.onBrushSizeChanged)
		sizer.Add(self.brushSize, 0, wx.ALIGN_CENTER_VERTICAL)

	def updateControls(self):
		if (self.brushType is None):
			return
		# A plain image handout has no fog to paint and nowhere to save it to.
		canPaint = (self.panel is not None) and self.panel.canPaint()
		self.brushType.Enable(canPaint)
		self.brushSize.Enable(canPaint)

	def onBrushTypeChanged(self, evt):
		panel = self.panel
		if (not panel.canPaint()):
			return
		brush = None
		brushType = self.brushType.GetStringSelection()
		self.updateBrushSizeSlider(brushType == "Grid")
		if (brushType == "Round"):
			brush = data.RoundFreehandBrush(self.getBrushSize())
		elif (brushType == "Square"):
			# TODO: We could support rects if we wanted
			size = self.getBrushSize()
			brush = data.SquareFreehandBrush(size, size)
		elif (brushType == "Grid"):
			if (panel.map.grid.type == data.Grid.GRID_NONE):
				dlg = wx.MessageDialog(self.frame,
									   'Cannot set brush type to grid unless grid is enabled.',
									   'Bad Brush Choice', wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()
				self.brushType.SetStringSelection("None")
			elif (panel.map.grid.type == data.Grid.GRID_SQUARE):
				brush = data.SquareGridBrush(panel.map.grid.size, self.getBrushSize())
			elif (panel.map.grid.type == data.Grid.GRID_HEX):
				brush = data.HexGridBrush(panel.map.grid.size, self.getBrushSize())
		self.setBrush(brush)
		panel.Refresh()

	def onBrushSizeChanged(self, evt):
		if (self.brush != None):
			self.brush.setSize(self.getBrushSize())
			self.panel.Refresh()

	def getBrushSize(self):
		return self.brushSize.GetValue()

	def updateBrushSizeSlider(self, isGrid):
		if (isGrid):
			newValue = (self.brushSize.GetValue() * 10 // self.brushSize.GetMax())
			self.brushSize.SetRange(1, 10)
			self.brushSize.SetValue(newValue)
		else:
			newValue = 5 + (self.brushSize.GetValue() * 495 // self.brushSize.GetMax())
			self.brushSize.SetRange(5, 500)
			self.brushSize.SetValue(newValue)

	# --- lifecycle ------------------------------------------------------------

	def setBrush(self, brush):
		self.brush = brush
		# Anchors are not comparable between brushes - a hex brush counts in
		# hexes, a freehand one in pixels - so the last one means nothing now.
		self.lastBrushPt = None

	def reset(self):
		self.setBrush(None)
		self.brushDrawnAt = None
		if (self.brushType != None):
			# The brush goes with the map it was picked for, so the toolbar has
			# to agree or the GM is left with a type selected and no brush.
			self.brushType.SetStringSelection("None")

	def leave(self):
		# Whatever is on screen was drawn by somebody else from here on.
		self.brushDrawnAt = None

	def onZoomChanged(self):
		self.brushDrawnAt = None

	def onGridChanged(self):
		if (isinstance(self.brush, data.GridBrush)):
			self.brush.setGridSize(self.panel.map.grid.size)

	# --- input ----------------------------------------------------------------

	def _canDab(self):
		return (self.brush != None) and self.panel.canPaint()

	def onLeftDown(self, evt, pos):
		if (not self._canDab()):
			return False
		self.panel.map.applyBrush(self.brush, pos[0], pos[1])
		self.lastBrushPt = self.brush.anchor(pos[0], pos[1])
		return True

	def onRightDown(self, evt, pos):
		if (not self._canDab()):
			return False
		self.panel.map.unapplyBrush(self.brush, pos[0], pos[1])
		self.lastBrushPt = self.brush.anchor(pos[0], pos[1])
		return True

	def onMouseMove(self, evt, pos):
		panel = self.panel
		panel.setModeCursor(None)

		self.axisLock = (evt.ShiftDown(), evt.ControlDown())
		if (not self.axisLock[0] and not self.axisLock[1]):
			self.mouse = pos
		elif (self.axisLock[0]):
			self.mouse = (self.mouse[0], pos[1])
		elif (self.axisLock[1]):
			self.mouse = (pos[0], self.mouse[1])

		# Where the brush would next leave its mark.  This comes off the brush
		# rather than off the displayed grid: a grid being switched on says
		# nothing about whether the brush in hand snaps to it, and taking it
		# from the grid meant a freehand brush on a gridded map only painted
		# where it crossed a cell boundary.
		if (self._canDab()):
			ptBrush = self.brush.anchor(self.mouse[0], self.mouse[1])
			if (ptBrush != self.lastBrushPt):
				if (evt.LeftIsDown()):
					panel.map.applyBrush(self.brush, self.mouse[0], self.mouse[1])
				elif (evt.RightIsDown()):
					panel.map.unapplyBrush(self.brush, self.mouse[0], self.mouse[1])
				self.lastBrushPt = ptBrush

		# Outside that guard on purpose.  The guard is about where the brush
		# next paints, which a grid snaps to whole cells; the cursor follows
		# the mouse itself and has to keep up with it whether or not a dab was
		# laid down.  Painting invalidates the dab's own box as well, and wx
		# folds the two into one repaint.
		self._refreshBrushCursor()
		return True

	def _brushRect(self, pt):
		"""Where a brush at pt - a map point - lands on the panel."""
		return self.panel._mapRectToClient(self.brush.bounds(pt[0], pt[1]))

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
		self.panel.RefreshRect(rect.Inflate(2, 2))

	def draw(self, gc, active):
		self.brushDrawnAt = None
		if ((self.brush is None) or (not active)):
			return
		gc.SetBrush(wx.Brush(wx.Colour(0, 255, 0, 128)))
		gc.PushState()
		self.panel._applyZoom(gc)
		# The brush draws itself where it would paint, which is in map pixels -
		# the same place the dab would land.
		self.brush.drawToGc(gc, self.mouse[0], self.mouse[1])
		gc.PopState()
		self.brushDrawnAt = self.mouse


class ViewportMode(InputMode):
	"""Frame what the players can see by dragging a cyan rectangle around the
	   GM's map.

	   The rectangle is never stored anywhere: it is derived from the player
	   panel's own zoom and pan every time it is drawn, and a drag runs that
	   derivation backwards.  See ui/viewport.py."""

	key = "viewport"
	label = "Viewport"
	hotkey = "CTRL+SHIFT+2"
	help = "Move and resize the area the players can see."

	TOLERANCE = 6
	HANDLE_SIZE = 9
	MOVE = "move"

	def __init__(self, frame):
		super(ViewportMode, self).__init__(frame)
		self.handle = None
		self.base = None
		self.grabPt = None
		self.fitButton = None

	# --- toolbar --------------------------------------------------------------

	def buildControls(self, parent, sizer):
		self.fitButton = wx.Button(parent, -1, "Fit to Map")
		self.fitButton.SetToolTip("Zoom the player view out until the whole map fits.")
		self.fitButton.Bind(wx.EVT_BUTTON, self.onFit)
		sizer.Add(self.fitButton, 0, wx.ALIGN_CENTER_VERTICAL)

	def updateControls(self):
		if (self.fitButton != None):
			self.fitButton.Enable(self.isAvailable() and (self.panel.map != None))

	def onFit(self, evt):
		self.frame.onFitPlayerView(evt)

	def isAvailable(self):
		"""Nothing to frame without a window to frame it for."""
		return self.playerPanel is not None

	# --- the rectangle --------------------------------------------------------

	def rect(self):
		"""The player viewport in map pixels, or None if there is nothing to show."""
		player = self.playerPanel
		return player.getViewportRect() if (player is not None) else None

	def tolerance(self):
		"""The grab tolerance is a distance on screen, so how much of the map
		   it covers depends on the zoom."""
		return ViewportMode.TOLERANCE / self.panel.scale

	def handleAt(self, pos):
		rect = self.rect()
		if (rect is None):
			return None
		return viewport.hitTest(rect, pos, self.tolerance())

	# --- lifecycle ------------------------------------------------------------

	def leave(self):
		self.endDrag()

	def reset(self):
		self.endDrag()

	def onPlayerViewChanged(self):
		self.panel.Refresh(False)

	def onCaptureLost(self):
		self.handle = None
		self.base = None
		self.grabPt = None

	# --- input ----------------------------------------------------------------

	def onLeftDown(self, evt, pos):
		return self.grab(pos)

	def onRightDown(self, evt, pos):
		return self.grab(pos)

	def grab(self, pos):
		"""Take hold of the overlay: an edge or corner resizes, anywhere else moves."""
		rect = self.rect()
		if (rect is None):
			return False
		self.handle = viewport.hitTest(rect, pos, self.tolerance()) or ViewportMode.MOVE
		self.base = rect
		self.grabPt = pos
		if (not self.panel.HasCapture()):
			self.panel.CaptureMouse()
		return True

	def endDrag(self):
		self.handle = None
		self.base = None
		self.grabPt = None
		panel = self.panel
		if ((panel is not None) and panel.HasCapture()):
			panel.ReleaseMouse()

	def onMouseUp(self, evt, pos):
		self.endDrag()
		return False

	def onMouseMove(self, evt, pos):
		if (self.handle is not None):
			if (evt.LeftIsDown() or evt.RightIsDown()):
				self.drag(pos)
			else:
				self.endDrag()
			return True
		if (self.rect() is None):
			self.panel.setModeCursor(None)
			return True
		# The overlay owns the mouse: edges and corners resize, the rest grabs.
		self.panel.setModeCursor(viewport.CURSORS.get(self.handleAt(pos), wx.CURSOR_HAND))
		return True

	def drag(self, pos):
		player = self.playerPanel
		if ((self.base is None) or (player is None)):
			return
		if (self.handle == ViewportMode.MOVE):
			# Both points are already map pixels, so the rectangle follows the
			# cursor one-for-one at any zoom.
			rect = (self.base[0] + pos[0] - self.grabPt[0],
					self.base[1] + pos[1] - self.grabPt[1],
					self.base[2], self.base[3])
		else:
			aspect = player.getViewportAspect()
			if (aspect is None):
				return
			# Scale limits become width limits, so a drag cannot outrun the zoom range.
			cw = player.GetClientSize()[0]
			rect = viewport.resize(self.base, self.handle, pos, aspect,
								   cw / float(player.MAX_SCALE),
								   cw / float(player.MIN_SCALE))
		player.showMapRect(rect)

	def draw(self, gc, active):
		rect = self.rect()
		if (rect is None):
			return
		# Drawn in panel coordinates rather than under the zoom, so the outline
		# stays a line and the handles stay grabbable however far the map is
		# zoomed out.
		viewport.draw(gc, [v * self.panel.scale for v in rect],
					  ViewportMode.HANDLE_SIZE)


class PlayerDriveMode(InputMode):
	"""Holding Alt hands the mouse to the player view, whatever mode the
	   toolbar is in: drag to pan it, wheel to zoom it about whatever the GM is
	   pointing at, right double-click to recentre it.

	   Not on the switcher, and not something a map file can be left in: it
	   lasts exactly as long as the key is held."""

	key = "drive"
	label = "Player View"

	def __init__(self, frame):
		super(PlayerDriveMode, self).__init__(frame)
		self.anchor = None

	def appliesTo(self, evt):
		return (self.playerPanel is not None) and evt.AltDown()

	def reset(self):
		self.anchor = None

	def onCaptureLost(self):
		self.anchor = None

	def onLeftDown(self, evt, pos):
		self.anchor = pos
		return True

	def onRightDown(self, evt, pos):
		self.anchor = pos
		return True

	def onMouseUp(self, evt, pos):
		self.anchor = None
		return False

	def onMouseMove(self, evt, pos):
		self.panel.setModeCursor(wx.CURSOR_HAND)
		if (evt.LeftIsDown() or evt.RightIsDown()):
			if (self.anchor is not None):
				# Both points are map pixels already, whatever the zoom.
				self.playerPanel.panByMapDelta(pos[0] - self.anchor[0],
											   pos[1] - self.anchor[1])
			self.anchor = pos
		else:
			self.anchor = None
		return True

	def onWheel(self, evt, pos):
		increment = 0.1 if (evt.GetWheelRotation() > 0) else -0.1
		self.playerPanel.zoomAtMapPoint(increment, pos)
		return True

	def onRightDClick(self, evt, pos):
		self.playerPanel.recentre()
		return True


# What the switcher offers, in the order it offers them.  The first is the
# mode a map opens in unless its file says otherwise.
MODES = (FogMode, ViewportMode)
