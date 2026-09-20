from lxml import etree


class Grid(object):
	"""No grid at all, and the base the kinds that are there are built on.

	   A map always holds one of these rather than None, so that everything
	   asking whether to draw a grid, or which kind is on, can simply ask.  A
	   grid of one kind is never turned into another: the settings dialog makes
	   a new one and hands it to the map, and a map file is read as whichever
	   kind it says it is.  See gridForType and gridFromXml."""

	GRID_NONE = "None"
	GRID_SQUARE = "Square"
	GRID_HEX = "Hex"

	# What a map file calls this kind, and what the settings dialog's type
	# picker matches on.
	type = GRID_NONE

	def __init__(self, updateCallback=None):
		self.__visible = False
		self.__updateCallback = updateCallback

	def setUpdateCallback(self, callback):
		self.__updateCallback = callback

	def copy(self):
		"""Another grid of this kind, set the same way - which is what the
		   settings dialog's Cancel puts back."""
		newGrid = self.__class__(self.__updateCallback)
		# Every setting there is, so that one added to a kind later cannot be
		# forgotten here.
		newGrid.__dict__.update(self.__dict__)
		return newGrid

	def setVisible(self, visible):
		if (visible != self.__visible):
			self.__visible = visible
			self.callUpdateCallback()

	def callUpdateCallback(self):
		if (self.__updateCallback != None):
			self.__updateCallback()

	# --- map files ------------------------------------------------------------

	def toXml(self):
		element = etree.Element("grid", type=self.type,
								visible=str(self.__visible).lower())
		self.writeSettings(element)
		return element

	def writeSettings(self, element):
		"""Add this kind's own measurements to the node.  A subclass writes its
		   own after calling this; the kind that is not there has none."""
		pass

	def readSettings(self, xml):
		"""Take them back off it, held to what a grid can actually be drawn at:
		   a file can be old, or hand-edited, or both."""
		self.__visible = (xml.get("visible") == "true")

	@staticmethod
	def readNumber(xml, names, fallback):
		"""The first of these attributes the file carries, as a number.  There
		   is more than one name to try because the formats this has been
		   through called the same measurement different things."""
		for name in names:
			text = xml.get(name)
			if (text != None):
				return int(text)
		return fallback

	visible = property(lambda x: x.__visible, setVisible)
