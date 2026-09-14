"""The player-viewport overlay drawn on the GM map.

The rectangle is never stored: it is derived from the player panel's scale and
offset every time it is drawn, so it cannot drift out of sync with what the
players are actually looking at.  Dragging a handle runs the derivation
backwards and pushes a new scale and offset onto the player panel.

Coordinates here are map pixels.  The GM panel draws the map 1:1 at its origin,
so its client coordinates are map pixels too and no conversion is needed.
"""
import wx

# Handles are named by the edges they move, so "nw" is the top-left corner.
CORNERS = ("nw", "ne", "sw", "se")
EDGES = ("n", "s", "w", "e")
HANDLES = CORNERS + EDGES

CURSORS = {
	"nw": wx.CURSOR_SIZENWSE, "se": wx.CURSOR_SIZENWSE,
	"ne": wx.CURSOR_SIZENESW, "sw": wx.CURSOR_SIZENESW,
	"n":  wx.CURSOR_SIZENS,   "s":  wx.CURSOR_SIZENS,
	"w":  wx.CURSOR_SIZEWE,   "e":  wx.CURSOR_SIZEWE,
}

# A viewport narrower than this is meaningless, and would divide by zero.
MIN_WIDTH = 1e-6

OUTLINE = wx.Colour(0, 220, 255)
SHADOW = wx.Colour(0, 0, 0, 170)


def handlePoints(rect):
	"""Map each handle name to the point it is drawn at."""
	x, y, w, h = rect
	midX = x + w / 2.0
	midY = y + h / 2.0
	return {
		"nw": (x, y),         "n": (midX, y),     "ne": (x + w, y),
		"w":  (x, midY),                          "e":  (x + w, midY),
		"sw": (x, y + h),     "s": (midX, y + h), "se": (x + w, y + h),
	}


def hitTest(rect, pt, tolerance):
	"""Which handle, if any, is under pt.  Corners win over edges."""
	x, y, w, h = rect
	if not ((x - tolerance) <= pt[0] <= (x + w + tolerance)):
		return None
	if not ((y - tolerance) <= pt[1] <= (y + h + tolerance)):
		return None

	handle = ""
	if (abs(pt[1] - y) <= tolerance):
		handle += "n"
	elif (abs(pt[1] - (y + h)) <= tolerance):
		handle += "s"
	if (abs(pt[0] - x) <= tolerance):
		handle += "w"
	elif (abs(pt[0] - (x + w)) <= tolerance):
		handle += "e"
	return handle or None


def resize(rect, handle, pt, aspect, minWidth=None, maxWidth=None):
	"""Move `handle` to `pt`, holding the opposite edge still and forcing the
	   result to `aspect` (width / height).  Returns a new (x, y, w, h)."""
	x, y, w, h = rect
	left, top, right, bottom = x, y, x + w, y + h

	if ("w" in handle): left = pt[0]
	if ("e" in handle): right = pt[0]
	if ("n" in handle): top = pt[1]
	if ("s" in handle): bottom = pt[1]

	horizontal = ("w" in handle) or ("e" in handle)
	vertical = ("n" in handle) or ("s" in handle)
	dragW = abs(right - left)
	dragH = abs(bottom - top)

	if (horizontal and vertical):
		# A corner follows the cursor on whichever axis it was dragged further.
		newW = max(dragW, dragH * aspect)
	elif horizontal:
		newW = dragW
	else:
		newW = dragH * aspect

	if (minWidth is not None):
		newW = max(newW, minWidth)
	if (maxWidth is not None):
		newW = min(newW, maxWidth)
	# Dragging an edge onto its opposite would otherwise collapse the rect.
	newW = max(newW, MIN_WIDTH)
	newH = newW / aspect

	# Whichever side was not dragged stays put; an undragged axis stays centred.
	if ("w" in handle):
		newLeft = right - newW
	elif ("e" in handle):
		newLeft = left
	else:
		newLeft = x + (w - newW) / 2.0

	if ("n" in handle):
		newTop = bottom - newH
	elif ("s" in handle):
		newTop = top
	else:
		newTop = y + (h - newH) / 2.0

	return (newLeft, newTop, newW, newH)


def draw(gc, rect, handleSize):
	"""Outline the rect with handles, dark-on-light so it reads over any map."""
	x, y, w, h = rect

	gc.SetBrush(wx.TRANSPARENT_BRUSH)
	gc.SetPen(wx.Pen(SHADOW, 3))
	gc.DrawRectangle(x, y, w, h)
	gc.SetPen(wx.Pen(OUTLINE, 1))
	gc.DrawRectangle(x, y, w, h)

	gc.SetBrush(wx.Brush(OUTLINE))
	gc.SetPen(wx.Pen(SHADOW, 1))
	half = handleSize / 2.0
	for pt in handlePoints(rect).values():
		gc.DrawRectangle(pt[0] - half, pt[1] - half, handleSize, handleSize)
