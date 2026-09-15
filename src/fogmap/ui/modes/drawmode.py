import wx

from .inputmode import BORDER, InputMode, addLabel


class DrawMode(InputMode):
	"""The whiteboard: draw over the map with the left button, rub out with the
	   right, and point at things with the cursor.

	   Everything this mode makes shows up in the player window as well - the
	   strokes, drawn in map pixels so they sit on the same feature at either
	   zoom, and the GM's own cursor, drawn as an arrow at a fixed size on
	   screen.  None of it is part of the map, and none of it is ever saved:
	   see data/board/whiteboard.py."""

	key = "draw"
	label = "Draw"
	hotkey = "CTRL+SHIFT+3"
	help = "Draw over the map for the players, and point at it."

	# What the Fade box offers, as (label, seconds).  None leaves a stroke up
	# until it is rubbed out or the map is closed.
	FADES = (("Never", None), ("5s", 5), ("10s", 10), ("20s", 20), ("30s", 30),
			 ("1m", 60), ("2m", 120), ("5m", 300))

	DEFAULT_COLOUR = wx.Colour(255, 48, 48)
	DEFAULT_WIDTH = 8
	DEFAULT_FADE = 20
	MIN_WIDTH = 1
	MAX_WIDTH = 60

	# The eraser is the pen: it rubs out whatever the nib would have covered,
	# with a floor so that a hairline pen is not impossible to aim.
	MIN_ERASE_RADIUS = 5

	# The swatch on the toolbar, in pixels.
	SWATCH = (26, 14)

	def __init__(self, frame):
		super(DrawMode, self).__init__(frame)
		self.colour = DrawMode.DEFAULT_COLOUR
		self.width = DrawMode.DEFAULT_WIDTH
		self.fade = DrawMode.DEFAULT_FADE
		self.colourButton = None
		self.widthSlider = None
		self.fadeChoice = None
		self.clearButton = None
		# Map pixels, like everything else a mode is handed.
		self.mouse = (0, 0)
		# Where the pen outline was last actually painted, and how big, as
		# (point, width).  Neither is necessarily what they are now: several
		# moves can go by between repaints, and the slider can have been moved
		# since - cleaning up after the outline means invalidating the one
		# really on screen rather than the one about to be.
		self.ringDrawnAt = None
		self.drawing = False
		self.erasing = False
		# Whether the mouse is over the GM's map at all.  The players' arrow
		# follows it, and should not be left hanging over the map pointing at
		# nothing once the GM has gone off to the toolbar or another window.
		self.overMap = False

	# --- toolbar --------------------------------------------------------------

	def buildControls(self, parent, sizer):
		addLabel(parent, sizer, "Colour: ")
		# A swatch that opens the system colour dialog, rather than a
		# wx.ColourPickerCtrl: wxPython falls back to a Python implementation
		# of that control on the Mac, and the fallback does not work.
		self.colourButton = wx.BitmapButton(parent, -1, self.__swatch())
		self.colourButton.SetToolTip("The colour of the pen, and of the arrow "
									 "the players see.")
		self.colourButton.Bind(wx.EVT_BUTTON, self.onPickColour)
		sizer.Add(self.colourButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, BORDER * 2)

		addLabel(parent, sizer, "Size: ")
		self.widthSlider = wx.Slider(parent, -1, self.width, DrawMode.MIN_WIDTH,
									 DrawMode.MAX_WIDTH, size=(80, -1),
									 style=wx.SL_HORIZONTAL)
		self.widthSlider.SetToolTip("How wide the pen is, in map pixels - so a "
									"stroke is the same size on the map in both "
									"windows.")
		self.widthSlider.Bind(wx.EVT_SLIDER, self.onWidthChanged)
		sizer.Add(self.widthSlider, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, BORDER * 2)

		addLabel(parent, sizer, "Fade: ")
		self.fadeChoice = wx.Choice(parent, -1,
									choices=[label for label, _ in DrawMode.FADES])
		self.fadeChoice.SetToolTip("How long a stroke lasts before it fades away.  "
								   "Never keeps everything until it is rubbed out.")
		self.fadeChoice.SetSelection(self.__fadeIndex(self.fade))
		self.fadeChoice.Bind(wx.EVT_CHOICE, self.onFadeChanged)
		sizer.Add(self.fadeChoice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, BORDER * 2)

		self.clearButton = wx.Button(parent, -1, "Clear")
		self.clearButton.SetToolTip("Wipe the whole layer at once.")
		self.clearButton.Bind(wx.EVT_BUTTON, self.onClear)
		sizer.Add(self.clearButton, 0, wx.ALIGN_CENTER_VERTICAL)

	def updateControls(self):
		if (self.colourButton is None):
			return
		# Drawing works on a plain image handout as well as on a fogged map:
		# there is nothing here to save, so there is nothing to stop.
		canDraw = self.__canDraw()
		self.colourButton.Enable(canDraw)
		self.widthSlider.Enable(canDraw)
		self.fadeChoice.Enable(canDraw)
		self.clearButton.Enable(canDraw)

	def __fadeIndex(self, seconds):
		for index, (_, value) in enumerate(DrawMode.FADES):
			if (value == seconds):
				return index
		return 0

	def onPickColour(self, evt):
		data = wx.ColourData()
		data.SetColour(self.colour)
		data.SetChooseFull(True)
		dlg = wx.ColourDialog(self.frame, data)
		if (dlg.ShowModal() == wx.ID_OK):
			self.colour = dlg.GetColourData().GetColour()
			self.colourButton.SetBitmap(self.__swatch())
			# The arrow the players are watching is drawn in the pen's colour,
			# so it changes under them as soon as the pen does.
			self.__updatePointer()
			self.__refreshRing(force=True)
		dlg.Destroy()

	def __swatch(self):
		"""The button's face: the pen's colour, boxed so that a pale one still
		   reads as a swatch rather than as an empty button."""
		width, height = DrawMode.SWATCH
		bmp = wx.Bitmap(width, height)
		dc = wx.MemoryDC(bmp)
		dc.SetBackground(wx.Brush(self.colour))
		dc.Clear()
		dc.SetPen(wx.Pen(wx.Colour(64, 64, 64)))
		dc.SetBrush(wx.TRANSPARENT_BRUSH)
		dc.DrawRectangle(0, 0, width, height)
		dc.SelectObject(wx.NullBitmap)
		return bmp

	def onWidthChanged(self, evt):
		self.width = self.widthSlider.GetValue()
		self.__refreshRing(force=True)

	def onFadeChanged(self, evt):
		index = self.fadeChoice.GetSelection()
		if (index == wx.NOT_FOUND):
			return
		self.fade = DrawMode.FADES[index][1]
		self.__applyFade()

	def onClear(self, evt):
		board = self.board()
		if (board is not None):
			board.clear()

	def __applyFade(self):
		board = self.board()
		if (board is not None):
			board.setLifetime(self.fade)

	# --- settings -------------------------------------------------------------

	def readConfig(self, config):
		# The colour is kept as a plain RGB integer rather than as text: it
		# goes back and forth without a parse that could fail on a hand-edited
		# config and leave the GM drawing in nothing.
		packed = config.ReadInt("colour", (DrawMode.DEFAULT_COLOUR.Red() << 16) |
										  (DrawMode.DEFAULT_COLOUR.Green() << 8) |
										  DrawMode.DEFAULT_COLOUR.Blue())
		self.colour = wx.Colour((packed >> 16) & 0xFF, (packed >> 8) & 0xFF,
								packed & 0xFF)
		self.width = min(max(config.ReadInt("width", DrawMode.DEFAULT_WIDTH),
							 DrawMode.MIN_WIDTH), DrawMode.MAX_WIDTH)
		# Zero says Never, which is also what an unrecognised value falls back
		# to being: the box has to be able to show whatever comes out of here.
		seconds = config.ReadInt("fade", DrawMode.DEFAULT_FADE)
		self.fade = DrawMode.FADES[self.__fadeIndex(seconds)][1]

	def writeConfig(self, config):
		config.WriteInt("colour", (self.colour.Red() << 16) |
								  (self.colour.Green() << 8) | self.colour.Blue())
		config.WriteInt("width", self.width)
		config.WriteInt("fade", self.fade if (self.fade is not None) else 0)

	# --- lifecycle ------------------------------------------------------------

	def board(self):
		panel = self.panel
		return panel.whiteboard if (panel is not None) else None

	def __canDraw(self):
		return ((self.panel is not None) and (self.panel.map is not None) and
				(self.board() is not None))

	def enter(self):
		# The board outlives any one visit to this mode - strokes go on fading
		# while the GM is back in Fog mode - so the setting is pushed onto it
		# here rather than being read off the box at every stroke.
		self.__applyFade()

	def leave(self):
		self.overMap = False
		self.__endDrag()
		# Whatever is on screen was drawn by somebody else from here on, and
		# the players should not be left watching a cursor that has stopped
		# meaning anything.
		self.ringDrawnAt = None
		self.__showPointer(None)

	def reset(self):
		self.overMap = False
		self.__endDrag()
		self.ringDrawnAt = None
		self.__showPointer(None)

	def onZoomChanged(self):
		self.ringDrawnAt = None

	def onCaptureLost(self):
		self.drawing = False
		self.erasing = False

	def onMouseLeave(self):
		self.overMap = False
		self.__showPointer(None)
		self.__refreshRing(force=True)
		self.ringDrawnAt = None

	def __endDrag(self):
		board = self.board()
		if (self.drawing and (board is not None)):
			board.end()
		self.drawing = False
		self.erasing = False
		panel = self.panel
		if ((panel is not None) and panel.HasCapture()):
			panel.ReleaseMouse()

	def __showPointer(self, pos):
		player = self.playerPanel
		if (player is not None):
			player.setPointer(pos, self.colour)

	def __updatePointer(self):
		"""Point the players at wherever the GM is, or at nothing at all if the
		   GM is not over the map."""
		self.__showPointer(self.mouse if self.overMap else None)

	# --- input ----------------------------------------------------------------

	def onLeftDown(self, evt, pos):
		if (not self.__canDraw()):
			return False
		self.__capture()
		self.drawing = True
		self.board().begin((self.colour.Red(), self.colour.Green(),
							self.colour.Blue()), self.width, pos)
		return True

	def onRightDown(self, evt, pos):
		if (not self.__canDraw()):
			return False
		self.__capture()
		self.erasing = True
		self.__erase(pos)
		return True

	def __capture(self):
		panel = self.panel
		if ((panel is not None) and (not panel.HasCapture())):
			panel.CaptureMouse()

	def __erase(self, pos):
		self.board().erase(pos, max(self.width / 2.0, DrawMode.MIN_ERASE_RADIUS))

	def onMouseUp(self, evt, pos):
		self.__endDrag()
		return False

	def onMouseMove(self, evt, pos):
		panel = self.panel
		panel.setModeCursor(wx.CURSOR_CROSS)
		self.mouse = pos
		self.overMap = True

		if (self.__canDraw()):
			if (self.drawing and evt.LeftIsDown()):
				self.board().extend(pos)
			elif (self.erasing and evt.RightIsDown()):
				self.__erase(pos)
		# The players follow the GM's cursor whether or not anything is being
		# drawn: pointing at something is half of what this mode is for.
		self.__showPointer(pos)
		self.__refreshRing()
		return True

	def __ringRect(self, pt, width):
		"""Where a pen outline of that width, at pt - a map point - lands on
		   the panel."""
		half = width / 2.0 + 1
		return self.panel._mapRectToClient((pt[0] - half, pt[1] - half,
											pt[0] + half, pt[1] + half))

	def __refreshRing(self, force=False):
		"""Invalidate just the pen outline: where it is on screen now, and
		   where it is about to be.  A whole-panel Refresh to move a small
		   circle would cost the size of the map."""
		if (self.panel is None):
			return
		rect = self.__ringRect(self.mouse, self.width)
		if (self.ringDrawnAt is not None):
			if ((not force) and (self.ringDrawnAt == (self.mouse, self.width))):
				return
			# Taken from what was actually drawn rather than from the pen as it
			# stands now, or narrowing the pen would leave the old, wider
			# outline behind on screen.
			rect = rect.Union(self.__ringRect(*self.ringDrawnAt))
		self.panel.RefreshRect(rect.Inflate(2, 2))

	def draw(self, gc, active):
		self.ringDrawnAt = None
		# Holding Alt lends the mouse to the player view, which leaves this
		# mode drawn but not driving anything.  The nib and the players' arrow
		# both stand for where the pen would go next, so both go away for as
		# long as that lasts and come back together with the key.
		self.__showPointer(self.mouse if (active and self.overMap) else None)
		if ((not active) or (not self.overMap)):
			return
		# The nib, where it would next leave a mark and the size it would leave
		# it.  Drawn under the zoom, in map pixels, because that is what the
		# width is measured in.
		gc.PushState()
		self.panel._applyMapTransform(gc)
		gc.SetBrush(wx.TRANSPARENT_BRUSH)
		half = self.width / 2.0
		gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(0, 0, 0, 120))
							   .Width(3.0 / self.panel.scale)))
		gc.DrawEllipse(self.mouse[0] - half, self.mouse[1] - half,
					   self.width, self.width)
		gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(self.colour)
							   .Width(1.0 / self.panel.scale)))
		gc.DrawEllipse(self.mouse[0] - half, self.mouse[1] - half,
					   self.width, self.width)
		gc.PopState()
		self.ringDrawnAt = (self.mouse, self.width)
