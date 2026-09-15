from lxml import etree


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
