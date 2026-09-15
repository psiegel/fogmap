"""The ephemeral layer the GM draws on top of the map."""
import time

from .stroke import Stroke


class Whiteboard(object):
	"""What the GM has drawn over the map, in map pixels, for as long as it
	   lasts.

	   This is deliberately not part of a Map and never reaches a map file:
	   it is a way of pointing at things during a session, not something the
	   map is supposed to come back with.  It is thrown away when the GM opens
	   another map, and with the application when it closes.

	   A stroke fades out over its last FADE seconds and is then dropped.  How
	   long it gets is `lifetime`, or None for strokes that stay until they are
	   erased.  The clock starts when the pen comes up rather than when it goes
	   down, so a long careful line does not begin fading while it is still
	   being drawn."""

	# How long a stroke spends on its way out.  Long enough to read as fading
	# rather than as a stroke that simply vanished.
	FADE = 1.5

	def __init__(self, lifetime=None):
		self.strokes = []
		self.lifetime = lifetime
		# The one being drawn right now, if any.  Kept out of the fade
		# arithmetic by having no finish time yet.
		self.current = None
		self.updateListeners = []
		self.tickListener = None

	# --- what is on it --------------------------------------------------------

	def isEmpty(self):
		return not self.strokes

	def expiryOf(self, stroke):
		"""When this stroke runs out, or None if it is here to stay."""
		if ((self.lifetime is None) or (stroke.finishedAt is None)):
			return None
		return stroke.finishedAt + self.lifetime

	def alphaOf(self, stroke, now):
		"""0-255, ramped down over the stroke's last FADE seconds."""
		expiry = self.expiryOf(stroke)
		if (expiry is None):
			return 255
		remaining = expiry - now
		if (remaining >= Whiteboard.FADE):
			return 255
		if (remaining <= 0):
			return 0
		return int(255 * remaining / Whiteboard.FADE)

	def visible(self, now=None):
		"""Every stroke still worth drawing, each with the alpha to draw it at."""
		now = Whiteboard.now() if (now is None) else now
		shown = []
		for stroke in self.strokes:
			alpha = self.alphaOf(stroke, now)
			if (alpha > 0):
				shown.append((stroke, alpha))
		return shown

	# --- drawing on it --------------------------------------------------------

	def begin(self, colour, width, pt):
		self.current = Stroke(colour, width, pt)
		self.strokes.append(self.current)
		self.__fire(self.current.bounds())

	def extend(self, pt):
		if (self.current is None):
			return
		rect = self.current.add(pt)
		if (rect is not None):
			self.__fire(rect)

	def end(self):
		if (self.current is None):
			return
		self.current.finish(Whiteboard.now())
		self.current = None
		# Only now does anything have a deadline, so only now is there
		# anything for the clock to do.
		self.__wake()

	def erase(self, pt, radius):
		"""Rub out every stroke within radius of pt."""
		hit = [stroke for stroke in self.strokes if stroke.hits(pt, radius)]
		for stroke in hit:
			self.__remove(stroke)
		return bool(hit)

	def clear(self):
		if (not self.strokes):
			return
		self.strokes = []
		self.current = None
		self.__fire(None)

	def setLifetime(self, lifetime):
		"""Change how long a stroke lasts, or None to let them all stay.

		   This applies to what is already on the board as well as to what is
		   drawn next: the setting is about the board, not about the moment a
		   particular stroke happened to be made."""
		if (lifetime == self.lifetime):
			return
		self.lifetime = lifetime
		if (lifetime is None):
			# Strokes part-way through fading have to come back to full.
			self.__fire(None)
		else:
			self.__wake()

	# --- the clock ------------------------------------------------------------

	def tick(self):
		"""Let time pass: repaint whatever is fading, drop whatever has run
		   out.  Returns True while there is still something on a deadline, so
		   that whoever is driving the clock knows to keep going."""
		now = Whiteboard.now()
		pending = False
		for stroke in list(self.strokes):
			expiry = self.expiryOf(stroke)
			if (expiry is None):
				continue
			if (now >= expiry):
				self.__remove(stroke)
			else:
				pending = True
				if (now >= (expiry - Whiteboard.FADE)):
					# Part-way out, and a shade lighter than it was drawn last
					# time.  Only the fading ones are repainted; a stroke with
					# minutes left on it is already right on screen.
					self.__fire(stroke.bounds())
		return pending

	@staticmethod
	def now():
		# Monotonic: strokes should not outlive their welcome, or vanish early,
		# because the wall clock was put back.
		return time.monotonic()

	# --- listeners ------------------------------------------------------------

	def setTickListener(self, listener):
		"""Called when something gains a deadline, so that whoever owns the
		   timer can start it running again."""
		self.tickListener = listener

	def addUpdateListener(self, listener):
		self.updateListeners.append(listener)

	def removeUpdateListener(self, listener):
		self.updateListeners.remove(listener)

	def __remove(self, stroke):
		self.strokes.remove(stroke)
		if (stroke is self.current):
			self.current = None
		self.__fire(stroke.bounds())

	def __fire(self, rect):
		"""rect is the box of map that changed, as (x0, y0, x1, y1), or None
		   when everything has to be repainted."""
		for listener in self.updateListeners:
			listener(rect)

	def __wake(self):
		if (self.tickListener is not None):
			self.tickListener()
