"""Reading and writing the one-bit fog mask a map file carries."""
import base64
import zlib

from PIL import Image
from lxml import etree

from ... import gfx


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
