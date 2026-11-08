import wx

from .. import viewport
from ..mappanel import PlayerMapPanel

from .inputmode import BORDER, InputMode, addIconButton


class ViewportMode(InputMode):
	"""Frame what the players can see by dragging a cyan rectangle around the
	   GM's map.

	   The rectangle is never stored anywhere: it is derived from the player
	   panel's own zoom and pan every time it is drawn, and a drag runs that
	   derivation backwards.  See ui/viewport.py.

	   This is also the mode Alt borrows: holding it hands this one the mouse
	   whatever the toolbar is set to, so the players' view can be moved without
	   putting the brush or the pen down first."""

	key = "viewport"
	label = "Viewport"
	icon = "mode-viewport"
	hotkey = "CTRL+SHIFT+4"
	help = "Move and resize the area the players can see."

	# This mode is the overlay, so it shows one whatever the GM's own
	# show-the-viewport setting says, and draws it itself rather than leaving
	# the panel to draw a faint one underneath.
	drawsViewport = True

	TOLERANCE = 6
	HANDLE_SIZE = 9
	MOVE = "move"

	def __init__(self, frame):
		super(ViewportMode, self).__init__(frame)
		self.handle = None
		self.base = None
		self.grabPt = None
		self.fitButton = None
		self.rotateCcwButton = None
		self.rotateCwButton = None
		self.zoomButtons = []
		self.zoomFont = None

	# --- toolbar --------------------------------------------------------------

	def buildControls(self, parent, sizer):
		self.fitButton = addIconButton(
			parent, sizer, "fit",
			"Zoom the player view out until the whole map fits.",
			self.onFit)
		self.rotateCcwButton = addIconButton(
			parent, sizer, "rotate-ccw",
			"Turn the player view a quarter turn counter-clockwise.",
			self.onRotateCcw)
		self.rotateCwButton = addIconButton(
			parent, sizer, "rotate-cw",
			"Turn the player view a quarter turn clockwise.",
			self.onRotateCw, border=BORDER * 4)

		# The zoom slots: numbers rather than icons, because which one is which
		# is the whole point of them.
		self.zoomButtons = []
		for slot in range(PlayerMapPanel.ZOOM_SLOTS):
			button = wx.Button(parent, -1, str(slot + 1), style=wx.BU_EXACTFIT)
			button.Bind(wx.EVT_BUTTON, lambda evt, slot=slot: self.onZoomSlot(slot))
			last = (slot == PlayerMapPanel.ZOOM_SLOTS - 1)
			sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
					  0 if last else BORDER)
			self.zoomButtons.append(button)
		self.zoomFont = self.zoomButtons[0].GetFont() if self.zoomButtons else None

	def updateControls(self):
		enable = self.isAvailable() and (self.panel.map != None)
		for button in (self.fitButton, self.rotateCcwButton, self.rotateCwButton):
			if (button != None):
				button.Enable(enable)
		self.updateZoomButtons(enable)

	def updateZoomButtons(self, enable=None):
		"""Bold where a zoom is stored, and the tooltip says which."""
		if (enable is None):
			enable = self.isAvailable() and (self.panel.map != None)
		memory = self.playerPanel.zoomMemory if (self.playerPanel != None) else None
		for slot, button in enumerate(self.zoomButtons):
			button.Enable(enable)
			scale = memory[slot] if (memory != None) else None
			font = wx.Font(self.zoomFont)
			if (scale is None):
				button.SetToolTip("Zoom %d: empty.  Click to remember the player "
								  "view's current zoom here." % (slot + 1))
			else:
				font.MakeBold()
				button.SetToolTip("Zoom %d: %d%%.  Click to zoom the player view "
								  "to it; Shift+click to remember the current zoom "
								  "instead." % (slot + 1, round(scale * 100)))
			button.SetFont(font)

	def onZoomSlot(self, slot):
		"""Click an empty slot and it takes the current zoom; click a full one
		   and the player view goes to it.  Shift+click always stores."""
		player = self.playerPanel
		if ((player is None) or (self.panel.map is None)):
			return
		if ((player.zoomMemory[slot] is None) or wx.GetKeyState(wx.WXK_SHIFT)):
			player.storeZoom(slot)
			self.updateZoomButtons()
		else:
			player.recallZoom(slot)

	def onFit(self, evt):
		self.frame.onFitPlayerView(evt)

	def onRotateCw(self, evt):
		self.frame.onRotatePlayerView(1)

	def onRotateCcw(self, evt):
		self.frame.onRotatePlayerView(-1)

	def isAvailable(self):
		"""Nothing to frame without a window to frame it for."""
		return self.playerPanel is not None

	def appliesTo(self, evt):
		"""Alt borrows this mode from wherever the toolbar happens to be, and
		   gives it straight back when the key comes up.  With no player window
		   there is nothing to frame, so the key does nothing at all."""
		return evt.AltDown() and self.isAvailable()

	# --- the rectangle --------------------------------------------------------

	def rect(self):
		"""The player viewport in map pixels, or None if there is nothing to show."""
		panel = self.panel
		return panel.viewportRect() if (panel is not None) else None

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
		self.panel.setModeCursor(self.cursorAt(pos))
		return True

	def onMouseAt(self, pos):
		"""Alt has just handed the mouse over.  The overlay it brings up can be
		   grabbed straight away, so the cursor says so without waiting for the
		   mouse to be moved first."""
		self.panel.setModeCursor(self.cursorAt(pos))

	def cursorAt(self, pos):
		"""The overlay owns the mouse: edges and corners resize, the rest grabs.
		   Nothing to grab, and it is the plain arrow."""
		if ((pos is None) or (self.rect() is None)):
			return None
		return viewport.CURSORS.get(self.handleAt(pos), wx.CURSOR_HAND)

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
			# Scale limits become width limits, so a drag cannot outrun the zoom
			# range.  The width along the map, which is the window's height
			# while the players' view is turned a quarter.
			cw = player.getViewportClientSize()[0]
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
