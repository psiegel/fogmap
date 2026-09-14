from PIL import Image
import base64
import os
import zlib
from lxml import etree

import gfx

# Mask payloads are runs of identical bytes almost end to end, so deflating
# them before base64 turns what used to be the whole weight of a map file into
# a rounding error.  The attribute is what tells a new file from an old one.
MASK_ENCODING = "zlib"


def readMaskNode(element):
	"""A <maskData> element as a 1-bit mask.

	   Also reads the old byte-per-pixel form, where the file held a separate
	   alpha mask alongside this one.  The two were only ever two views of the
	   same boolean - 0/255 here, 128/255 there - so this one carries all of
	   it and the other is thrown away."""
	w = int(element.get("width"))
	h = int(element.get("height"))
	raw = base64.b64decode(element.text)
	if (element.get("encoding") == MASK_ENCODING):
		raw = zlib.decompress(raw)
	mask = Image.frombytes(element.get("mode"), (w, h), raw)
	if (mask.mode != gfx.MASK_MODE):
		# Threshold explicitly: convert() on its own would dither, which would
		# leave every fog edge speckled.
		mask = mask.point(lambda v: gfx.MASK_REVEALED if (v > 127) else gfx.MASK_HIDDEN,
						  mode=gfx.MASK_MODE)
	return mask


def writeMaskNode(tag, mask):
	node = etree.Element(tag, mode=mask.mode, encoding=MASK_ENCODING,
						 width=str(mask.size[0]), height=str(mask.size[1]))
	# tobytes() is where the bit packing happens; rows are padded out to a byte
	# boundary, which frombytes() undoes given the same width.
	node.text = base64.b64encode(zlib.compress(mask.tobytes(), 9)).decode("ascii")
	return node


def isLegacyMaskNode(element):
	return ((element.get("mode") != gfx.MASK_MODE) or
			(element.get("encoding") != MASK_ENCODING))

class Grid(object):
	GRID_NONE = "None"
	GRID_SQUARE = "Square"
	GRID_HEX = "Hex"
	
	def __init__(self, updateCallback=None):
		self.__type = Grid.GRID_NONE
		self.__size = 8
		self.__visible = False
		self.__updateCallback = updateCallback
		
	def setUpdateCallback(self, callback):
		self.__updateCallback = callback
		
	def copy(self):
		newGrid = Grid(self.__updateCallback)
		newGrid.__type = self.__type
		newGrid.__size = self.__size
		newGrid.__visible = self.__visible
		return newGrid
		
	def setType(self, type):
		self.__type = type
		self.callUpdateCallback()
		
	def setSize(self, size):
		self.__size = size
		self.callUpdateCallback()
		
	def setVisible(self, visible):
		self.__visible = visible
		self.callUpdateCallback()
		
	def toXml(self):
		return etree.Element("grid", type=self.type, size=str(self.size), visible=str(self.visible).lower())
	
	def fromXml(self, xml):
		self.type = xml.get("type")
		self.size = int(xml.get("size"))
		self.visible = xml.get("visible") == "true"
		
	def callUpdateCallback(self):
		if (self.__updateCallback != None):
			self.__updateCallback()
		
	type = property(lambda x: x.__type, setType)
	size = property(lambda x: x.__size, setSize)
	visible = property(lambda x: x.__visible, setVisible)
			

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
		self.__contentChanged()

	def unapplyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, gfx.MASK_HIDDEN)
		self.__contentChanged()

	def __contentChanged(self):
		self.contentDirty = True
		self.__fireUpdateListeners()

	def addUpdateListener(self, listener):
		self.updateListeners.append(listener)

	def removeUpdateListener(self, listener):
		self.updateListeners.remove(listener)

	def __fireUpdateListeners(self):
		for listener in self.updateListeners:
			listener()

	size = property(lambda x: x.mapImg.size)
