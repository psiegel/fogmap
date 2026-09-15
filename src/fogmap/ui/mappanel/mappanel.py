import wx
import numpy as np

from ... import data
from ... import gfx

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
		self.playerPanel = None
		self.viewListener = None
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
		
	def setPlayerPanel(self, panel):
		self.playerPanel = panel
		self.Bind(wx.EVT_KEY_DOWN, self.playerPanel.onKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.playerPanel.onKeyUp)

	def setViewListener(self, listener):
		"""Called whenever this panel's scale, offset or size changes."""
		self.viewListener = listener

	def _fireViewChanged(self):
		if (self.viewListener != None):
			self.viewListener()

	def reset(self):
		self.mapImg = None
		self.mapBmp = None

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

	def onClose(self, evt):
		if (self.map != None):
			self.map.removeUpdateListener(self._updateMap)
		return True

	def _drawMap(self, gc):
		raise Exception("_drawMap called on base MapPanel class.")

	def _drawGrid(self, gc, box):
		raise Exception("_drawGrid called on base MapPanel class.")

	def _alpha(self, mask, box=None):
		"""How this panel turns the fog mask into alpha.  The two windows show
		   the same mask differently, and that is the only difference between
		   them here."""
		raise Exception("_alpha called on base MapPanel class.")

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
			self._onImageCreated()
		self._updateGrid()
		if (self.mapImg is None):
			return

		box = self._clipToMap(rect) if (rect is not None) else None
		if (fresh or (box is None)):
			self.mapImg.SetAlpha(self._alpha(self.map.mask).tobytes())
			self.mapBmp = None
			self.Refresh(False)
			return

		self._patchMap(box)
		self.RefreshRect(self._mapRectToClient(box))

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

		buf = np.frombuffer(self.mapImg.GetAlphaBuffer(), np.uint8)
		buf = buf.reshape(self.mapImg.GetHeight(), self.mapImg.GetWidth())
		buf[y0:y1, x0:x1] = alpha

		if (self.mapBmp is None):
			# Nothing built yet; the next paint reads the image and gets this.
			return
		rgba = np.empty((h, w, 4), np.uint8)
		rgba[:, :, :3] = np.asarray(self.map.mapImg.crop(box))[:, :, :3]
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
