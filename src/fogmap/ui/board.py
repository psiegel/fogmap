"""Drawing the whiteboard layer, and the GM's pointer, onto a map panel.

Both windows show the same strokes.  They are held in map pixels, so each
panel pushes its own transform - the GM's zoom, or the player view's zoom and
pan - and then asks for them at face value, exactly as the grid is drawn.

The pointer is the other half of the same idea and the opposite way round: it
is drawn in panel coordinates, at a fixed size on screen, because an arrow
that grew and shrank with the zoom would be a poor thing to point with.  Only
the player window draws one; the GM has a real cursor already.
"""
import wx


# The arrow, as offsets from its tip in screen pixels.  Shaped like an
# ordinary mouse pointer, because that is what it stands in for, and drawn
# half as big again as a real one: the players are looking at it from across a
# table, often on a projector, rather than from eighteen inches away.
POINTER = ((0.0, 0.0), (0.0, 29.5), (8.0, 22.5), (13.5, 33.0),
		   (18.0, 30.5), (12.5, 20.5), (21.5, 20.5))
POINTER_OUTLINE = wx.Colour(0, 0, 0, 220)
# The arrow takes the pen's colour, which can be anything, over a map that can
# be anything.  A heavy white edge is what makes a dark pen visible on dark
# ground, and the dark outline inside it what keeps a pale one visible on pale.
POINTER_HALO = wx.Colour(255, 255, 255, 235)
POINTER_HALO_WIDTH = 6


def draw(gc, whiteboard, now=None):
	"""Every stroke still on the board, in map pixels.  The caller has already
	   pushed whatever transform puts map pixels where they belong."""
	for stroke, alpha in whiteboard.visible(now):
		colour = wx.Colour(stroke.colour[0], stroke.colour[1], stroke.colour[2],
						   alpha)
		if (len(stroke.points) < 2):
			# A tap rather than a drag: a round pen leaves a dot.
			half = stroke.width / 2.0
			pt = stroke.points[0]
			gc.SetPen(wx.TRANSPARENT_PEN)
			gc.SetBrush(wx.Brush(colour))
			gc.DrawEllipse(pt[0] - half, pt[1] - half, stroke.width, stroke.width)
			continue
		# Round caps and joins, so a stroke reads as one line rather than as
		# the run of separate segments it actually is.  The pen goes through
		# GraphicsPenInfo for a width that can be fractional: the width is in
		# map pixels, and the transform can be anything.
		gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(colour)
							   .Width(stroke.width)
							   .Cap(wx.CAP_ROUND)
							   .Join(wx.JOIN_ROUND)))
		path = gc.CreatePath()
		path.MoveToPoint(stroke.points[0][0], stroke.points[0][1])
		for pt in stroke.points[1:]:
			path.AddLineToPoint(pt[0], pt[1])
		gc.StrokePath(path)


def drawPointer(gc, pt, colour):
	"""The GM's cursor, in the panel's own coordinates, filled with whatever
	   colour they are drawing in.  Outlined dark over a pale shadow so that it
	   shows up on a map of any colour, the way the viewport overlay does."""
	path = gc.CreatePath()
	path.MoveToPoint(pt[0] + POINTER[0][0], pt[1] + POINTER[0][1])
	for offset in POINTER[1:]:
		path.AddLineToPoint(pt[0] + offset[0], pt[1] + offset[1])
	path.CloseSubpath()

	gc.SetBrush(wx.TRANSPARENT_BRUSH)
	gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(POINTER_HALO)
						   .Width(POINTER_HALO_WIDTH)
						   .Join(wx.JOIN_ROUND)))
	gc.StrokePath(path)
	gc.SetBrush(wx.Brush(colour))
	gc.SetPen(wx.Pen(POINTER_OUTLINE, 1))
	gc.DrawPath(path)


def pointerRect(pt):
	"""Where a pointer at pt lands, as a rectangle to invalidate.  Generous by
	   the width of the halo drawn around it, and a little over."""
	xs = [offset[0] for offset in POINTER]
	ys = [offset[1] for offset in POINTER]
	pad = POINTER_HALO_WIDTH + 2
	left = int(pt[0] + min(xs)) - pad
	top = int(pt[1] + min(ys)) - pad
	right = int(pt[0] + max(xs)) + pad + 1
	bottom = int(pt[1] + max(ys)) + pad + 1
	return wx.Rect(left, top, right - left, bottom - top)
