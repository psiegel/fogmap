import wx
import hex

class Grid(object):
	def __init__(self, gridSize):
		self.gridSize = gridSize

	def drawGrid(self, gc, w, h):
		raise Exception("Call to drawGrid on base Grid class.")

	def getGridCoords(self, ptPixel):
		raise Exception("Call to fillCircle on base Grid class.")

	def getGridUnitSize(self):
		raise Exception("Call to fillCircle on base Grid class.")

class SquareGrid(Grid):
	def __init__(self, gridSize):
		super(SquareGrid, self).__init__(gridSize)

	def createGridPath(self, gc):
		path = gc.CreatePath()
		path.MoveToPoint(0, self.gridSize)
		path.AddLineToPoint(self.gridSize, self.gridSize)
		path.AddLineToPoint(self.gridSize, 0)
		return path

	def drawGrid(self, gc, w, h):
		x = 0
		y = 0
		path = self.createGridPath(gc)
		gc.SetPen(wx.Pen("black", 1))

		gc.PushState() 
		while x < w:
			gc.PushState()
			while y < h:
				gc.StrokePath(path)
				gc.Translate(0, self.gridSize)
				y += self.gridSize
			gc.PopState()
			gc.Translate(self.gridSize, 0)
			x += self.gridSize
			y = 0
		gc.PopState()     

	def getGridCoords(self, ptPixel):
		return (ptPixel[0] / self.gridSize, ptPixel[1] / self.gridSize)

	def getGridUnitSize(self):
		return (self.gridSize, self.gridSize)

class HexGrid(Grid):
	def __init__(self, gridSize):
		super(HexGrid, self).__init__(gridSize)

	def drawGrid(self, gc, w, h):
		hex.drawHexGridToGc(gc, w, h, self.gridSize)

	def getGridCoords(self, ptPixel):
		return hex.pointToHexCoords(ptPixel, self.gridSize)

	def getGridUnitSize(self):
		return ((self.gridSize/4)*3, self.gridSize)
