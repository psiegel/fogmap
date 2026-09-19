from PIL import ImageDraw

from .gridbrush import GridBrush


class SquareGridBrush(GridBrush):
	"""Paints whole cells of a square grid at a time, in blocks brushSize cells
	   across, aligned to the grid's own origin rather than to the map's corner."""

	def __init__(self, grid, brushSize):
		self.brushSize = brushSize
		self.setGrid(grid)

	def getSize(self):
		return self.brushSize

	def setSize(self, size):
		self.brushSize = size

	def setGrid(self, grid):
		self.cellWidth = grid.cellWidth
		self.cellHeight = grid.cellHeight
		self.offsetX = grid.offsetX
		self.offsetY = grid.offsetY

	def dabSize(self):
		"""How big one dab is, in map pixels."""
		return (self.brushSize * self.cellWidth, self.brushSize * self.cellHeight)

	def drawToGc(self, gc, x, y):
		x, y = self.anchor(x, y)
		w, h = self.dabSize()
		gc.DrawRectangle(x, y, w, h)

	def drawToImage(self, image, x, y, color):
		x, y = self.anchor(x, y)
		w, h = self.dabSize()
		draw = ImageDraw.Draw(image)
		draw.rectangle((x, y, x + w, y + h), fill=color)
		del draw

	def anchor(self, x, y):
		w, h = self.dabSize()
		# Floor division rather than a remainder: an offset grid, or a point
		# left of or above the origin, gives a negative index, and the block
		# has to start at the corner of that block either way.
		return (self.offsetX + (((x - self.offsetX) // w) * w),
				self.offsetY + (((y - self.offsetY) // h) * h))

	def bounds(self, x, y):
		x, y = self.anchor(x, y)
		w, h = self.dabSize()
		return (x, y, x + w + 1, y + h + 1)
