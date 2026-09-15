import os

from ..doc import Map

from .mapfile import readMapFile, writeMapFile
from .paths import isImagePath


class Document(object):
	"""The one file currently open.  Everything else in the project lives on
	   disk, either as its original or as a temp copy."""

	def __init__(self, path, map, project=None, settings=None):
		self.path = path
		self.map = map
		self.project = project
		self.settings = settings
		self.viewDirty = False

	editable = property(lambda x: x.map.editable)
	name = property(lambda x: os.path.basename(x.path) if (x.path is not None) else "Untitled")

	def isDirty(self):
		return self.editable and (self.map.contentDirty or self.viewDirty)

	def markClean(self):
		self.map.contentDirty = False
		self.viewDirty = False

	@staticmethod
	def open(path, project=None):
		if (isImagePath(path)):
			doc = Document(path, Map.forImage(path), project)
		else:
			source = path
			fromTemp = (project is not None) and project.hasTemp(path)
			if (fromTemp):
				source = project.tempPathFor(path)
			map, settings = readMapFile(source, os.path.dirname(os.path.abspath(path)))
			doc = Document(path, map, project, settings)
			# An old-format file counts as unsaved from the outset: saving it
			# is what converts it, whether or not the GM paints on it.
			doc.map.contentDirty = fromTemp or map.legacyFormat

		if (project is not None):
			remembered = project.rememberedSettings(path)
			if (remembered is not None):
				doc.settings = remembered
			doc.viewDirty = project.isDirty(path) and not doc.map.contentDirty
		return doc

	@staticmethod
	def createNew(imagePath, project=None):
		doc = Document(None, Map.createNew(imagePath), project)
		# Nothing of it exists on disk yet, so it is unsaved from the outset.
		doc.map.contentDirty = True
		return doc

	def write(self, path):
		writeMapFile(path, self.map, self.settings)
