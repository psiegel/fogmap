"""What is still outstanding for one file in a project."""


class DirtyEntry(object):
	"""What is outstanding for one file.

	   hasTemp means the fog, grid or image changed and a full copy is sitting
	   in .fogmap/.  legacy means nothing was edited at all - the file is
	   simply still in the old mask format and wants rewriting in place.
	   Without either, only the player view moved and the settings held here
	   are the whole of the change."""

	def __init__(self, rel, hasTemp, settings, legacy=False):
		self.rel = rel
		self.hasTemp = hasTemp
		self.settings = settings
		self.legacy = legacy
