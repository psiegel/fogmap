import wx

from .. import viewport

from .inputmode import InputMode, addIconButton


class ViewportMode(InputMode):
	"""Frame what the players can see by dragging a cyan rectangle around the
	   GM's map.

	   The rectangle is never stored anywhere: it is derived from the player
	   panel's own zoom and pan every time it is drawn, and a drag runs that
	   derivation backwards.  See ui/viewport.py."""

	key = "viewport"
	label = "Viewport"
	icon = "mode-viewport"
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
		self.fitButton = addIconButton(
			parent, sizer, "fit",
			"Zoom the player view out until the whole map fits.",
			self.onFit, border=0)

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
