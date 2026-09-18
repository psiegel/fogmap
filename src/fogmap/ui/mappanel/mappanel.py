import wx
import numpy as np

from ... import data
from ... import gfx

from .. import board
from .. import grid


class MapPanel(wx.Panel):	
	def __init__(self, parent):
		super(MapPanel, self).__init__(parent, -1)
		self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
		self.SetDoubleBuffered(True)

		self.map = None
		self.grid = None
		self.mapImg = None
		# The map image converted for drawing.  Held across paints because the
		# conversion costs time proportional to the whole map - a sixth of a
		# second on a big one - and it used to be paid on every single repaint,
		# including the ones that only move the brush cursor.  A brush dab
		# patches the box it touched rather than throwing this away.
		self.mapBmp = None
		# Which pixelVersion of the map the colours in mapImg were composited
		# from.  None until anything has been, and compared rather than
		# trusted: a grid change asks for a wholesale rebuild too, and must
		# not pay for a composite of the whole map on every tick of a slider.
		self.rgbVersion = None
		self.playerPanel = None
		self.viewListener = None
		# The GM's drawings over the map.  Shared between the two windows and
		# owned by neither; ephemeral, and no part of the map or its file.
		self.whiteboard = None
		self._buffer = wx.Bitmap.FromRGBA(1, 1)
		
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_PAINT, self.onPaint)

	def setMap(self, map):
		if (self.map != None):
			self.map.removeUpdateListener(self._updateMap)
		self.map = map
		self.map.addUpdateListener(self._updateMap)
		self.mapBmp = None
		self._updateMap()
		
	def setWhiteboard(self, whiteboard):
		"""The drawing layer both windows show.  One board serves both, so a
		   stroke the GM makes is already on the players' screen."""
		if (self.whiteboard != None):
			self.whiteboard.removeUpdateListener(self._boardChanged)
		self.whiteboard = whiteboard
		if (whiteboard != None):
			whiteboard.addUpdateListener(self._boardChanged)
		self.Refresh(False)

	def _boardChanged(self, rect=None):
		"""rect is the box of map a stroke touched, or None when the whole
		   layer changed.  Repainting no more than that is what keeps a fading
		   stroke from costing the whole map on every frame of the fade."""
		if ((rect is None) or (self.mapImg is None)):
			self.Refresh(False)
			return
		self.RefreshRect(self._mapRectToClient(rect))

	def setPlayerPanel(self, panel):
		self.playerPanel = panel
		# Bound to this panel's own handlers rather than straight to the player
		# view's, so that a panel with something of its own to do with a key can
		# do it on the way past.
		self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.onKeyUp)

	def onKeyDown(self, evt):
		"""Keys pressed over this window drive the player view, so that the GM
		   can zoom and pan what the players see without leaving their own."""
		self.playerPanel.onKeyDown(evt)

	def onKeyUp(self, evt):
		self.playerPanel.onKeyUp(evt)

	def setViewListener(self, listener):
		"""Called whenever this panel's scale, offset or size changes."""
		self.viewListener = listener

	def _fireViewChanged(self):
		if (self.viewListener != None):
			self.viewListener()

	def reset(self):
		self.mapImg = None
		self.mapBmp = None
		self.rgbVersion = None

	def onSize(self, evt):
		w, h = self.GetClientSize()
		self._buffer = wx.Bitmap.FromRGBA(max(w, 1), max(h, 1))
		self._fireViewChanged()
		self.Refresh()
		
	def onPaint(self, evt):
		dc = wx.BufferedPaintDC(self, self._buffer)
		try:
			gc = wx.GraphicsContext.Create(dc)
		except NotImplementedError:
			dc.DrawText("This build of wxPython does not support the wx.GraphicsContext "
						"family of classes.",
						25, 25)
			return	

		# Draw no more of the map than was invalidated.  The buffer is kept
		# between paints, so whatever falls outside the clip is still there
		# from last time - which is what makes a brush dab cost the size of the
		# brush instead of the size of the map.
		box = self.GetUpdateRegion().GetBox()
		if (box.IsEmpty()):
			return

		gc.PushState()
		gc.Clip(box.x, box.y, box.width, box.height)
		self._draw(gc, (box.x, box.y, box.x + box.width, box.y + box.height))
		gc.PopState()
		
	def _draw(self, gc, box):
		"""box is the part of the panel being repainted, in its own
		   coordinates.  Passed down so the grid can skip what is off-screen
		   rather than relying on the clip to throw it away afterwards."""
		self._drawMap(gc)
		if ((self.map != None) and (self.map.grid.visible)):
			self._drawGrid(gc, box)
		self._drawBoard(gc)

	def onClose(self, evt):
		if (self.map != None):
			self.map.removeUpdateListener(self._updateMap)
		if (self.whiteboard != None):
			self.whiteboard.removeUpdateListener(self._boardChanged)
			self.whiteboard = None
		return True

	def _drawBoard(self, gc):
		"""The GM's drawings, over the map and its grid.  Held in map pixels,
		   so this pushes whatever transform the panel draws the map through
		   and hands them over unchanged - the same stroke then lands on the
		   same feature in both windows, at whatever zoom each of them is."""
		if ((self.whiteboard is None) or self.whiteboard.isEmpty() or
			(self.mapImg is None)):
			return
		gc.PushState()
		self._applyMapTransform(gc)
		board.draw(gc, self.whiteboard)
		gc.PopState()

	def _drawMap(self, gc):
		raise Exception("_drawMap called on base MapPanel class.")

	def _drawGrid(self, gc, box):
		raise Exception("_drawGrid called on base MapPanel class.")

	def _applyMapTransform(self, gc):
		"""Put the context into map pixels: the GM's zoom, or the player
		   view's zoom and pan."""
		raise Exception("_applyMapTransform called on base MapPanel class.")

	def _alpha(self, mask, box=None):
		"""How this panel turns the fog mask into alpha.  The two windows show
		   the same mask differently, and that is one of the two differences
		   between them here."""
		raise Exception("_alpha called on base MapPanel class.")

	def _rgb(self, box=None):
		"""What colour this panel draws the map, as an (h, w, 3) array of
		   bytes.  The other difference: with secrets on the map the GM sees
		   unrevealed ones ghosted through and revealed ones washed with a
		   tint, and the players see neither.

		   With no secret layer this is the map's own pixels and costs
		   nothing, which is the case every map without them is in."""
		raise Exception("_rgb called on base MapPanel class.")

	def _mapRectToClient(self, box):
		"""A box in map pixels as a rectangle in this panel's own coordinates."""
		raise Exception("_mapRectToClient called on base MapPanel class.")

	def _mapBitmap(self):
		"""The drawable map, converted on first use after a change and then
		   kept.  Callers must not hold onto it across a _updateMap."""
		if ((self.mapBmp is None) and (self.mapImg is not None)):
			self.mapBmp = self.mapImg.ConvertToBitmap()
		return self.mapBmp

	def _clipToMap(self, box):
		"""A brush at the edge of the map reaches past it; nothing downstream
		   copes with that, so trim first.  None if nothing is left."""
		w, h = self.map.size
		x0 = max(int(box[0]), 0)
		y0 = max(int(box[1]), 0)
		x1 = min(int(box[2]), w)
		y1 = min(int(box[3]), h)
		if ((x1 <= x0) or (y1 <= y0)):
			return None
		return (x0, y0, x1, y1)

	def _updateMap(self, rect=None):
		"""rect is the box a brush dab touched.  None means rebuild the lot -
		   a new map, a swapped image, a grid change."""
		fresh = (self.mapImg is None)
		if (fresh):
			self.mapImg = gfx.pilToWx(self.map.mapImg)
			self.mapBmp = None
			self.rgbVersion = None
			self._onImageCreated()
		self._updateGrid()
		if (self.mapImg is None):
			return
		if (tuple(self.mapImg.GetSize()) != tuple(self.map.size)):
			# The image under us has just been swapped for one of another
			# size.  The panel is about to be reset and handed the new one, so
			# anything built against these dimensions would be thrown away -
			# and wx rejects a buffer of the wrong length outright.
			return

		if ((not fresh) and (rect is not None)):
			box = self._clipToMap(rect)
			if (box is None):
				# The dab fell off the edge of the map entirely, so there is
				# nothing to bring up to date and nothing to repaint.
				return
			self._patchMap(box)
			self.RefreshRect(self._mapRectToClient(box))
			return

		if (self.map.secretLayers and (self.rgbVersion != self.map.pixelVersion)):
			# The colours themselves have moved: a swapped image, a secret
			# painted in, a layer put on or taken off.  Everything else that
			# comes through here - a grid being dragged about, most of all -
			# leaves them alone and must not pay for compositing the map.
			# _putRgb puts the alpha back itself, so this is the whole update.
			self._putRgb(self._rgb())
		else:
			self.mapImg.SetAlpha(self._alpha(self.map.mask).tobytes())
		self.rgbVersion = self.map.pixelVersion
		self.mapBmp = None
		self.Refresh(False)

	def _putRgb(self, rgb):
		"""Put a whole composite into the image.

		   SetData replaces the image's contents outright and takes the alpha
		   channel with them, so the fog has to go straight back on.  That is
		   what this exists for: a bare SetData at each call site is a fogless
		   map waiting to happen."""
		self.mapImg.SetData(gfx.rgbBytes(rgb))
		self.mapImg.SetAlpha(self._alpha(self.map.mask).tobytes())

	def refreshComposite(self):
		"""Put the whole composite back together because the way this panel
		   derives it has changed, rather than because the map has.  Ghosting
		   and the tint are the GM's own settings, and neither is a change to
		   any map."""
		if ((self.mapImg is None) or (self.map is None) or
			(not self.map.secretLayers)):
			# With no layer there is nothing for either setting to change, and
			# what is already in the image is the map's own pixels anyway.
			return
		self._putRgb(self._rgb())
		self.rgbVersion = self.map.pixelVersion
		self.mapBmp = None
		self.Refresh(False)

	def _onImageCreated(self):
		"""Hook for whatever a panel has to do once, when the image appears."""
		pass

	def _patchMap(self, box):
		"""Bring one box of the map up to date with the mask, and nothing else.

		   Both the image and the bitmap built from it are kept in step: the
		   image because a later wholesale rebuild reads from it, the bitmap
		   because that is what actually gets drawn.  The patch is always built
		   from the original image rather than read back off the bitmap, so
		   repeated dabs over the same ground cannot accumulate error."""
		x0, y0, x1, y1 = box
		w = x1 - x0
		h = y1 - y0
		alpha = self._alpha(self.map.mask, box)
		rgb = self._rgb(box)

		buf = np.frombuffer(self.mapImg.GetAlphaBuffer(), np.uint8)
		buf = buf.reshape(self.mapImg.GetHeight(), self.mapImg.GetWidth())
		buf[y0:y1, x0:x1] = alpha

		if (self.map.secretLayers):
			# A secret dab changes what colour those pixels are, and the image
			# is read again from scratch whenever the bitmap is rebuilt - so
			# the colours have to land in both or the dab is lost the next
			# time anything asks for a wholesale rebuild.
			data = np.frombuffer(self.mapImg.GetDataBuffer(), np.uint8)
			data = data.reshape(self.mapImg.GetHeight(), self.mapImg.GetWidth(), 3)
			data[y0:y1, x0:x1] = rgb
			self.rgbVersion = self.map.pixelVersion

		if (self.mapBmp is None):
			# Nothing built yet; the next paint reads the image and gets this.
			return
		rgba = np.empty((h, w, 4), np.uint8)
		rgba[:, :, :3] = rgb
		rgba[:, :, 3] = alpha
		dc = wx.MemoryDC(self.mapBmp)
		gc = wx.GraphicsContext.Create(dc)
		# SOURCE rather than the default OVER: this replaces those pixels
		# outright, alpha included, instead of blending onto what is there.
		gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
		gc.DrawBitmap(wx.Bitmap.FromBufferRGBA(w, h, rgba), x0, y0, w, h)
		del gc
		dc.SelectObject(wx.NullBitmap)

	def _updateGrid(self):
		self.grid = None
		if (self.map.grid.type == data.Grid.GRID_SQUARE):
			self.grid = grid.SquareGrid(self.map.grid.size)
		elif (self.map.grid.type == data.Grid.GRID_HEX):
			self.grid = grid.HexGrid(self.map.grid.size)
			
	def readSettings(self, settings):
		raise Exception("getSettings called on base MapPanel class.")
	
	def writeSettings(self, settings):
		raise Exception("getSettings called on base MapPanel class.")
