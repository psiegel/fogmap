"""Painting a mask over the map with a brush, which two modes do.

   Fog mode paints what the players can see; Secret mode paints which of two
   images they see it from.  Everything between the two - the switcher, the
   size slider, the axis lock, and the business of keeping the cursor on
   screen without repainting the whole map to move it - is the same, and is
   here.  A subclass says what its dabs land on and what colour its cursor is
   drawn in."""
import wx

from ... import data

from .inputmode import IconRadioGroup, InputMode, addIcon


class BrushMode(InputMode):
	# What this mode's brush lays down, for the tooltips on its switcher.
	paintNoun = "the map"

	# What the brush outline is drawn in.  Deliberately different per mode:
	# the two brushes paint different masks and look otherwise identical, and
	# the colour under the cursor is the only thing saying which one is in
	# hand before the button goes down.
	cursorColour = wx.Colour(0, 255, 0, 128)

	def __init__(self, frame):
		super(BrushMode, self).__init__(frame)
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

	# --- what a subclass says -------------------------------------------------

	def canPaintNow(self):
		"""Whether there is anything for this mode's brush to paint on."""
		panel = self.panel
		return (panel is not None) and panel.canPaint()

	def applyDab(self, x, y):
		"""The left button: put this mode's mark down at a map point."""
		raise Exception("applyDab called on base BrushMode class.")

	def unapplyDab(self, x, y):
		"""The right button: take it away again."""
		raise Exception("unapplyDab called on base BrushMode class.")

	# --- toolbar --------------------------------------------------------------

	def brushTypes(self):
		"""What the brush switcher offers, as (name, icon, tooltip).  The name
		   is what onBrushTypeChanged matches on, and what reset puts back."""
		return (
			("None", "brush-none",
			 "No brush - the mouse does nothing to %s." % self.paintNoun),
			("Round", "brush-round", "A round brush, sized in map pixels."),
			("Square", "brush-square", "A square brush, sized in map pixels."),
			("Grid", "brush-grid", "A brush that paints whole grid cells at a "
								   "time.  Needs a grid on the map."),
		)

	def buildControls(self, parent, sizer):
		self.brushType = IconRadioGroup(parent, sizer, self.brushTypes(),
										self.onBrushTypeChanged)

		tip = ("How big the brush is.  Map pixels for a round or square brush, "
			   "cells for a grid one.")
		addIcon(parent, sizer, "size", tip)
		self.brushSize = wx.Slider(parent, -1, 1, 1, 100, size=(100, -1),
								   style=wx.SL_HORIZONTAL)
		self.brushSize.SetToolTip(tip)
		self.brushSize.Bind(wx.EVT_SLIDER, self.onBrushSizeChanged)
		sizer.Add(self.brushSize, 0, wx.ALIGN_CENTER_VERTICAL)

	def updateControls(self):
		if (self.brushType is None):
			return
		# A plain image handout has no fog to paint and nowhere to save it to,
		# and a map with no secret layer has no secrets to paint either.
		canPaint = self.canPaintNow()
		self.brushType.Enable(canPaint)
		self.brushSize.Enable(canPaint)

	def onBrushTypeChanged(self, brushType):
		panel = self.panel
		if (not self.canPaintNow()):
			return
		brush = None
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
				self.brushType.SetValue("None")
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
			self.brushType.SetValue("None")

	def leave(self):
		# Whatever is on screen was drawn by somebody else from here on.
		self.brushDrawnAt = None

	def onZoomChanged(self):
		self.brushDrawnAt = None

	def onMouseAt(self, pos):
		"""Alt has handed the mouse back.  The brush cursor is about to be drawn
		   again, and without this it would come back where it was when the key
		   went down and sit there until the mouse was moved.

		   A mouse off the map leaves it where it is, the same as walking off the
		   edge of the panel does."""
		if (pos is not None):
			self.mouse = pos

	def onGridChanged(self):
		if (isinstance(self.brush, data.GridBrush)):
			self.brush.setGridSize(self.panel.map.grid.size)

	# --- input ----------------------------------------------------------------

	def _canDab(self):
		return (self.brush != None) and self.canPaintNow()

	def onLeftDown(self, evt, pos):
		if (not self._canDab()):
			return False
		self.applyDab(pos[0], pos[1])
		self.lastBrushPt = self.brush.anchor(pos[0], pos[1])
		return True

	def onRightDown(self, evt, pos):
		if (not self._canDab()):
			return False
		self.unapplyDab(pos[0], pos[1])
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
					self.applyDab(self.mouse[0], self.mouse[1])
				elif (evt.RightIsDown()):
					self.unapplyDab(self.mouse[0], self.mouse[1])
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
		gc.SetBrush(wx.Brush(self.cursorColour))
		gc.PushState()
		self.panel._applyZoom(gc)
		# The brush draws itself where it would paint, which is in map pixels -
		# the same place the dab would land.
		self.brush.drawToGc(gc, self.mouse[0], self.mouse[1])
		gc.PopState()
		self.brushDrawnAt = self.mouse
