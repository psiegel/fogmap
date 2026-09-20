from .... import hex

from .cellgrid import CellGrid
from .grid import Grid


class HexGrid(CellGrid):
	"""Hexes: the box one fits in, the length of the two edges that run across
	   the way it points, and which way that is.  See fogmap.hex for what those
	   measurements make of a hexagon."""

	type = Grid.GRID_HEX

	# An edge of nothing at all is not a hexagon; how long it is allowed to get
	# depends on the hex it belongs to, which is the dialog's business.
	MIN_EDGE = 1

	def __init__(self, updateCallback=None):
		super(HexGrid, self).__init__(updateCallback)
		self.__width = CellGrid.DEFAULT_SIZE
		self.__height = CellGrid.DEFAULT_SIZE
		self.__edge = CellGrid.DEFAULT_SIZE // 2
		self.__orientation = hex.FLAT_TOP

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

	def setEdge(self, edge):
		edge = HexGrid.asEdge(edge)
		if (edge != self.__edge):
			self.__edge = edge
			self.callUpdateCallback()

	def setOrientation(self, orientation):
		orientation = HexGrid.asOrientation(orientation)
		if (orientation != self.__orientation):
			self.__orientation = orientation
			self.callUpdateCallback()

	@staticmethod
	def asEdge(value):
		return max(HexGrid.MIN_EDGE, min(CellGrid.MAX_SIZE, int(value)))

	@staticmethod
	def asOrientation(value):
		return value if (value in hex.ORIENTATIONS) else hex.FLAT_TOP

	def writeSettings(self, element):
		super(HexGrid, self).writeSettings(element)
		element.set("width", str(self.__width))
		element.set("height", str(self.__height))
		element.set("edge", str(self.__edge))
		element.set("orientation", self.__orientation)

	def readSettings(self, xml):
		super(HexGrid, self).readSettings(xml)
		# The "hex" prefixes are what the version that first gave a hex more
		# than one measurement wrote.  Older files carry a single size - the
		# hex both ways across, flat topped, with its edges half of that.
		size = Grid.readNumber(xml, ("size", "hexSize"), CellGrid.DEFAULT_SIZE)
		self.__width = CellGrid.asSize(
			Grid.readNumber(xml, ("width", "hexWidth"), size))
		self.__height = CellGrid.asSize(
			Grid.readNumber(xml, ("height", "hexHeight"), size))
		self.__edge = HexGrid.asEdge(
			Grid.readNumber(xml, ("edge", "hexEdge"), size // 2))
		self.__orientation = HexGrid.asOrientation(
			xml.get("orientation") or xml.get("hexOrientation"))

	width = property(lambda x: x.__width, setWidth)
	height = property(lambda x: x.__height, setHeight)
	edge = property(lambda x: x.__edge, setEdge)
	orientation = property(lambda x: x.__orientation, setOrientation)
