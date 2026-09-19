import math

import wx

from .grid import Grid


class SquareGrid(Grid):
	"""Cells of a fixed width and height, laid out from an origin that is not
	   necessarily the top left corner of the map: scanned maps rarely have
	   their first cell starting exactly there, and the cells are not always
	   square."""

	def __init__(self, cellWidth, cellHeight, offsetX=0, offsetY=0):
		super(SquareGrid, self).__init__()
		self.cellWidth = cellWidth
		self.cellHeight = cellHeight
		self.offsetX = offsetX
		self.offsetY = offsetY

	def createGridPath(self, gc):
		path = gc.CreatePath()
		path.MoveToPoint(0, self.cellHeight)
		path.AddLineToPoint(self.cellWidth, self.cellHeight)
		path.AddLineToPoint(self.cellWidth, 0)
		return path

	def drawGrid(self, gc, w, h, clip=None):
		cw, ch = self.cellWidth, self.cellHeight
		if ((cw <= 0) or (ch <= 0)):
			return
		ox, oy = self.offsetX, self.offsetY
		# Each cell is stroked as its own bottom-and-right corner, exactly as
		# it always was - batching the whole grid into one path instead would
		# change how the overlaps at the crossings come out.  All that is new
		# is which cells are worth stroking.
		#
		# Cell (i, j) starts at (ox + i*cw, oy + j*ch), and an offset means the
		# first of them can start left of and above the map: the partial cell
		# in the corner still has edges to draw.
		iFrom, iTo = self.__cellRange(0, w, ox, cw)
		jFrom, jTo = self.__cellRange(0, h, oy, ch)
		if (clip != None):
			x0, y0, x1, y1 = clip
			# A pixel of slack in each direction for the pen.
			iClipFrom, iClipTo = self.__cellRange(x0 - 1, x1 + 1, ox, cw)
			jClipFrom, jClipTo = self.__cellRange(y0 - 1, y1 + 1, oy, ch)
			iFrom, iTo = max(iFrom, iClipFrom), min(iTo, iClipTo)
			jFrom, jTo = max(jFrom, jClipFrom), min(jTo, jClipTo)

		path = self.createGridPath(gc)
		gc.SetPen(wx.Pen("black", 1))
		for i in range(iFrom, iTo):
			for j in range(jFrom, jTo):
				gc.PushState()
				gc.Translate(ox + (i * cw), oy + (j * ch))
				gc.StrokePath(path)
				gc.PopState()

	@staticmethod
	def __cellRange(fromPixel, toPixel, offset, cellSize):
		"""Which cell indices along one axis reach into [fromPixel, toPixel],
		   as the half-open range the loops want."""
		first = int(math.floor((fromPixel - offset) / float(cellSize)))
		end = int(math.ceil((toPixel - offset) / float(cellSize)))
		return (first, end)

	def getGridCoords(self, ptPixel):
		# Floor division, so a point in the partial cell left of or above the
		# origin lands in cell -1 rather than sharing cell 0 with its
		# neighbour.
		return ((ptPixel[0] - self.offsetX) // self.cellWidth,
				(ptPixel[1] - self.offsetY) // self.cellHeight)

	def getGridUnitSize(self):
		return (self.cellWidth, self.cellHeight)
