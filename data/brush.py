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
	def anchor(self, x, y):
		"""What this brush's mark at (x, y) actually depends on.

		   Two positions with the same anchor paint identical fog and draw an
		   identical cursor, so there is no work to do between them.  A
		   freehand brush lands wherever the mouse is, so its anchor is the
		   point itself and every pixel of movement counts; a brush that snaps
		   to the grid has the same anchor right across a cell."""
		raise Exception("Call to anchor on base Brush class.")

	def bounds(self, x, y):
		"""The box this brush covers at (x, y), as (x0, y0, x1, y1) with the
		   far edge exclusive.

		   Everything downstream of a dab is done to this box and no more: the
		   alpha it changed, the patch blitted into the cached bitmap, and the
		   region invalidated for repaint.  It is also what the on-screen brush
		   cursor is redrawn within.  May be generous - painting a few pixels
		   more than were touched is only slightly wasted work - but it must
		   never be short, or stale fog is left on screen."""
		raise Exception("Call to bounds on base Brush class.")

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

	def anchor(self, x, y):
		# Everything this brush draws is worked out from the hex the point
		# falls in, both on screen and into the mask.
		return hex.pointToHexCoords((x, y), self.hexSize)

	def bounds(self, x, y):
		# Which hexes a circle of this radius picks up depends on where the
		# centre falls within its own hex, so this is deliberately loose: one
		# hex of slack in every direction beyond the nominal reach.
		reach = (self.brushSize + 2) * self.hexSize
		return (x - reach, y - reach, x + reach, y + reach)
		
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

