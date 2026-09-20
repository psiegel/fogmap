from ... import hex

from .grid import Grid


class HexGrid(Grid):
	def __init__(self, layout):
		super(HexGrid, self).__init__()
		self.layout = layout

	def drawGrid(self, gc, w, h, clip=None):
		hex.drawHexGridToGc(gc, w, h, self.layout, clip)

	def getGridCoords(self, ptPixel):
		return self.layout.pointToHex(ptPixel)

	def getGridUnitSize(self):
		# One cell along and one cell down, which for hexes is a column and a
		# row apart rather than the size of the hex itself.
		return (int(round(self.layout.stepX)), int(round(self.layout.stepY)))
