import wx

from ... import data

from .inputmode import BORDER, InputMode, addLabel


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
