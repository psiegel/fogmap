"""Brushes: the shapes the GM paints fog away and back with."""
from ..doc import HexGrid, SquareGrid

from .brush import Brush, makeBoxCenteredOnPoint
from .gridbrush import GridBrush
from .hexgridbrush import HexGridBrush
from .roundfreehandbrush import RoundFreehandBrush
from .squarefreehandbrush import SquareFreehandBrush
from .squaregridbrush import SquareGridBrush


def createGridBrush(grid, brushSize):
	"""The brush that snaps to a map's grid, or None if the map has no grid to
	   snap to.  The one place that knows which brush goes with which type."""
	if (isinstance(grid, SquareGrid)):
		return SquareGridBrush(grid, brushSize)
	elif (isinstance(grid, HexGrid)):
		return HexGridBrush(grid, brushSize)
	return None


__all__ = ["Brush", "GridBrush", "HexGridBrush", "RoundFreehandBrush",
		   "SquareFreehandBrush", "SquareGridBrush", "createGridBrush",
		   "makeBoxCenteredOnPoint"]
