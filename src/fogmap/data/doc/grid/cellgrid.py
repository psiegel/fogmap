from .grid import Grid


class CellGrid(Grid):
	"""A grid that has cells, and so has an origin to lay them out from: a grid
	   over a map somebody else drew rarely starts in its corner."""

	# What a measurement will take.  The settings dialog builds its controls to
	# match, and these hold whatever an ancient or hand-edited file says.
	MIN_SIZE = 4
	MAX_SIZE = 512
	MAX_OFFSET = 512
	DEFAULT_SIZE = 8

	def __init__(self, updateCallback=None):
		super(CellGrid, self).__init__(updateCallback)
		self.__offsetX = 0
		self.__offsetY = 0

	def setOffsetX(self, offset):
		offset = CellGrid.asOffset(offset)
		if (offset != self.__offsetX):
			self.__offsetX = offset
			self.callUpdateCallback()

	def setOffsetY(self, offset):
		offset = CellGrid.asOffset(offset)
		if (offset != self.__offsetY):
			self.__offsetY = offset
			self.callUpdateCallback()

	@staticmethod
	def asSize(value):
		return max(CellGrid.MIN_SIZE, min(CellGrid.MAX_SIZE, int(value)))

	@staticmethod
	def asOffset(value):
		return max(-CellGrid.MAX_OFFSET, min(CellGrid.MAX_OFFSET, int(value)))

	def writeSettings(self, element):
		super(CellGrid, self).writeSettings(element)
		element.set("offsetX", str(self.__offsetX))
		element.set("offsetY", str(self.__offsetY))

	def readSettings(self, xml):
		super(CellGrid, self).readSettings(xml)
		self.__offsetX = CellGrid.asOffset(Grid.readNumber(xml, ("offsetX",), 0))
		self.__offsetY = CellGrid.asOffset(Grid.readNumber(xml, ("offsetY",), 0))

	offsetX = property(lambda x: x.__offsetX, setOffsetX)
	offsetY = property(lambda x: x.__offsetY, setOffsetY)
