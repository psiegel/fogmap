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


# --- secret layers ------------------------------------------------------------
# A map can carry a second image over its own - the same rooms with the secret
# doors drawn in - and one mask per layer saying how much of it has been let
# through.  The fog mask decides what a pixel's alpha is; these decide what
# colour it is, and the two never have to agree about anything.

# The wash the GM sees over ground where a secret has been painted in.  It is
# the only thing on screen that says a dab landed at all: the two images are
# identical everywhere except at the secrets themselves, so over almost all of
# a map revealing one changes nothing that can be seen.
SECRET_TINT = (168, 72, 220)
SECRET_TINT_WEIGHT = 46		# out of 256, so a little under a fifth

# The same wash while peeking.  With the whole layer shown at full strength
# there, the tint is the only thing left saying which of it the players have
# actually found - so it is heavier, and dark enough to read as shade rather
# than as colour.  A violet at the ordinary brightness does not: washed over
# saturated red it comes out purpler but no darker at all, because what it
# takes off the red it puts back as blue.  This one loses about a fifth of
# the brightness of red, over a third of parchment, and still takes a little
# off ink, which is as near to "shaded everywhere" as one colour gets.
SECRET_PEEK_TINT = (52, 10, 84)
SECRET_PEEK_TINT_WEIGHT = 110

# How much of an unrevealed secret the GM sees ghosted through the map over it.
# The players are always shown none of one.
GHOST_OFF = 0.0
GHOST_HALF = 0.5
GHOST_FULL = 1.0

# Compositing runs a band of rows at a time.  A lerp's intermediate product
# needs 32 bits a channel, and a whole large map's worth of those runs to
# hundreds of megabytes; a band is bounded and no slower.
_BAND_ROWS = 256


def rgbBytes(rgb):
	"""A composite packed the way wx.Image.SetData wants it.  The slicing that
	   drops the alpha channel leaves a view rather than a block of memory, so
	   this is not the no-op it looks."""
	return np.ascontiguousarray(rgb).tobytes()


def baseRgb(img, box=None):
	"""The colour channels of an image, as an (h, w, 3) array of bytes."""
	return np.asarray(img.crop(box) if (box is not None) else img)[:, :, :3]


def playerRgb(mapImg, layers, box=None):
	"""What the players see: a secret shows only once it has been painted in,
	   and until then the map looks exactly as it would with no layer at all."""
	return composite(mapImg, layers, box)


def gmRgb(mapImg, layers, box=None, ghost=GHOST_OFF, tint=True, peeking=False):
	"""What the GM sees: unrevealed secrets ghosted through at `ghost`, and a
	   wash over whatever has been revealed so that painting one is visible
	   even where the two images are identical.

	   Peeking overrides both and shows the layer entire, found and unfound
	   alike, with the found parts washed harder so the two can still be told
	   apart.  It is a look at the map rather than a setting on it: nothing it
	   does reaches the players, any mask, or any file."""
	if (peeking):
		return composite(mapImg, layers, box, GHOST_FULL,
						 SECRET_PEEK_TINT, SECRET_PEEK_TINT_WEIGHT)
	return composite(mapImg, layers, box, ghost,
					 SECRET_TINT if (tint) else None, SECRET_TINT_WEIGHT)


def composite(mapImg, layers, box=None, ghost=GHOST_OFF, tint=None,
			  tintWeight=SECRET_TINT_WEIGHT):
	"""The map with its secret layers over it, as an (h, w, 3) array of bytes.

	   box limits it to (x0, y0, x1, y1), far edge exclusive, which is how a
	   brush dab composites the handful of pixels it touched rather than the
	   whole map.  With no layers this is the map's own pixels and nothing is
	   computed at all - which is the case every map without secrets is in."""
	if (not layers):
		return baseRgb(mapImg, box)
	x0, y0, x1, y1 = box if (box is not None) else (0, 0) + mapImg.size
	out = np.empty((y1 - y0, x1 - x0, 3), np.uint8)
	for top in range(y0, y1, _BAND_ROWS):
		bottom = min(top + _BAND_ROWS, y1)
		out[(top - y0):(bottom - y0)] = _compositeBand(
			mapImg, layers, (x0, top, x1, bottom), ghost, tint, tintWeight)
	return out


def _compositeBand(mapImg, layers, box, ghost, tint, tintWeight):
	active = [layer for layer in layers if layer.touches(box)]
	if (not active):
		# No layer reaches this band, so the map's own pixels are the answer
		# and there is nothing to lerp them onto.  This is what makes a layer
		# drawn as the secrets alone cost only the ground it actually covers,
		# and it bounds the tint to there as well - which is right, since
		# painting where the layer holds nothing reveals nothing.
		return baseRgb(mapImg, box)
	rgb = baseRgb(mapImg, box).astype(np.int16)
	revealed = None
	for layer in active:
		weight = layer.weight(box, ghost)
		if (weight is not None):
			_lerp(rgb, baseRgb(layer.img, box).astype(np.int16), weight)
		if (tint is not None):
			# Outside the guard above on purpose: the tint follows the mask
			# rather than what the layer has to show, because saying where the
			# brush has been is the whole of its job.
			shown = maskBytes(layer.mask, box) > 0
			revealed = shown if (revealed is None) else (revealed | shown)
	if ((revealed is not None) and revealed.any()):
		_lerp(rgb, np.asarray(tint, np.int16),
			  np.where(revealed, tintWeight, 0).astype(np.int32))
	return rgb.astype(np.uint8)


def _lerp(rgb, target, weight):
	"""rgb += (target - rgb) * weight / 256, in place and in whole bytes.

	   weight is one value per pixel, 0 to 256 inclusive, so a weight of 256
	   lands exactly on the target and one of 0 changes nothing.  The product
	   is taken in 32 bits: a difference of 255 times a weight of 256 overruns
	   an int16 twice over.  Both ends being colours the result cannot leave
	   0-255, so there is no clamping to pay for."""
	diff = (target - rgb).astype(np.int32)
	diff *= weight[:, :, None]
	rgb += (diff >> 8).astype(np.int16)
