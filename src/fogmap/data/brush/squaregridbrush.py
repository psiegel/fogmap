from PIL import ImageDraw

from .gridbrush import GridBrush


class SquareGridBrush(GridBrush):
	def __init__(self, gridSize, brushSize):
		self.gridSize = gridSize
		self.brushSize = brushSize

	def getSize(self):
		return self.brushSize
	
	def setSize(self, size):
		self.brushSize = size
		
	def setGridSize(self, size):
		self.gridSize = size
		
	def drawToGc(self, gc, x, y):
		size = self.brushSize * self.gridSize
		x -= x % size
		y -= y % size
		gc.DrawRectangle(x, y, size, size)

	def drawToImage(self, image, x, y, color):
		size = self.brushSize * self.gridSize
		x -= x % size
		y -= y % size
		draw = ImageDraw.Draw(image)
		draw.rectangle((x, y, x+size, y+size), fill=color)
		del draw

	def anchor(self, x, y):
		size = self.brushSize * self.gridSize
		return (x - x % size, y - y % size)

	def bounds(self, x, y):
		x, y = self.anchor(x, y)
		size = self.brushSize * self.gridSize
		return (x, y, x + size + 1, y + size + 1)
