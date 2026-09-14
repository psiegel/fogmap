from PIL import Image, ImageDraw
import numpy as np
import wx

# The fog mask is one bit per pixel: set where the map shows through, clear
# where it is hidden.  What the two windows actually need is a byte of alpha
# per pixel, but those are both functions of that single bit and are derived
# on the way to the screen rather than stored.
#
# PIL holds a "1" image at a byte per pixel and only packs it down in
# tobytes(), so the mode buys nothing in memory over "L" - the saving is in
# carrying one mask instead of two, and in what goes to disk.
MASK_MODE = "1"

# PIL will store whatever value it is handed in a "1" image, so a mask painted
# with 1 rather than 255 comes back out as alpha 1: invisible instead of
# opaque.  Everything that paints a mask goes through these.
MASK_REVEALED = 255
MASK_HIDDEN = 0

def pilToWx(pil, alpha=True):
	image = wx.Image(pil.size[0], pil.size[1])
	image.SetData(pil.convert("RGB").tobytes())
	if alpha:
		image.SetAlpha(pil.convert("RGBA").tobytes()[3::4])
	return image

def wxToPil(image):
	return Image.frombytes("RGB",
						   (image.GetWidth(), image.GetHeight()),
						   bytes(image.GetData()))

def createNewImg(w, h, color, alpha=False):
	if (alpha):
		im = Image.new("RGBA", (w, h))
		draw = ImageDraw.Draw(im)
		draw.rectangle([(0, 0), (w, h)], fill=color)
		del draw
	else:
		im = Image.new("RGB", (w, h))
		draw = ImageDraw.Draw(im)
		draw.rectangle([(0, 0), (w, h)], fill=color)
		del draw
	return im

def createMask(w, h, revealed):
	return Image.new(MASK_MODE, (w, h), MASK_REVEALED if revealed else MASK_HIDDEN)

def maskBytes(mask, box=None):
	"""The mask as a 2-D array of bytes, 0 or 255.

	   box limits it to (x0, y0, x1, y1), far edge exclusive - which is how a
	   brush dab avoids touching anything but the handful of pixels it
	   actually changed."""
	# Cropping first, rather than slicing after, is the whole point: PIL hands
	# numpy a copy of the image rather than a view of it, so asking for the
	# whole mask and taking a corner of it would copy every pixel of the map
	# for the sake of a brush-sized box.  It also means the result can never
	# be a stale view of a mask that has since been painted on.
	if (box is not None):
		mask = mask.crop(box)
	return np.asarray(mask).view(np.uint8)

def playerAlpha(mask, box=None):
	"""Player alpha: hidden ground is fully transparent, so the black behind
	   the map comes through."""
	return maskBytes(mask, box)

def gmAlpha(mask, box=None):
	"""GM alpha: hidden ground is dimmed rather than removed, so the GM can
	   still see what they are about to reveal.  255 -> 255, 0 -> 128."""
	return (maskBytes(mask, box) >> 1) | np.uint8(128)
