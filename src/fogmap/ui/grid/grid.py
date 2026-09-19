"""The base a drawable grid presents to the map panels."""


class Grid(object):
	"""A grid of one particular kind, built from the settings on the map's own
	   grid."""

	def drawGrid(self, gc, w, h, clip=None):
		"""clip is the box of map being repainted, as (x0, y0, x1, y1), or None
		   for the whole map.  Honouring it is what keeps a grid affordable:
		   drawn in full, a fine grid on a large map is tens of thousands of
		   strokes, and it was being redrawn on every repaint."""
		raise Exception("Call to drawGrid on base Grid class.")

	def getGridCoords(self, ptPixel):
		raise Exception("Call to fillCircle on base Grid class.")

	def getGridUnitSize(self):
		raise Exception("Call to fillCircle on base Grid class.")
