import wx

from .brushmode import BrushMode


class FogMode(BrushMode):
	"""The main mode: paint the fog away with the left button, back with the
	   right, using the brush picked from this mode's own toolbar controls."""

	key = "fog"
	label = "Fog"
	icon = "mode-fog"
	hotkey = "CTRL+SHIFT+1"
	help = "Reveal and re-hide the map with the brush."

	paintNoun = "the fog"
	cursorColour = wx.Colour(0, 255, 0, 128)

	def applyDab(self, x, y):
		self.panel.map.applyBrush(self.brush, x, y)

	def unapplyDab(self, x, y):
		self.panel.map.unapplyBrush(self.brush, x, y)
