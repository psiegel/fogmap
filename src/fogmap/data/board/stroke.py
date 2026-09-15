"""One mark made on the whiteboard layer."""
import math


class Stroke(object):
	"""A single drag of the pen: its colour, its width, and the map points it
	   passed through.

	   Everything here is in map pixels, so the same stroke lands on the same
	   feature in both windows however either of them happens to be zoomed.
	   Nothing about a stroke is ever written to a map file - see Whiteboard."""

	def __init__(self, colour, width, pt):
		# (r, g, b).  The alpha a stroke is actually drawn with is worked out
		# from how much of its life is left, and is not stored.
		self.colour = colour
		self.width = max(float(width), 1.0)
		self.points = [pt]
		# When the pen came up.  None while the stroke is still being drawn,
		# which is what keeps a slow, careful line from fading out from under
		# the hand drawing it.
		self.finishedAt = None

	def add(self, pt):
		"""Extend the stroke.  Returns the box that changed, or None if the
		   point added nothing - the mouse can report the same position twice."""
		last = self.points[-1]
		if (pt == last):
			return None
		self.points.append(pt)
		return self.segmentBounds(last, pt)

	def finish(self, now):
		self.finishedAt = now

	def segmentBounds(self, a, b):
		"""The box one segment covers, pen width included."""
		pad = self.width / 2.0 + 1.0
		return (min(a[0], b[0]) - pad, min(a[1], b[1]) - pad,
				max(a[0], b[0]) + pad, max(a[1], b[1]) + pad)

	def bounds(self):
		"""The box the whole stroke covers, as (x0, y0, x1, y1).  Used to
		   invalidate what a fading or vanishing stroke leaves behind."""
		pad = self.width / 2.0 + 1.0
		xs = [pt[0] for pt in self.points]
		ys = [pt[1] for pt in self.points]
		return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

	def hits(self, pt, radius):
		"""Whether pt comes within radius of the stroke, the pen width counted
		   as part of it.  This is what the eraser tests against."""
		reach = radius + self.width / 2.0
		if (len(self.points) == 1):
			return Stroke.__distance(pt, self.points[0]) <= reach
		for index in range(len(self.points) - 1):
			if (Stroke.__distanceToSegment(pt, self.points[index],
										   self.points[index + 1]) <= reach):
				return True
		return False

	@staticmethod
	def __distance(a, b):
		return math.hypot(a[0] - b[0], a[1] - b[1])

	@staticmethod
	def __distanceToSegment(pt, a, b):
		dx = b[0] - a[0]
		dy = b[1] - a[1]
		lengthSq = (dx * dx) + (dy * dy)
		if (lengthSq <= 0):
			return Stroke.__distance(pt, a)
		# How far along the segment the nearest point is, clamped to its ends.
		t = (((pt[0] - a[0]) * dx) + ((pt[1] - a[1]) * dy)) / lengthSq
		t = min(max(t, 0.0), 1.0)
		return Stroke.__distance(pt, (a[0] + t * dx, a[1] + t * dy))
