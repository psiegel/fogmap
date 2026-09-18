"""The player-viewport overlay drawn on the GM map.

It comes two ways.  Viewport mode draws the whole of it - the rectangle and the
handles that move and resize it - and every other mode draws a faint outline and
nothing else, whenever the GM has asked to see where the players are looking.

The rectangle is never stored: it is derived from the player panel's scale and
offset every time it is drawn, so it cannot drift out of sync with what the
players are actually looking at.  Dragging a handle runs the derivation
backwards and pushes a new scale and offset onto the player panel.

Coordinates here are map pixels.  The GM panel undoes its own zoom before it
asks anything of this module, and scales the rectangle back up itself when it
comes to draw it, so that the outline and its handles stay the same size on
screen however far the map is zoomed out.
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

# The same rectangle as shown by the modes that do not own it: dimmed, because
# it is there to say where the players are looking rather than to be worked on,
# and the map under it is what those modes are for.
FAINT_OUTLINE = wx.Colour(0, 220, 255)
FAINT_SHADOW = wx.Colour(0, 0, 0, 80)


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


def outline(gc, rect, colour, shadow):
	"""The rectangle itself, dark-on-light so it reads over any map."""
	x, y, w, h = rect
	gc.SetBrush(wx.TRANSPARENT_BRUSH)
	gc.SetPen(wx.Pen(shadow, 3))
	gc.DrawRectangle(x, y, w, h)
	gc.SetPen(wx.Pen(colour, 1))
	gc.DrawRectangle(x, y, w, h)


def draw(gc, rect, handleSize):
	"""The overlay as Viewport mode shows it: the rectangle plus the handles
	   that move and resize it."""
	outline(gc, rect, OUTLINE, SHADOW)

	gc.SetBrush(wx.Brush(OUTLINE))
	gc.SetPen(wx.Pen(SHADOW, 1))
	half = handleSize / 2.0
	for pt in handlePoints(rect).values():
		gc.DrawRectangle(pt[0] - half, pt[1] - half, handleSize, handleSize)


def drawFaint(gc, rect):
	"""The outline as every other mode shows it: no handles, because there is
	   nothing to take hold of here - the mouse belongs to whatever the GM is
	   actually doing, and this only says where the players are looking."""
	outline(gc, rect, FAINT_OUTLINE, FAINT_SHADOW)
