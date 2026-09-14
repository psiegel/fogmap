from PIL import Image
import base64
import os
from lxml import etree

import gfx

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
	def __init__(self, mapImg, mapImgPath, mask, alphaMask, editable=True):
		self.mapImg = mapImg
		self.mapImgPath = mapImgPath
		self.mask = mask
		self.alphaMask = alphaMask

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
		mask = gfx.createMask(mapImg.size[0], mapImg.size[1], 0)
		alphaMask = gfx.createMask(mapImg.size[0], mapImg.size[1], 128)
		return Map(mapImg, imgPath, mask, alphaMask)

	@staticmethod
	def forImage(imgPath):
		"""A plain image, shown whole to the players with no fog at all.

		   Both masks are fully opaque, so the players see everything and the
		   GM sees it at full brightness rather than the usual half.  They are
		   the same object because neither can ever be painted on."""
		mapImg = Image.open(imgPath).convert("RGBA")
		mask = gfx.createMask(mapImg.size[0], mapImg.size[1], 255)
		return Map(mapImg, imgPath, mask, mask, editable=False)

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
		alphaMask = None
		grid = Grid()
		for element in root:
			if (element.tag == "imagePath"):
				imgPath = element.text
				mapImg = Image.open(Map.resolveImagePath(imgPath, baseDir)).convert("RGBA")
			elif (element.tag == "grid"):
				grid.fromXml(element)
			elif (element.tag == "maskData"):
				mode = element.get("mode")
				w = int(element.get("width"))
				h = int(element.get("height"))
				mask = Image.frombytes(mode, (w, h), base64.b64decode(element.text))
			elif (element.tag == "alphaMaskData"):
				mode = element.get("mode")
				w = int(element.get("width"))
				h = int(element.get("height"))
				alphaMask = Image.frombytes(mode, (w, h), base64.b64decode(element.text))

		# Held resolved, so the image can be found again whatever the working
		# directory is; write() turns it back into a relative path.
		map = Map(mapImg, Map.resolveImagePath(imgPath, baseDir), mask, alphaMask)
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

		maskData = etree.Element("maskData", mode=self.mask.mode, width=str(self.mask.size[0]), height=str(self.mask.size[1]))
		maskData.text = base64.b64encode(self.mask.tobytes()).decode("ascii")
		root.append(maskData)

		alphaData = etree.Element("alphaMaskData", mode=self.alphaMask.mode, width=str(self.alphaMask.size[0]), height=str(self.alphaMask.size[1]))
		alphaData.text = base64.b64encode(self.alphaMask.tobytes()).decode("ascii")
		root.append(alphaData)
		
		return root

	def applyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, 255)
		brush.drawToImage(self.alphaMask, x, y, 255)
		self.__contentChanged()

	def unapplyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, 0)
		brush.drawToImage(self.alphaMask, x, y, 128)
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
