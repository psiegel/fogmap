import os


class Node(object):
	"""One row of the sidebar tree."""

	def __init__(self, path, isDir, children=None):
		self.path = path
		self.isDir = isDir
		self.children = children if (children is not None) else []

	name = property(lambda x: os.path.basename(x.path))
