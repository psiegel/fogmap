"""Grids drawn over the map, and the cell arithmetic that goes with them."""
from ... import data

from .grid import Grid
from .hexgrid import HexGrid
from .squaregrid import SquareGrid


def createGrid(gridData):
	"""The drawable grid a map's grid settings ask for, or None if the map has
	   no grid.  The one place that knows which settings each type is drawn
	   from."""
	if (gridData.type == data.Grid.GRID_SQUARE):
		return SquareGrid(gridData.cellWidth, gridData.cellHeight,
						  gridData.offsetX, gridData.offsetY)
	elif (gridData.type == data.Grid.GRID_HEX):
		return HexGrid(gridData.hexSize)
	return None


__all__ = ["Grid", "HexGrid", "SquareGrid", "createGrid"]
