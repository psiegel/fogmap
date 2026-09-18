"""A layer of secrets over a map: a second image, and the mask saying how much
   of it has been let through."""
import numpy as np
from PIL import Image
from lxml import etree

from ... import gfx

from .imagepath import relativeImagePath, resolveImagePath
from .mask import readMaskNode, writeMaskNode


class SecretLayer(object):
	"""The same rooms with the secret doors drawn in, over the map that has
	   them shut.

	   The mask is one bit per pixel like the fog's, and set where the layer
	   shows through - so it starts empty, the left button reveals and the
	   right button re-hides, exactly as the fog brush does.  Nothing here
	   touches the fog: that decides whether a pixel is on screen at all, and
	   this decides which of the two images it comes from."""

	# The element a map file stores one of these in.  Written before the fog
	# mask so that the sidebar can read a layer's path without wading through
	# the base64 that is most of a map file's weight.
	TAG = "secretLayer"

	def __init__(self, img, path, mask=None):
		self.img = img
		self.path = path
		self.mask = mask if (mask is not None) else \
					gfx.createMask(img.size[0], img.size[1], False)
		self.__measure()

	def __measure(self):
		"""What this layer can possibly change, and by how much.

		   A layer drawn as the secrets alone over transparency says so in its
		   own alpha channel: outside the box that channel covers there is
		   nothing to show whatever the mask says, so compositing skips those
		   bands outright.  A layer that is a full second copy of the map is
		   opaque, covers all of it, and has nothing to skip - which is why the
		   transparent form is the cheaper one to work with."""
		alpha = self.img.getchannel("A")
		if (alpha.getextrema()[0] == 255):
			self.coverage = None
			self.bounds = (0, 0) + self.img.size
		else:
			self.coverage = alpha
			self.bounds = alpha.getbbox() or (0, 0, 0, 0)

	def touches(self, box):
		"""Whether any of this layer falls inside (x0, y0, x1, y1)."""
		return ((box[0] < self.bounds[2]) and (box[2] > self.bounds[0]) and
				(box[1] < self.bounds[3]) and (box[3] > self.bounds[1]))

	def weight(self, box, ghost):
		"""How much of this layer shows through each pixel of box, 0 to 256 -
		   or None when none of it does anywhere, and there is nothing for the
		   caller to composite at all.

		   ghost is how much of the layer shows where it has *not* been painted
		   in, which is how the GM sees a secret before finding it.  The
		   players pass 0 and see none of one."""
		revealed = gfx.maskBytes(self.mask, box)
		unrevealed = int(round(min(max(ghost, 0.0), 1.0) * 256))
		if ((unrevealed == 0) and (not revealed.any())):
			return None
		weight = np.where(revealed > 0, 256, unrevealed).astype(np.int32)
		if (self.coverage is None):
			return weight
		# Scaled by the layer's own alpha, so secrets drawn over transparency
		# show where they were drawn and nowhere else.  255 * 256 // 255 is
		# 256 exactly, so a solid pixel still lands fully on the secret.
		cover = np.asarray(self.coverage.crop(box), np.uint8).astype(np.int32)
		return (cover * weight) // 255

	def conform(self, size):
		"""Stretch to the map this covers, if it does not already fit.

		   Everything downstream assumes one layer pixel per map pixel.  A
		   layer falls out of step when the image under it is swapped for one
		   at another resolution, and when it is re-exported at another size
		   between sessions; what has been revealed of it keeps its place
		   either way, exactly as the fog does.  The mask goes nearest
		   neighbour, because a mask pixel is revealed or it is not and there
		   is nothing in between for it to hold."""
		if (self.img.size != size):
			self.img = self.img.resize(size, Image.BICUBIC)
			self.__measure()
		if (self.mask.size != size):
			self.mask = self.mask.resize(size, Image.NEAREST)

	def fill(self, revealed):
		"""Reveal or re-hide the whole layer at one go."""
		self.mask = gfx.createMask(self.mask.size[0], self.mask.size[1], revealed)

	def toXml(self, baseDir=None):
		node = etree.Element(SecretLayer.TAG)
		path = relativeImagePath(self.path, baseDir)
		if (path is not None):
			node.set("path", path)
		node.append(writeMaskNode("maskData", self.mask))
		return node

	@staticmethod
	def fromXml(element, baseDir=None):
		layer = SecretLayer.forImage(
			resolveImagePath(element.get("path"), baseDir))
		for child in element:
			if (child.tag == "maskData"):
				layer.mask = readMaskNode(child)
		return layer

	@staticmethod
	def forImage(path):
		return SecretLayer(Image.open(path).convert("RGBA"), path)

	size = property(lambda x: x.img.size)
