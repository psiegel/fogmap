from .brush import Brush


class GridBrush(Brush):
	def setGridSize(self, size):
		raise Exception("Call to setGridSize on base GridBrush class.")		
