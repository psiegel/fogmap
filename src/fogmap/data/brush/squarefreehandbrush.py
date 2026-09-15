from PIL import ImageDraw

from .brush import Brush, makeBoxCenteredOnPoint


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

	def anchor(self, x, y):
		return (x, y)

	def bounds(self, x, y):
		box = makeBoxCenteredOnPoint(x, y, self.w, self.h)
		return (box[0], box[1], box[2] + 1, box[3] + 1)
