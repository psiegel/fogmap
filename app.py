#!/usr/bin/python
import optparse
import wx
from PIL import Image
from lxml import etree

import data
import ui	

class ImageTestApp(wx.App):
	def __init__(self, file):
		super(ImageTestApp, self).__init__(0)
		self.lastSavePath = None
		if (file is not None):
			self.loadMap(file)

	def OnInit(self):
		self.playerFrame = ui.PlayerFrame(None, -1, "Player View", size=(800, 600))
		self.playerFrame.Show(True)

		self.gmFrame = ui.GMFrame(None, -1, "GM View", size=(800, 600))
		self.gmFrame.Show(True)

		self.gmFrame.panel.setPlayerPanel(self.playerFrame.panel)

		return True	
	
	def newMap(self, path):
		map = data.Map.createNew(path)
		self.setMap(map)
		self.lastSavePath = None

	def loadMap(self, path):
		self.lastSavePath = path
		xml = etree.parse(path)
		root = xml.getroot()	

		if (root.tag == "map"):
			# Backwards compatibility
			self.setMap(data.Map.read(root))
		else:
			for child in root:
				if (child.tag == "map"):
					self.setMap(data.Map.read(child))
				elif (child.tag == "settings"):
					self.readSettings(child)

	def swapMapImage(self, path):
		self.map.replaceImage(path)
		self.setMap(self.map)


	def saveMap(self, path):
		self.lastSavePath = path
		root = etree.Element("fogmap")
		
		mapNode = etree.Element("map")
		self.map.write(mapNode)
		root.append(mapNode)
				
		settings = etree.Element("settings")
		self.writeSettings(settings)
		root.append(settings)
		
		file = open(path, mode="w")
		file.write(etree.tostring(root, pretty_print=True))
		file.close()

	def setMap(self, map):
		self.map = map
		if (self.playerFrame != None):
			self.playerFrame.setMap(self.map)
		if (self.gmFrame != None):
			self.gmFrame.setMap(self.map)
			
	def readSettings(self, settings):
		for child in settings:
			if ((child.tag == "player") and (self.playerFrame != None)):
				self.playerFrame.panel.readSettings(child)
			elif ((child.tag == "gm") and (self.gmFrame != None)):
				self.gmFrame.panel.readSettings(child)
	
	def writeSettings(self, settings):
		playerSettings = etree.Element("player")
		if (self.playerFrame != None):
			self.playerFrame.panel.writeSettings(playerSettings)
		settings.append(playerSettings)
		
		gmSettings = etree.Element("gm")
		if (self.gmFrame != None):
			self.gmFrame.panel.writeSettings(gmSettings)
		settings.append(gmSettings)


if __name__ == '__main__':
	usage = "usage: fogmap [options]"
	parser = optparse.OptionParser(version='%prog 1.0', usage=usage)
	parser.add_option('-f', '--file', dest='file', default=None, metavar='FILE', help='Map file to open')	
	options, args = parser.parse_args()

	app = ImageTestApp(options.file)
	app.MainLoop()
