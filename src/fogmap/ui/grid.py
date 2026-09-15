import math

import wx
from .. import hex


class Grid(object):
	def __init__(self, gridSize):
		self.gridSize = gridSize

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

class SquareGrid(Grid):
	def __init__(self, gridSize):
		super(SquareGrid, self).__init__(gridSize)

	def createGridPath(self, gc):
		path = gc.CreatePath()
		path.MoveToPoint(0, self.gridSize)
		path.AddLineToPoint(self.gridSize, self.gridSize)
		path.AddLineToPoint(self.gridSize, 0)
		return path

	def drawGrid(self, gc, w, h, clip=None):
		size = self.gridSize
		if (size <= 0):
			return
		# Each cell is stroked as its own bottom-and-right corner, exactly as
		# it always was - batching the whole grid into one path instead would
		# change how the overlaps at the crossings come out.  All that is new
		# is which cells are worth stroking.
		cols = int(math.ceil(w / float(size)))
		rows = int(math.ceil(h / float(size)))
		if (clip is None):
			iFrom, iTo, jFrom, jTo = 0, cols, 0, rows
		else:
			x0, y0, x1, y1 = clip
			# A cell reaches a whole cell down and right of its origin, plus a
			# pixel of slack for the pen.
			iFrom = max(0, int(math.floor((x0 - size - 1) / float(size))))
			iTo = min(cols, int(math.floor((x1 + 1) / float(size))) + 1)
			jFrom = max(0, int(math.floor((y0 - size - 1) / float(size))))
			jTo = min(rows, int(math.floor((y1 + 1) / float(size))) + 1)

		path = self.createGridPath(gc)
		gc.SetPen(wx.Pen("black", 1))
		for i in range(iFrom, iTo):
			for j in range(jFrom, jTo):
				gc.PushState()
				gc.Translate(i * size, j * size)
				gc.StrokePath(path)
				gc.PopState()

	def getGridCoords(self, ptPixel):
		return (ptPixel[0] // self.gridSize, ptPixel[1] // self.gridSize)

	def getGridUnitSize(self):
		return (self.gridSize, self.gridSize)

class HexGrid(Grid):
	def __init__(self, gridSize):
		super(HexGrid, self).__init__(gridSize)

	def drawGrid(self, gc, w, h, clip=None):
		hex.drawHexGridToGc(gc, w, h, self.gridSize, clip)

	def getGridCoords(self, ptPixel):
		return hex.pointToHexCoords(ptPixel, self.gridSize)

	def getGridUnitSize(self):
		return ((self.gridSize // 4) * 3, self.gridSize)
