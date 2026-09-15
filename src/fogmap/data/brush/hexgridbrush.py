from ... import hex

from .gridbrush import GridBrush


class HexGridBrush(GridBrush):
	def __init__(self, hexSize, brushSize):
		self.hexSize = hexSize
		self.brushSize = brushSize
		
	def getSize(self):
		return self.brushSize

	def setSize(self, size):
		self.brushSize = size
		
	def setGridSize(self, size):
		self.hexSize = size

	def drawToGc(self, gc, x, y):
		hex.fillHexCircleToGc(gc, (x, y), self.brushSize, self.hexSize)

	def drawToImage(self, image, x, y, color):
		hex.fillHexeCircleToImage(image, (x, y), self.brushSize, self.hexSize, color)

	def anchor(self, x, y):
		# Everything this brush draws is worked out from the hex the point
		# falls in, both on screen and into the mask.
		return hex.pointToHexCoords((x, y), self.hexSize)

	def bounds(self, x, y):
		# Which hexes a circle of this radius picks up depends on where the
		# centre falls within its own hex, so this is deliberately loose: one
		# hex of slack in every direction beyond the nominal reach.
		reach = (self.brushSize + 2) * self.hexSize
		return (x - reach, y - reach, x + reach, y + reach)
