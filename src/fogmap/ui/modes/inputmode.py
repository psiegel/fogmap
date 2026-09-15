"""The base every input mode is built on, and the toolbar helpers that go
   with writing one.

   A mode's controls are icons and tooltips rather than captions and labelled
   drop-downs: the toolbar is one row across the top of the GM window, and text
   spends its width faster than anything else.  See resources/icons/README.md
   for where the icons come from."""
import wx

from ... import resources


# Room to breathe between a mode's own toolbar controls.
BORDER = 4


def addIcon(parent, sizer, name, tip):
	"""An icon standing in for a caption, in front of the control it names.

	   It is decoration, so the tooltip is the only thing that actually says
	   what the control is - put the same one on the control itself."""
	bitmap = wx.StaticBitmap(parent, -1, resources.icon(name))
	bitmap.SetToolTip(tip)
	resources.trackIcon(bitmap, bitmap.SetBitmap, name)
	sizer.Add(bitmap, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, BORDER)
	return bitmap


def addIconButton(parent, sizer, name, tip, handler, border=BORDER * 2):
	"""A button with an icon on it and nothing else.  The tooltip carries what
	   the caption used to."""
	button = wx.BitmapButton(parent, -1, resources.icon(name), style=wx.BU_EXACTFIT)
	button.SetToolTip(tip)
	button.Bind(wx.EVT_BUTTON, handler)
	resources.trackIcon(button, button.SetBitmap, name)
	sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border)
	return button


class IconRadioGroup(object):
	"""A row of icon buttons with exactly one of them pressed: what a mode uses
	   in place of a labelled wx.Choice.

	   wx.ITEM_RADIO belongs to the toolbar itself, and a mode's controls sit on
	   a panel inside the toolbar rather than on it, so a group of toggles keeps
	   the one-at-a-time rule here instead.

	   The wx-shaped method names are deliberate: this stands in for the
	   wx.Choice it replaced, and reads the same way at the call site."""

	def __init__(self, parent, sizer, choices, handler, border=BORDER * 2):
		"""choices is ((value, iconName, tooltip), ...), and handler is called
		   with the new value whenever the GM picks a different one."""
		self.handler = handler
		self.buttons = {}
		self.value = choices[0][0] if (choices) else None
		for index, (value, name, tip) in enumerate(choices):
			button = wx.BitmapToggleButton(parent, -1, resources.icon(name),
										   style=wx.BU_EXACTFIT)
			button.SetToolTip(tip)
			button.Bind(wx.EVT_TOGGLEBUTTON,
						lambda evt, value=value: self.__onToggle(value))
			resources.trackIcon(button, button.SetBitmap, name)
			# Butted together, so the row reads as one control rather than as
			# several unrelated buttons.  The gap goes after the last of them.
			isLast = (index == (len(choices) - 1))
			sizer.Add(button, 0,
					  wx.ALIGN_CENTER_VERTICAL | (wx.RIGHT if (isLast) else 0),
					  border if (isLast) else 0)
			self.buttons[value] = button
		self.SetValue(self.value)

	def __onToggle(self, value):
		# Clicking the one already pressed would otherwise leave the group with
		# nothing selected, so the state is always set rather than accepted.
		self.SetValue(value)
		if (self.handler != None):
			self.handler(value)

	def GetValue(self):
		return self.value

	def SetValue(self, value):
		if (value in self.buttons):
			self.value = value
		for each, button in self.buttons.items():
			button.SetValue(each == self.value)

	def Enable(self, enable=True):
		for button in self.buttons.values():
			button.Enable(enable)


class InputMode(object):
	# key    - what a map file stores, so a map comes back in the mode it was
	#          left in whatever order the switcher happens to be in.
	# label  - what the switcher and the View menu call it.
	# icon   - the name of the switcher's icon, in resources/icons.  Only the
	#          modes on the switcher need one.
	# hotkey - accelerator for that menu item, or None.
	# help   - the one-line description the menu shows, and the switcher's
	#          tooltip.
	key = None
	label = None
	icon = None
	hotkey = None
	help = ""

	def __init__(self, frame):
		self.frame = frame

	@property
	def panel(self):
		return self.frame.panel

	@property
	def playerPanel(self):
		panel = self.panel
		return panel.playerPanel if (panel is not None) else None

	# --- toolbar --------------------------------------------------------------

	def buildControls(self, parent, sizer):
		"""Add this mode's own controls to its page of the toolbar book.  A
		   mode with nothing of its own to offer need not override this."""
		pass

	def updateControls(self):
		"""Bring those controls into line with the open document."""
		pass

	def isAvailable(self):
		"""Whether the mode can be entered at all just now."""
		return True

	# --- settings -------------------------------------------------------------
	# A mode's own settings belong to the GM rather than to any one map, so
	# they live in wx.Config alongside the recent-files list rather than in a
	# map file.  The frame calls these with the path already set to this
	# mode's own group.

	def readConfig(self, config):
		"""Called once, before the toolbar is built, so that a mode's controls
		   can start out where the GM last left them."""
		pass

	def writeConfig(self, config):
		"""Called as the window closes."""
		pass

	# --- lifecycle ------------------------------------------------------------

	def enter(self):
		"""The mode has just been switched to."""
		pass

	def leave(self):
		"""The mode has just been switched away from."""
		pass

	def reset(self):
		"""The map is being swapped out from under every mode."""
		pass

	def onGridChanged(self):
		pass

	def onZoomChanged(self):
		"""The GM's own zoom has changed, so whatever the mode last drew is
		   no longer where it was."""
		pass

	def onPlayerViewChanged(self):
		pass

	def onCaptureLost(self):
		pass

	def onMouseLeave(self):
		"""The mouse has left the map, so anything the mode was showing at the
		   cursor is pointing at nothing."""
		pass

	# --- input ----------------------------------------------------------------
	# pos is the mouse in map pixels: the panel undoes its own zoom once, before
	# any of this, rather than in each of the things the mouse can be driving.
	# A handler returns True if it dealt with the event, and a button press that
	# says True keeps the drag that follows, whatever the keyboard does meanwhile.

	def onLeftDown(self, evt, pos):
		return False

	def onRightDown(self, evt, pos):
		return False

	def onMouseUp(self, evt, pos):
		return False

	def onMouseMove(self, evt, pos):
		return False

	def onWheel(self, evt, pos):
		return False

	def onRightDClick(self, evt, pos):
		return False

	def draw(self, gc, active):
		"""Whatever the mode overlays on the map.

		   active is False when something else has the mouse for the moment -
		   Alt driving the player view - so that a mode can go on showing what
		   it is about without showing a cursor that would do nothing."""
		pass
