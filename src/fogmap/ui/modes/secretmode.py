import wx

from .brushmode import BrushMode


class SecretMode(BrushMode):
	"""Paint in the secrets: the left button lets the layer over the map show
	   through, the right button covers it back up.

	   The same brushes as Fog mode, and a mask of the same shape, but a
	   different thing done with it.  The fog mask says whether the players
	   see a pixel at all; this one says which of the map's two images it
	   comes from, so painting here can change what a wall is without changing
	   whether it is on screen.

	   Available only on a map that has a secret layer to reveal.  On every
	   other map the toolbar greys this out, the way Viewport mode greys out
	   with no player window to frame."""

	key = "secret"
	label = "Secrets"
	icon = "mode-secret"
	hotkey = "CTRL+SHIFT+2"
	help = "Reveal and re-hide the secrets on the map with the brush."

	paintNoun = "the secrets"
	# Violet against Fog mode's green.  The two brushes are the same shapes on
	# the same map, and the cursor's colour is the only warning before the
	# button goes down that this one paints the other mask.
	cursorColour = wx.Colour(190, 90, 255, 128)

	def isAvailable(self):
		map = self.panel.map if (self.panel is not None) else None
		return (map is not None) and map.editable and map.hasSecrets

	def canPaintNow(self):
		return super(SecretMode, self).canPaintNow() and self.panel.map.hasSecrets

	def applyDab(self, x, y):
		self.panel.map.applySecretBrush(self.brush, x, y)

	def unapplyDab(self, x, y):
		self.panel.map.unapplySecretBrush(self.brush, x, y)
