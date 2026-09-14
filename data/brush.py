from PIL import ImageDraw

import hex

def makeBoxCenteredOnPoint(ptx, pty, boxw, boxh):
	x = ptx - boxw // 2
	y = pty - boxh // 2
	return (x, y, x+boxw, y+boxh)

class Brush(object):
	def getSize(self):
		raise Exception("Call to getSize on base Brush class.")    
	def setSize(self, size):
		raise Exception("Call to setSize on base Brush class.")    
	def drawToGc(self, x, y):
		raise Exception("Call to drawToGc on base Brush class.")    
	def drawToImage(self, x, y):
		raise Exception("Call to drawToImage on base Brush class.")

class RoundFreehandBrush(Brush):    
	def __init__(self, size):
		self.size = size
		
	def getSize(self):
		return self.size

	def setSize(self, size):
		self.size = size   

	def drawToGc(self, gc, x, y):
		half = self.size // 2
		gc.DrawEllipse(x-half, y-half, self.size, self.size)

	def drawToImage(self, image, x, y, color):
		draw = ImageDraw.Draw(image)	
		draw.ellipse(makeBoxCenteredOnPoint(x, y, self.size, self.size), fill=color)
		del draw
		
class SquareFreehandBrush(Brush):    
	def __init__(self, w, h):
		self.w = w
		self.h = h
		
	def getSize(self):
		return self.w		
		
	def setSize(self, size):
		self.w = size
		self.h = size

	def drawToGc(self, gc, x, y):
		gc.DrawRectangle(x - self.w // 2, y - self.h // 2, self.w, self.h)

	def drawToImage(self, image, x, y, color):
		draw = ImageDraw.Draw(image)
		draw.rectangle(makeBoxCenteredOnPoint(x, y, self.w, self.h), fill=color)
		del draw

class GridBrush(Brush):
	def setGridSize(self, size):
		raise Exception("Call to setGridSize on base GridBrush class.")		
		
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

