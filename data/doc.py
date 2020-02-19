from PIL import Image
import base64
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
	def __init__(self, mapImg, mapImgPath, mask, alphaMask):
		self.mapImg = mapImg
		self.mapImgPath = mapImgPath
		self.mask = mask
		self.alphaMask = alphaMask

		self.__grid = Grid(self.__fireUpdateListeners)

		self.updateListeners = []
		
	def setGrid(self, grid):
		self.__grid = grid
		self.__grid.setUpdateCallback(self.__fireUpdateListeners)
	grid = property(lambda x: x.__grid, setGrid)

	@staticmethod
	def createNew(imgPath):
		mapImg = Image.open(imgPath).convert("RGBA")
		mask = gfx.createMask(mapImg.size[0], mapImg.size[1], 0)
		alphaMask = gfx.createMask(mapImg.size[0], mapImg.size[1], 128)        
		return Map(mapImg, imgPath, mask, alphaMask)

	@staticmethod
	def read(root):
		mapImg = None
		imgPath = None
		mask = None
		alphaMask = None
		grid = Grid()
		for element in root:
			if (element.tag == "imagePath"):
				imgPath = element.text
				mapImg = Image.open(imgPath).convert("RGBA")
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

		map = Map(mapImg, imgPath, mask, alphaMask)     
		map.setGrid(grid)
		return map

	def replaceImage(self, path):
		self.mapImg = Image.open(path).convert("RGBA")
		self.mapImgPath = path
		self.__fireUpdateListeners()

	def write(self, root):
		pathNode = etree.Element("imagePath")
		pathNode.text = self.mapImgPath
		root.append(pathNode)

		gridNode = self.grid.toXml()
		root.append(gridNode)

		maskData = etree.Element("maskData", mode=self.mask.mode, width=str(self.mask.size[0]), height=str(self.mask.size[1]))
		maskData.text = base64.b64encode(self.mask.tobytes())
		root.append(maskData)

		alphaData = etree.Element("alphaMaskData", mode=self.alphaMask.mode, width=str(self.alphaMask.size[0]), height=str(self.alphaMask.size[1]))
		alphaData.text = base64.b64encode(self.alphaMask.tobytes())
		root.append(alphaData)
		
		return root

	def applyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, 255)
		brush.drawToImage(self.alphaMask, x, y, 255)
		self.__fireUpdateListeners()
		
	def unapplyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, 0)
		brush.drawToImage(self.alphaMask, x, y, 128)
		self.__fireUpdateListeners()

	def addUpdateListener(self, listener):
		self.updateListeners.append(listener)

	def removeUpdateListener(self, listener):
		self.updateListeners.remove(listener)

	def __fireUpdateListeners(self):
		for listener in self.updateListeners:
			listener()

	size = property(lambda x: x.mapImg.size)
