from PIL import ImageDraw

from .brush import Brush, makeBoxCenteredOnPoint


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

	def anchor(self, x, y):
		return (x, y)

	def bounds(self, x, y):
		# ImageDraw treats the box as inclusive on both edges, so the far edge
		# lands one past what makeBoxCenteredOnPoint returns.
		box = makeBoxCenteredOnPoint(x, y, self.size, self.size)
		return (box[0], box[1], box[2] + 1, box[3] + 1)
