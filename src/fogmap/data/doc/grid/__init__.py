"""A map's grid: which kind it is, how big its cells are, and where they start
   counting from.

   One class per kind, so that a square grid carries nothing about hexes and a
   map with no grid carries nothing at all.  Changing kind means a new grid
   rather than a grid changing its mind, which is what these two make."""
from .cellgrid import CellGrid
from .grid import Grid
from .hexgrid import HexGrid
from .squaregrid import SquareGrid


def gridForType(type, updateCallback=None):
	"""A new grid of the kind that goes by this name, at its own defaults.

	   Anything else - a map that says it has no grid, a file from some later
	   version that knows a kind this one does not - is the grid that is not
	   there, which draws nothing and says so."""
	for gridClass in (SquareGrid, HexGrid):
		if (gridClass.type == type):
			return gridClass(updateCallback)
	return Grid(updateCallback)


def gridFromXml(xml, updateCallback=None):
	"""The grid a map file describes, of whichever kind it says it is."""
	grid = gridForType(xml.get("type"), updateCallback)
	grid.readSettings(xml)
	return grid


__all__ = ["CellGrid", "Grid", "HexGrid", "SquareGrid", "gridForType",
		   "gridFromXml"]
