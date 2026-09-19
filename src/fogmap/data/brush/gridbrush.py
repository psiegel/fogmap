from .brush import Brush


class GridBrush(Brush):
	def setGrid(self, grid):
		"""Take the geometry again from the map's grid settings, which the GM
		   can change with a brush already in hand."""
		raise Exception("Call to setGrid on base GridBrush class.")
