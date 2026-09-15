from ... import hex

from .grid import Grid


class HexGrid(Grid):
	def __init__(self, gridSize):
		super(HexGrid, self).__init__(gridSize)

	def drawGrid(self, gc, w, h, clip=None):
		hex.drawHexGridToGc(gc, w, h, self.gridSize, clip)

	def getGridCoords(self, ptPixel):
		return hex.pointToHexCoords(ptPixel, self.gridSize)

	def getGridUnitSize(self):
		return ((self.gridSize // 4) * 3, self.gridSize)
