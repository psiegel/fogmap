import os

from PIL import Image
from lxml import etree

from ... import gfx

from .grid import Grid
from .mask import isLegacyMaskNode, readMaskNode, writeMaskNode


class Map(object):
	def __init__(self, mapImg, mapImgPath, mask, editable=True):
		self.mapImg = mapImg
		self.mapImgPath = mapImgPath
		# One bit per pixel; the alpha the two windows draw with is derived
		# from it.  See gfx.playerAlpha / gfx.gmAlpha.
		self.mask = mask

		# True when this came out of a file still holding the old two-mask
		# format, which makes it unsaved from the moment it is opened so that
		# writing it back converts it.
		self.legacyFormat = False

		# False for a plain image opened straight from the project tree: there
		# is no fog to paint and nowhere to save it back to.
		self.editable = editable
		# Set by anything that would have to be saved as mask data - fog, grid
		# or a swapped image.  Merely moving the player view does not count;
		# that is tracked on the document, and costs far less to write out.
		self.contentDirty = False

		self.__grid = Grid(self.__contentChanged)

		self.updateListeners = []

	def setGrid(self, grid):
		self.__grid = grid
		self.__grid.setUpdateCallback(self.__contentChanged)
	grid = property(lambda x: x.__grid, setGrid)

	@staticmethod
	def createNew(imgPath):
		mapImg = Image.open(imgPath).convert("RGBA")
		return Map(mapImg, imgPath, gfx.createMask(mapImg.size[0], mapImg.size[1], False))

	@staticmethod
	def forImage(imgPath):
		"""A plain image, shown whole to the players with no fog at all.

		   The mask is entirely revealed, which the players see as the whole
		   image and the GM sees at full brightness rather than the usual
		   half - both fall out of the one mask, so there is nothing here to
		   keep in step."""
		mapImg = Image.open(imgPath).convert("RGBA")
		mask = gfx.createMask(mapImg.size[0], mapImg.size[1], True)
		return Map(mapImg, imgPath, mask, editable=False)

	@staticmethod
	def resolveImagePath(imgPath, baseDir):
		"""Where the image actually is.

		   <imagePath> is stored relative to the map file, so it is read against
		   the folder that file lives in.  Absolute paths, which is what older
		   map files hold, are used as they stand."""
		if ((imgPath is not None) and (baseDir is not None) and
			(not os.path.isabs(imgPath))):
			return os.path.normpath(os.path.join(baseDir, imgPath))
		return imgPath

	@staticmethod
	def relativeImagePath(imgPath, baseDir):
		"""How the path is written back: relative to the map file, so a project
		   folder keeps working when it is copied or moved somewhere else."""
		if ((imgPath is None) or (baseDir is None)):
			return imgPath
		try:
			return os.path.relpath(imgPath, baseDir)
		except ValueError:
			# No common root to be relative to, so there is nothing to shorten.
			return imgPath

	@staticmethod
	def read(root, baseDir=None):
		mapImg = None
		imgPath = None
		mask = None
		legacy = False
		grid = Grid()
		for element in root:
			if (element.tag == "imagePath"):
				imgPath = element.text
				mapImg = Image.open(Map.resolveImagePath(imgPath, baseDir)).convert("RGBA")
			elif (element.tag == "grid"):
				grid.fromXml(element)
			elif (element.tag == "maskData"):
				mask = readMaskNode(element)
				legacy = legacy or isLegacyMaskNode(element)
			elif (element.tag == "alphaMaskData"):
				# Derived from <maskData> and no longer kept; its presence is
				# itself enough to date the file.
				legacy = True

		# Held resolved, so the image can be found again whatever the working
		# directory is; write() turns it back into a relative path.
		map = Map(mapImg, Map.resolveImagePath(imgPath, baseDir), mask)
		map.legacyFormat = legacy
		map.setGrid(grid)
		return map

	def replaceImage(self, path):
		self.mapImg = Image.open(path).convert("RGBA")
		self.mapImgPath = path
		self.__contentChanged()

	def write(self, root, baseDir=None):
		"""baseDir is the folder the image path is written relative to - the
		   folder the map file belongs in."""
		pathNode = etree.Element("imagePath")
		pathNode.text = Map.relativeImagePath(self.mapImgPath, baseDir)
		root.append(pathNode)

		gridNode = self.grid.toXml()
		root.append(gridNode)

		root.append(writeMaskNode("maskData", self.mask))

		return root

	def applyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, gfx.MASK_REVEALED)
		self.__contentChanged(brush.bounds(x, y))

	def unapplyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, gfx.MASK_HIDDEN)
		self.__contentChanged(brush.bounds(x, y))

	def __contentChanged(self, rect=None):
		self.contentDirty = True
		self.__fireUpdateListeners(rect)

	def addUpdateListener(self, listener):
		self.updateListeners.append(listener)

	def removeUpdateListener(self, listener):
		self.updateListeners.remove(listener)

	def __fireUpdateListeners(self, rect=None):
		"""rect is the box a brush dab touched, or None when the change was
		   wholesale - a new grid, a swapped image - and everything has to be
		   rebuilt."""
		for listener in self.updateListeners:
			listener(rect)

	size = property(lambda x: x.mapImg.size)
