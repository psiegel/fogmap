"""What every brush has to be able to do, and the box arithmetic they share."""


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
