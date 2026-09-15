"""The base every input mode is built on, and the toolbar helpers that go
   with writing one."""
import wx


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

	# --- settings -------------------------------------------------------------
	# A mode's own settings belong to the GM rather than to any one map, so
	# they live in wx.Config alongside the recent-files list rather than in a
	# map file.  The frame calls these with the path already set to this
	# mode's own group.

	def readConfig(self, config):
		"""Called once, before the toolbar is built, so that a mode's controls
		   can start out where the GM last left them."""
		pass

	def writeConfig(self, config):
		"""Called as the window closes."""
		pass

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

	def onMouseLeave(self):
		"""The mouse has left the map, so anything the mode was showing at the
		   cursor is pointing at nothing."""
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
