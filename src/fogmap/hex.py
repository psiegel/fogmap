"""Hexagons: what shape one is, where the hexes of a grid sit, and the cell
   arithmetic that goes with them.

   A hex here is described by the box it fits in - a width and a height - and
   by the length of its two parallel edges: the top and bottom of a flat-topped
   hex, the left and right of a pointy-topped one.  A regular hexagon is the
   case where that edge is half the width (flat top) or half the height (pointy
   top), and every other case is a hex stretched or squashed to sit on a map
   that was drawn by somebody who was not counting pixels - which is most of
   them.  The angles give, not the size of the box: that is what makes a grid
   set by eye land on the map and stay there.

   A cell is counted as a column and a row, every other one of them pushed
   along half a cell, because that is what a map file and a brush hold.
   Neighbours and distances are worked out in cube coordinates, where they are
   simple arithmetic rather than a page of parity cases, and converted back.
   See https://www.redblobgames.com/grids/hexagons/ for both, under "offset
   coordinates" and "cube coordinates"."""
import math

import wx

from PIL import ImageDraw


# Which way up the hexes are: flat-topped ones have an edge across the top and
# a corner at each side, pointy-topped ones the other way about.
FLAT_TOP = "Flat Top"
POINTY_TOP = "Pointy Top"
ORIENTATIONS = (FLAT_TOP, POINTY_TOP)


def sideOfLine(pt, a, b):
	"""Which side of the line through a and b a point is on: negative one way,
	   positive the other, zero on the line itself."""
	return (((pt[0] - b[0]) * (a[1] - b[1])) -
			((a[0] - b[0]) * (pt[1] - b[1])))

def pointInTriangle(pt, triangle):
	"""Point is a tuple (x, y) and triangle is a list of three tuples defining
	   the three points of the triangle.  A point on an edge counts as in.

	   This asks which side of each edge the point falls on, rather than
	   whether the three triangles it makes with the corners add back up to the
	   whole one.  That test wants the sum to come out exact, which it does
	   while a hex is a whole number of pixels across and its corners land on
	   whole pixels - and does not once it is any size the GM cares to set: a
	   point plainly inside came out a ten-thousandth of a pixel over and was
	   handed to the wrong cell."""
	d1 = sideOfLine(pt, triangle[0], triangle[1])
	d2 = sideOfLine(pt, triangle[1], triangle[2])
	d3 = sideOfLine(pt, triangle[2], triangle[0])
	return not (((d1 < 0) or (d2 < 0) or (d3 < 0)) and
				((d1 > 0) or (d2 > 0) or (d3 > 0)))


class HexLayout(object):
	"""One hex grid's shape and where it starts: everything that has to be
	   agreed on between the grid drawn over the map and the brush that paints
	   whole cells of it."""

	def __init__(self, width, height, edge, orientation=FLAT_TOP,
				 offsetX=0, offsetY=0):
		self.width = float(width)
		self.height = float(height)
		self.orientation = orientation
		self.offsetX = offsetX
		self.offsetY = offsetY

		# The edge runs across the way the hex is pointed, and cannot be longer
		# than the hex is that way: at exactly that length the slanted corners
		# have gone altogether and the cells are rectangles, which is a silly
		# grid but a drawable one.  Anything past it would fold the shape
		# inside out, so it is stopped here rather than trusted to the caller.
		self.across = self.width if (orientation == FLAT_TOP) else self.height
		self.edge = max(1.0, min(float(edge), self.across))
		# How much of the box the slanted part of the hex takes up on each
		# side, which is also how far the cells of one column or row reach back
		# over the one before it.
		self.slant = (self.across - self.edge) / 2.0

		if (orientation == POINTY_TOP):
			# Columns are a whole hex apart and rows overlap by the slant;
			# every other row is pushed half a hex to the right.
			self.stepX = self.width
			self.stepY = self.height - self.slant
			self.staggerX = self.width / 2.0
			self.staggerY = 0.0
		else:
			self.stepX = self.width - self.slant
			self.stepY = self.height
			self.staggerX = 0.0
			self.staggerY = self.height / 2.0

	@staticmethod
	def forGrid(grid):
		"""The layout a map's hex grid settings ask for."""
		return HexLayout(grid.width, grid.height, grid.edge, grid.orientation,
						 grid.offsetX, grid.offsetY)

	# --- where the hexes are --------------------------------------------------

	def hexOrigin(self, col, row):
		"""The top left corner of the box a hex fits in, in map pixels."""
		return (self.offsetX + (col * self.stepX) +
				(self.staggerX if (row % 2) else 0.0),
				self.offsetY + (row * self.stepY) +
				(self.staggerY if (col % 2) else 0.0))

	def hexShape(self):
		"""The six corners of a hex, in order, measured from the top left of
		   the box it fits in.  The two orientations are the same shape turned
		   on its side, and are written out separately because that reads
		   better than transposing one into the other."""
		w, h, e, slant = self.width, self.height, self.edge, self.slant
		if (self.orientation == POINTY_TOP):
			return ((w / 2.0, 0.0), (w, slant), (w, slant + e),
					(w / 2.0, h), (0.0, slant + e), (0.0, slant))
		return ((0.0, h / 2.0), (slant, 0.0), (slant + e, 0.0),
				(w, h / 2.0), (slant + e, h), (slant, h))

	def hexCorners(self, col, row):
		"""The six corners of one hex of the grid, in map pixels."""
		x, y = self.hexOrigin(col, row)
		return [(x + cx, y + cy) for cx, cy in self.hexShape()]

	def hexBounds(self, col, row):
		"""The box one hex of the grid fits in, as (x0, y0, x1, y1)."""
		x, y = self.hexOrigin(col, row)
		return (x, y, x + self.width, y + self.height)

	def cellRange(self, x0, y0, x1, y1):
		"""The columns and rows whose hexes reach into a box of map, as the
		   half-open ranges the drawing loops want.

		   Deliberately a hex or so generous at each edge: drawing one that
		   turns out to be just outside costs a stroke, and missing one leaves
		   a hole in the grid."""
		colFrom = int(math.floor((x0 - self.offsetX - self.width -
								  self.staggerX) / self.stepX))
		colTo = int(math.ceil((x1 - self.offsetX) / self.stepX)) + 1
		rowFrom = int(math.floor((y0 - self.offsetY - self.height -
								  self.staggerY) / self.stepY))
		rowTo = int(math.ceil((y1 - self.offsetY) / self.stepY)) + 1
		return (colFrom, colTo, rowFrom, rowTo)

	def pointToHex(self, point):
		"""Which hex a map point falls in, as (column, row)."""
		x = point[0] - self.offsetX
		y = point[1] - self.offsetY
		if (self.orientation == POINTY_TOP):
			# A pointy-topped grid is a flat-topped one on its side, so the
			# whole business is done once and handed swapped coordinates.
			col, row = _flatPointToHex(y, x, self.height, self.width, self.edge)
			return (row, col)
		return _flatPointToHex(x, y, self.width, self.height, self.edge)

	# --- which hexes are near which ------------------------------------------

	def toCube(self, col, row):
		"""A column and row as cube coordinates, where the hexes fall into
		   three straight axes and stepping about between them is arithmetic.
		   Only two of the three are kept; the third is always minus their
		   sum."""
		if (self.orientation == POINTY_TOP):
			# Odd rows are pushed right, which redblobgames calls odd-r.
			return (col - ((row - (row & 1)) // 2), row)
		# Odd columns are pushed down: odd-q.
		return (col, row - ((col - (col & 1)) // 2))

	def fromCube(self, q, r):
		if (self.orientation == POINTY_TOP):
			return (q + ((r - (r & 1)) // 2), r)
		return (q, r + ((q - (q & 1)) // 2))

	def hexesWithin(self, col, row, radius):
		"""Every hex within radius-1 steps of one hex, itself included.

		   A radius of one is that hex alone, which is what a brush of size one
		   paints: the sizes count hexes across from the middle, not steps."""
		reach = max(0, int(radius) - 1)
		q, r = self.toCube(col, row)
		hexes = []
		for dq in range(-reach, reach + 1):
			for dr in range(max(-reach, -dq - reach),
							min(reach, -dq + reach) + 1):
				hexes.append(self.fromCube(q + dq, r + dr))
		return hexes

	def circleBounds(self, point, radius):
		"""The box every hex a brush of this size would paint fits in."""
		col, row = self.pointToHex(point)
		hexes = self.hexesWithin(col, row, radius)
		boxes = [self.hexBounds(c, r) for c, r in hexes]
		return (min(b[0] for b in boxes), min(b[1] for b in boxes),
				max(b[2] for b in boxes), max(b[3] for b in boxes))


def _flatPointToHex(x, y, w, h, e):
	"""Which hex of a flat-topped grid a point falls in, as (column, row), with
	   the grid's own origin already taken off the point.

	   The columns are stepped through as if they were plain rectangles, and
	   then the left corner of the hex - which reaches back over the column
	   before it - is dealt with by asking which side of the slanted edge the
	   point is on."""
	colStep = (w + e) / 2.0
	slant = (w - e) / 2.0
	col = int(math.floor(x / colStep))
	# Odd columns hang half a hex lower than even ones.
	localY = y - ((h / 2.0) if (col % 2) else 0.0)
	row = int(math.floor(localY / h))

	dx = x - (col * colStep)
	dy = localY - (row * h)
	if (dx < slant):
		if (dy < (h / 2.0)):
			# Over the top left corner: the hex up and to the left.
			if (pointInTriangle((dx, dy), ((0, 0), (0, h / 2.0), (slant, 0)))):
				col -= 1
				if (col % 2):
					row -= 1
		elif (pointInTriangle((dx, dy), ((0, h / 2.0), (0, h), (slant, h)))):
			# Over the bottom left corner: the hex down and to the left.
			col -= 1
			if (not (col % 2)):
				row += 1
	return (col, row)


# --- drawing ------------------------------------------------------------------

def createHexPath(gc, layout):
	"""One hex as a path, with its box's top left corner at the origin."""
	corners = layout.hexShape()
	path = gc.CreatePath()
	path.MoveToPoint(*corners[0])
	for corner in corners[1:]:
		path.AddLineToPoint(*corner)
	path.AddLineToPoint(*corners[0])
	return path

def drawHexGridToGc(gc, w, h, layout, clip=None):
	"""clip is the box of map being repainted, as (x0, y0, x1, y1), or None for
	   the whole map.  Only the hexes that reach into it are stroked; drawing
	   the lot is thousands of strokes on a large map, and it happens on every
	   repaint."""
	if ((layout.stepX <= 0) or (layout.stepY <= 0)):
		return

	x0, y0, x1, y1 = clip if (clip != None) else (0, 0, w, h)
	# A pixel of slack for the pen, and never anything outside the map itself.
	x0, y0 = max(0, x0 - 1), max(0, y0 - 1)
	x1, y1 = min(w, x1 + 1), min(h, y1 + 1)

	gc.SetPen(wx.Pen("black", 1))
	gc.SetBrush(wx.Brush("black"))
	hexPath = createHexPath(gc, layout)

	colFrom, colTo, rowFrom, rowTo = layout.cellRange(x0, y0, x1, y1)
	for col in range(colFrom, colTo):
		for row in range(rowFrom, rowTo):
			x, y = layout.hexOrigin(col, row)
			if (((x + layout.width) < 0) or (x > w) or
				((y + layout.height) < 0) or (y > h)):
				# Off the map: an edge of the staggered columns, or the slack
				# cellRange leaves around the box.
				continue
			gc.PushState()
			gc.Translate(x, y)
			gc.StrokePath(hexPath)
			gc.PopState()

def fillHexCircleToGc(gc, center, radius, layout):
	"""The hexes a brush of this size would paint, filled with whatever brush
	   the caller has set."""
	hexPath = createHexPath(gc, layout)
	col, row = layout.pointToHex(center)
	for eachCol, eachRow in layout.hexesWithin(col, row, radius):
		x, y = layout.hexOrigin(eachCol, eachRow)
		gc.PushState()
		gc.Translate(x, y)
		gc.DrawPath(hexPath)
		gc.PopState()

def fillHexToImage(im, layout, col, row, color):
	draw = ImageDraw.Draw(im)
	draw.polygon([(int(round(x)), int(round(y)))
				  for x, y in layout.hexCorners(col, row)], color)
	del draw

def fillHexCircleToImage(im, center, radius, layout, color):
	col, row = layout.pointToHex(center)
	for eachCol, eachRow in layout.hexesWithin(col, row, radius):
		fillHexToImage(im, layout, eachCol, eachRow, color)
