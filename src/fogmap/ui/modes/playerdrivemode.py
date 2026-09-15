import wx

from .inputmode import InputMode


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
