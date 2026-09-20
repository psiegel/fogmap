"""The settings each kind of grid offers, one panel per kind."""
import wx

from .. import hex

from .fields import HGAP, VGAP, ChoiceField, FlagField, NumericField


# The GM is setting these against a map they can see, so every change goes
# straight onto the grid and both windows repaint as it happens.  Cancel puts
# back the copy the dialog was handed.
class GridSettingsPanel(wx.Panel):
	"""A column of fields, one per setting, all lined up on a shared grid
	   sizer.  A grid type with nothing to set adds no fields and takes up no
	   room, which is what the None grid does."""

	def __init__(self, parent, grid):
		super(GridSettingsPanel, self).__init__(parent, -1)
		self.grid = grid
		self.sizer = wx.FlexGridSizer(cols=3, vgap=VGAP, hgap=HGAP)
		# The sliders take whatever width is going; the labels and the boxes
		# they are typed into keep theirs.
		self.sizer.AddGrowableCol(2, 1)
		self.build()
		self.SetSizer(self.sizer)

	def build(self):
		"""Put this kind of grid's fields on the panel."""
		pass

	# --- the fields a panel is built from -------------------------------------

	def addNumber(self, label, value, minValue, maxValue, tip, onChange):
		return NumericField(self, self.sizer, label, value, minValue, maxValue,
							1, tip, onChange)

	def addChoice(self, label, value, choices, tip, onChange):
		return ChoiceField(self, self.sizer, label, value, choices, tip,
						   onChange)

	def addFlag(self, label, value, tip, onChange):
		return FlagField(self, self.sizer, label, value, tip, onChange)

	def addOrigin(self):
		"""Where the cells start counting from, which every grid laid over a
		   map has to be able to shift."""
		limit = self.grid.MAX_OFFSET
		self.offsetX = self.addNumber("X Offset", self.grid.offsetX,
									  -limit, limit,
									  "Shifts the whole grid sideways, for a "
									  "map whose cells do not start at its "
									  "left edge.", self.onOffsetX)
		self.offsetY = self.addNumber("Y Offset", self.grid.offsetY,
									  -limit, limit,
									  "Shifts the whole grid up or down, for "
									  "a map whose cells do not start at its "
									  "top edge.", self.onOffsetY)

	def onOffsetX(self, value):
		self.grid.offsetX = value

	def onOffsetY(self, value):
		self.grid.offsetY = value


class SquareGridPanel(GridSettingsPanel):
	def build(self):
		self.width = self.addNumber("Cell Width", self.grid.width,
									self.grid.MIN_SIZE, self.grid.MAX_SIZE,
									"How wide one cell is, in map pixels.",
									self.onWidth)
		self.height = self.addNumber("Cell Height", self.grid.height,
									 self.grid.MIN_SIZE, self.grid.MAX_SIZE,
									 "How tall one cell is, in map pixels.",
									 self.onHeight)
		self.addOrigin()

	def onWidth(self, value):
		self.grid.width = value

	def onHeight(self, value):
		self.grid.height = value


class HexGridPanel(GridSettingsPanel):
	def build(self):
		self.orientation = self.addChoice("Orientation",
										  self.grid.orientation,
										  hex.ORIENTATIONS,
										  "Flat topped hexes have an edge "
										  "across the top and a corner at "
										  "each side; pointy topped ones the "
										  "other way about.",
										  self.onOrientation)

		# Ticked to begin with where the hexes already stand that way, so that
		# a grid laid out as proper hexes stays that way when it is picked up
		# again and nudged.
		self.lock = self.addFlag("Lock Width/Height",
								 self.grid.width == self.grid.height,
								 "Holds the width and the height the same, so "
								 "that setting either one sets the other.",
								 self.onLock)
		self.width = self.addNumber("Hex Width", self.grid.width,
									self.grid.MIN_SIZE, self.grid.MAX_SIZE,
									"How wide one hex is, across the box it "
									"fits in.", self.onWidth)
		self.height = self.addNumber("Hex Height", self.grid.height,
									 self.grid.MIN_SIZE, self.grid.MAX_SIZE,
									 "How tall one hex is, down the box it "
									 "fits in.", self.onHeight)

		self.regular = self.addFlag("Proper Hex", self.__isRegular(),
									"Holds the edge at half the way the hexes "
									"point, which is what a regular hexagon "
									"has.  The edge is not the GM's to set "
									"while this is ticked.",
									self.onRegular)
		self.edge = self.addNumber("Edge Length", self.grid.edge,
								   self.grid.MIN_EDGE, self.grid.MAX_SIZE,
								   "How long the two edges are that run "
								   "across the way the hex is pointed: the "
								   "top and bottom of a flat topped hex, the "
								   "left and right of a pointy topped one.  "
								   "Half the way across gives a proper "
								   "hexagon; anything else leans its corners "
								   "in or out to suit the map, without "
								   "changing how big it is.", self.onEdge)

		self.addOrigin()
		self.__conformEdge()

	def onOrientation(self, value):
		self.grid.orientation = value
		# Which measurement the edge is half of has just changed with it.
		self.__conformEdge()

	def onWidth(self, value):
		self.grid.width = value
		if (self.lock.GetValue()):
			self.height.SetValue(value)
			self.grid.height = value
		self.__conformEdge()

	def onHeight(self, value):
		self.grid.height = value
		if (self.lock.GetValue()):
			self.width.SetValue(value)
			self.grid.width = value
		self.__conformEdge()

	def onEdge(self, value):
		self.grid.edge = value

	def onLock(self, locked):
		if (locked):
			# The width leads, so that ticking the box settles the two on
			# something rather than leaving them as they were.
			self.onWidth(self.width.GetValue())

	def onRegular(self, regular):
		self.__conformEdge()

	def __span(self):
		"""How far across the hex is the way it points, which is what its two
		   parallel edges are measured against."""
		return (self.grid.width
				if (self.grid.orientation == hex.FLAT_TOP)
				else self.grid.height)

	def __isRegular(self):
		return self.grid.edge == HexGridPanel.__halfSpan(self.__span())

	@staticmethod
	def __halfSpan(span):
		return int(round(span / 2.0))

	def __conformEdge(self):
		"""Put the edge field back in step with the hex it belongs to.

		   It can never be longer than the hex is across - at exactly that the
		   corners have gone and the cells are rectangles - and while Proper
		   Hex is ticked it is worked out rather than chosen."""
		span = self.__span()
		self.edge.SetRange(self.grid.MIN_EDGE, span)
		if (self.regular.GetValue()):
			self.edge.SetValue(HexGridPanel.__halfSpan(span))
		self.edge.Enable(not self.regular.GetValue())
		# Neither SetRange nor SetValue calls back, and either can have moved
		# the number, so the grid is told what the field came to.
		self.grid.edge = self.edge.GetValue()
