from PIL import Image
from lxml import etree

from ... import gfx

from .grid import Grid
from .imagepath import relativeImagePath, resolveImagePath
from .mask import isLegacyMaskNode, readMaskNode, writeMaskNode
from .secretlayer import SecretLayer


class Map(object):
	def __init__(self, mapImg, mapImgPath, mask, editable=True):
		self.mapImg = mapImg
		self.mapImgPath = mapImgPath
		# One bit per pixel; the alpha the two windows draw with is derived
		# from it.  See gfx.playerAlpha / gfx.gmAlpha.
		self.mask = Map.conformMask(mask, mapImg)

		# The secrets over this map, if it has any: another image the same size
		# and a mask of its own, deciding what colour a pixel is where the fog
		# mask has already decided it is on screen at all.  Empty for the great
		# majority of maps, and the whole feature costs those nothing.
		self.__secretLayers = []
		# Bumped whenever something changes what colour the map is, as against
		# what is hidden behind fog.  The panels hold the map composited with
		# its secret layers, and putting all of one back together costs the
		# whole map - while dragging the grid-size slider fires a change for
		# every tick of it and touches no pixel's colour at all.
		self.pixelVersion = 0

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
	def conformMask(mask, mapImg):
		"""The mask, stretched to the image it fogs if it does not already fit.

		   Everything downstream assumes one mask pixel per image pixel: the
		   panels hand the derived alpha straight to wx, which rejects a buffer
		   of the wrong length outright.  A mask arrives the wrong size when the
		   image behind it is swapped for one at another resolution, and in map
		   files whose image has been replaced on disk since they were saved.

		   Nearest neighbour, because a mask pixel is either revealed or hidden
		   and anything in between is not a value it can hold."""
		if ((mask is None) or (mapImg is None) or (mask.size == mapImg.size)):
			return mask
		return mask.resize(mapImg.size, Image.NEAREST)

	@staticmethod
	def read(root, baseDir=None):
		mapImg = None
		imgPath = None
		mask = None
		legacy = False
		grid = Grid()
		layers = []
		for element in root:
			if (element.tag == "imagePath"):
				imgPath = element.text
				mapImg = Image.open(resolveImagePath(imgPath, baseDir)).convert("RGBA")
			elif (element.tag == "grid"):
				grid.fromXml(element)
			elif (element.tag == "maskData"):
				mask = readMaskNode(element)
				legacy = legacy or isLegacyMaskNode(element)
			elif (element.tag == SecretLayer.TAG):
				layers.append(SecretLayer.fromXml(element, baseDir))
			elif (element.tag == "alphaMaskData"):
				# Derived from <maskData> and no longer kept; its presence is
				# itself enough to date the file.
				legacy = True

		# Held resolved, so the image can be found again whatever the working
		# directory is; write() turns it back into a relative path.
		map = Map(mapImg, resolveImagePath(imgPath, baseDir), mask)
		map.legacyFormat = legacy
		map.setGrid(grid)
		map.setSecretLayers(layers)
		return map

	def replaceImage(self, path):
		self.mapImg = Image.open(path).convert("RGBA")
		self.mapImgPath = path
		# An image of another size leaves the fog the wrong shape for the map it
		# now covers; what has been explored keeps its place on the new image.
		self.mask = Map.conformMask(self.mask, self.mapImg)
		# And the secrets with it, for the same reason and by the same rule.
		self.conformSecretLayers()
		self.__pixelsChanged()

	def write(self, root, baseDir=None):
		"""baseDir is the folder the image path is written relative to - the
		   folder the map file belongs in."""
		pathNode = etree.Element("imagePath")
		pathNode.text = relativeImagePath(self.mapImgPath, baseDir)
		root.append(pathNode)

		gridNode = self.grid.toXml()
		root.append(gridNode)

		# Ahead of the fog mask on purpose: the sidebar reads a map's image
		# paths out of the head of the file, and everything past this point is
		# base64 by the megabyte.  See project.readImagePaths.
		for layer in self.__secretLayers:
			root.append(layer.toXml(baseDir))

		root.append(writeMaskNode("maskData", self.mask))

		return root

	def applyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, gfx.MASK_REVEALED)
		self.__contentChanged(brush.bounds(x, y))

	def unapplyBrush(self, brush, x, y):
		brush.drawToImage(self.mask, x, y, gfx.MASK_HIDDEN)
		self.__contentChanged(brush.bounds(x, y))

	# --- secrets --------------------------------------------------------------
	# The UI offers one layer.  A map file holds a list of them, and everything
	# below works on the list, because which of those two is cheap to change
	# later is not the same one.

	def setSecretLayers(self, layers):
		"""The layers of secrets over this map, innermost first.

		   Quiet, like setGrid: this is how a map file's layers are put on a
		   map that is being read, which is nothing to mark as unsaved."""
		self.__secretLayers = list(layers)
		self.conformSecretLayers()
	secretLayers = property(lambda x: x.__secretLayers, setSecretLayers)

	secretLayer = property(lambda x: x.__secretLayers[0] if (x.__secretLayers) else None)
	hasSecrets = property(lambda x: bool(x.__secretLayers))

	def __imagePaths(self):
		"""Every image this map is drawn from: its own, and its layers'.

		   Held resolved, so they can be handed straight to anything that has
		   to find the files - the sidebar above all, which nests them under
		   the map and cannot read them out of the map file until it has been
		   saved."""
		paths = [self.mapImgPath] + [layer.path for layer in self.__secretLayers]
		return [path for path in paths if (path is not None)]
	imagePaths = property(__imagePaths)

	def conformSecretLayers(self):
		if (self.mapImg is not None):
			for layer in self.__secretLayers:
				layer.conform(self.mapImg.size)

	def setSecretImage(self, path):
		"""Put an image of the secrets over this map, in place of whatever was
		   there before.

		   What has already been revealed is kept when the new image is the
		   same size as the old: swapping one draft of the secrets for the next
		   should not undo an evening's painting.  A size that does not match
		   the map is refused rather than stretched - unlike a layer already on
		   a map, which has to cope with whatever it finds, this is the GM
		   picking a file and able to pick another."""
		layer = SecretLayer.forImage(path)
		if (layer.size != self.mapImg.size):
			raise ValueError(
				"That image is %d x %d and the map is %d x %d.  A secret layer "
				"has to be the same size as the map it covers."
				% (layer.size + self.mapImg.size))
		current = self.secretLayer
		if (current is not None):
			layer.mask = current.mask
		self.__secretLayers = [layer] + self.__secretLayers[1:]
		self.__pixelsChanged()

	def removeSecretImage(self):
		if (not self.__secretLayers):
			return
		self.__secretLayers = self.__secretLayers[1:]
		self.__pixelsChanged()

	def applySecretBrush(self, brush, x, y):
		self.__paintSecret(brush, x, y, gfx.MASK_REVEALED)

	def unapplySecretBrush(self, brush, x, y):
		self.__paintSecret(brush, x, y, gfx.MASK_HIDDEN)

	def __paintSecret(self, brush, x, y, value):
		layer = self.secretLayer
		if (layer is None):
			return
		brush.drawToImage(layer.mask, x, y, value)
		self.__pixelsChanged(brush.bounds(x, y))

	def fillSecrets(self, revealed):
		"""Reveal, or re-hide, every secret on the map at one go."""
		layer = self.secretLayer
		if (layer is None):
			return
		layer.fill(revealed)
		self.__pixelsChanged()

	# --- change notification --------------------------------------------------

	def __pixelsChanged(self, rect=None):
		"""A change to what colour the map is, rather than to what is hidden
		   behind fog.  Counted apart from the rest so that the panels can tell
		   the two sorts of change from one another - see pixelVersion."""
		self.pixelVersion += 1
		self.__contentChanged(rect)

	def __contentChanged(self, rect=None):
		self.contentDirty = True
		self.__fireUpdateListeners(rect)

	def addUpdateListener(self, listener):
		self.updateListeners.append(listener)

	def removeUpdateListener(self, listener):
		# Quietly ignores one that is not registered: removal happens on the
		# teardown paths, where raising would leave the thing being torn down
		# half attached and the next attempt in the same state.
		if (listener in self.updateListeners):
			self.updateListeners.remove(listener)

	def __fireUpdateListeners(self, rect=None):
		"""rect is the box a brush dab touched, or None when the change was
		   wholesale - a new grid, a swapped image - and everything has to be
		   rebuilt."""
		for listener in self.updateListeners:
			listener(rect)

	size = property(lambda x: x.mapImg.size)
