from ... import hex

from .grid import Grid


class HexGrid(Grid):
	def __init__(self, hexSize):
		super(HexGrid, self).__init__()
		self.hexSize = hexSize

	def drawGrid(self, gc, w, h, clip=None):
		hex.drawHexGridToGc(gc, w, h, self.hexSize, clip)

	def getGridCoords(self, ptPixel):
		return hex.pointToHexCoords(ptPixel, self.hexSize)

	def getGridUnitSize(self):
		return ((self.hexSize // 4) * 3, self.hexSize)
