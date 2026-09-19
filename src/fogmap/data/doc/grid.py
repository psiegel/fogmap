from lxml import etree


class GridOption(object):
	"""One setting a grid type exposes, and everything needed to put a control
	   on screen for it: what it is called, what it is worth to begin with, and
	   the range and step it will take.

	   The settings dialog is built out of these rather than knowing the grid
	   types itself, so a new kind of grid arrives with its own settings and
	   needs nothing of the UI."""

	def __init__(self, key, label, default, minValue, maxValue, step=1, tip=""):
		self.key = key
		self.label = label
		self.default = default
		self.minValue = minValue
		self.maxValue = maxValue
		self.step = step
		self.tip = tip

	def clamp(self, value):
		"""The nearest value this option will actually take: in range, and on a
		   step boundary counted up from the minimum.  A value can arrive from
		   anywhere - a typed-in number, an older map file - so nothing is taken
		   at face value."""
		value = max(self.minValue, min(self.maxValue, int(value)))
		steps = int(round((value - self.minValue) / float(self.step)))
		return min(self.minValue + (steps * self.step), self.maxValue)


class Grid(object):
	GRID_NONE = "None"
	GRID_SQUARE = "Square"
	GRID_HEX = "Hex"

	# What each grid type is made of.  A type not listed here has nothing to
	# set, which is what makes GRID_NONE work without a special case.
	OPTIONS = {
		GRID_NONE: (),
		GRID_SQUARE: (
			GridOption("cellWidth", "Cell Width", 8, 4, 512, 1,
					   "How wide one cell is, in map pixels."),
			GridOption("cellHeight", "Cell Height", 8, 4, 512, 1,
					   "How tall one cell is, in map pixels."),
			GridOption("offsetX", "X Offset", 0, -512, 512, 1,
					   "Shifts the whole grid sideways, for a map whose cells "
					   "do not start at its left edge."),
			GridOption("offsetY", "Y Offset", 0, -512, 512, 1,
					   "Shifts the whole grid up or down, for a map whose "
					   "cells do not start at its top edge."),
		),
		GRID_HEX: (
			GridOption("hexSize", "Hex Size", 8, 8, 256, 4,
					   "Corner to opposite corner, in map pixels.  Hexes only "
					   "tile at multiples of four."),
		),
	}

	# Every option there is, by key.  Two types asking for the same setting
	# share one of these, and so share its value.
	OPTIONS_BY_KEY = dict((option.key, option)
						  for options in OPTIONS.values()
						  for option in options)

	def __init__(self, updateCallback=None):
		self.__type = Grid.GRID_NONE
		# Every option of every type, not only the current one's: a GM who
		# tries the hex grid and goes back to squares should find the square
		# settings as they were left.
		self.__values = Grid.defaultValues()
		self.__visible = False
		self.__updateCallback = updateCallback

	@staticmethod
	def defaultValues():
		return dict((key, option.default)
					for key, option in Grid.OPTIONS_BY_KEY.items())

	@staticmethod
	def optionsForType(type):
		return Grid.OPTIONS.get(type, ())

	@property
	def options(self):
		"""The settings this grid's own type has, in the order they should be
		   shown."""
		return Grid.optionsForType(self.__type)

	def setUpdateCallback(self, callback):
		self.__updateCallback = callback

	def copy(self):
		newGrid = Grid(self.__updateCallback)
		newGrid.__type = self.__type
		newGrid.__values = dict(self.__values)
		newGrid.__visible = self.__visible
		return newGrid

	def setType(self, type):
		self.__type = type
		self.callUpdateCallback()

	def setVisible(self, visible):
		self.__visible = visible
		self.callUpdateCallback()

	def getOption(self, key):
		return self.__values[key]

	def setOption(self, key, value):
		value = Grid.OPTIONS_BY_KEY[key].clamp(value)
		if (self.__values[key] == value):
			# Dragging a slider fires a change for every tick of it, and most
			# of those land on the value it already had.  Each one that gets
			# through here costs a repaint and marks the map unsaved.
			return
		self.__values[key] = value
		self.callUpdateCallback()

	def toXml(self):
		element = etree.Element("grid", type=self.type,
								visible=str(self.visible).lower())
		# Every option, not just the current type's, for the same reason they
		# are all held in memory: switching type and back should not lose the
		# settings that went with the old one.
		for key in sorted(self.__values.keys()):
			element.set(key, str(self.__values[key]))
		return element

	def fromXml(self, xml):
		self.__type = xml.get("type")
		self.__visible = xml.get("visible") == "true"
		self.__values = Grid.defaultValues()
		for key, option in Grid.OPTIONS_BY_KEY.items():
			value = xml.get(key)
			if (value != None):
				self.__values[key] = option.clamp(int(value))
		# Maps written before the grid had more than one measurement carry a
		# single "size", which was the cell square or the hex across.
		size = xml.get("size")
		if (size != None):
			size = int(size)
			for key in ("cellWidth", "cellHeight", "hexSize"):
				if (xml.get(key) is None):
					self.__values[key] = Grid.OPTIONS_BY_KEY[key].clamp(size)
		self.callUpdateCallback()

	def callUpdateCallback(self):
		if (self.__updateCallback != None):
			self.__updateCallback()

	type = property(lambda x: x.__type, setType)
	visible = property(lambda x: x.__visible, setVisible)

	# The settings themselves, for the code that draws a grid of one particular
	# kind.  Anything working across types - the settings dialog, saving - goes
	# through the options instead.
	cellWidth = property(lambda x: x.getOption("cellWidth"),
						 lambda x, v: x.setOption("cellWidth", v))
	cellHeight = property(lambda x: x.getOption("cellHeight"),
						  lambda x, v: x.setOption("cellHeight", v))
	offsetX = property(lambda x: x.getOption("offsetX"),
					   lambda x, v: x.setOption("offsetX", v))
	offsetY = property(lambda x: x.getOption("offsetY"),
					   lambda x, v: x.setOption("offsetY", v))
	hexSize = property(lambda x: x.getOption("hexSize"),
					   lambda x, v: x.setOption("hexSize", v))
