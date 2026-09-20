"""Grids drawn over the map, and the cell arithmetic that goes with them."""
from ... import data
from ... import hex

from .grid import Grid
from .hexgrid import HexGrid
from .squaregrid import SquareGrid


def createGrid(gridData):
	"""The drawable grid a map's grid settings ask for, or None if the map has
	   no grid.  The one place that knows which settings each type is drawn
	   from."""
	if (isinstance(gridData, data.SquareGrid)):
		return SquareGrid(gridData.width, gridData.height,
						  gridData.offsetX, gridData.offsetY)
	elif (isinstance(gridData, data.HexGrid)):
		return HexGrid(hex.HexLayout.forGrid(gridData))
	return None


__all__ = ["Grid", "HexGrid", "SquareGrid", "createGrid"]
