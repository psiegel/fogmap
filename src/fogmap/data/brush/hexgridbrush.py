import math

from ... import hex

from .gridbrush import GridBrush


class HexGridBrush(GridBrush):
	"""Paints whole hexes at a time: the one under the cursor and every hex
	   within brushSize-1 steps of it, whatever shape and whichever way up the
	   map's hexes are."""

	def __init__(self, grid, brushSize):
		self.brushSize = brushSize
		self.setGrid(grid)
		
	def getSize(self):
		return self.brushSize

	def setSize(self, size):
		self.brushSize = size
		
	def setGrid(self, grid):
		self.layout = hex.HexLayout.forGrid(grid)

	def drawToGc(self, gc, x, y):
		hex.fillHexCircleToGc(gc, (x, y), self.brushSize, self.layout)

	def drawToImage(self, image, x, y, color):
		hex.fillHexCircleToImage(image, (x, y), self.brushSize, self.layout, color)

	def anchor(self, x, y):
		# Everything this brush draws is worked out from the hex the point
		# falls in, both on screen and into the mask.
		return self.layout.pointToHex((x, y))

	def bounds(self, x, y):
		# The hexes this would actually paint, rather than a guess at how far
		# they reach: which ones a patch of that size picks up depends on where
		# the middle falls, and the guess it replaces was a hex of slack in
		# every direction.
		x0, y0, x1, y1 = self.layout.circleBounds((x, y), self.brushSize)
		return (int(math.floor(x0)) - 1, int(math.floor(y0)) - 1,
				int(math.ceil(x1)) + 1, int(math.ceil(y1)) + 1)
