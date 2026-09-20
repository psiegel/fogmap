from .cellgrid import CellGrid
from .grid import Grid


class SquareGrid(CellGrid):
	"""Cells of a fixed width and height, which need not be the same."""

	type = Grid.GRID_SQUARE

	def __init__(self, updateCallback=None):
		super(SquareGrid, self).__init__(updateCallback)
		self.__width = CellGrid.DEFAULT_SIZE
		self.__height = CellGrid.DEFAULT_SIZE

	def setWidth(self, width):
		width = CellGrid.asSize(width)
		if (width != self.__width):
			self.__width = width
			self.callUpdateCallback()

	def setHeight(self, height):
		height = CellGrid.asSize(height)
		if (height != self.__height):
			self.__height = height
			self.callUpdateCallback()

	def writeSettings(self, element):
		super(SquareGrid, self).writeSettings(element)
		element.set("width", str(self.__width))
		element.set("height", str(self.__height))

	def readSettings(self, xml):
		super(SquareGrid, self).readSettings(xml)
		# "cellWidth" and "cellHeight" are what the version that first told the
		# two apart wrote; "size" is older still, from when a cell was a square
		# and one number did for it.
		size = Grid.readNumber(xml, ("size",), CellGrid.DEFAULT_SIZE)
		self.__width = CellGrid.asSize(
			Grid.readNumber(xml, ("width", "cellWidth"), size))
		self.__height = CellGrid.asSize(
			Grid.readNumber(xml, ("height", "cellHeight"), size))

	width = property(lambda x: x.__width, setWidth)
	height = property(lambda x: x.__height, setHeight)
