"""The app's own image files, found wherever fogmap happens to be installed."""
import os

import wx

_DIR = os.path.dirname(os.path.abspath(__file__))

# Largest last: wx picks the best match out of a bundle, and a .ico carries its
# own set of sizes, so listing both leaves it a small icon for the title bar and
# a big one for the Dock.
_ICON_FILES = ("fogmap.ico", "fogmap.png")


def appIcons():
	"""The app icon at every size it was supplied in, or None if there is none.

	   Missing files are not an error: the icon is decoration, and a build
	   without one should still put its windows on the screen."""
	bundle = wx.IconBundle()
	for name in _ICON_FILES:
		path = os.path.join(_DIR, name)
		if (os.path.exists(path)):
			try:
				bundle.AddIcon(path)
			except Exception:
				# A corrupt or unreadable icon is not worth failing startup over.
				pass
	return bundle if (bundle.GetIconCount() > 0) else None


def largestIcon(icons=None):
	"""The biggest icon available, for the macOS Dock tile.

	   IconBundle.GetIcon falls back to the system icon size when the bundle
	   holds nothing of the size asked for, and returns an invalid icon when
	   that is missing too - which is what a single large .png gives you.  So
	   the choice is made here rather than left to a size request."""
	if (icons is None):
		icons = appIcons()
	if (icons is None):
		return None
	best = None
	for i in range(icons.GetIconCount()):
		icon = icons.GetIconByIndex(i)
		if (icon.IsOk() and ((best is None) or (icon.GetWidth() > best.GetWidth()))):
			best = icon
	return best


def path(name):
	"""The full path to a file in the resource folder, whether or not it exists."""
	return os.path.join(_DIR, name)


# --- toolbar icons ------------------------------------------------------------
# Line art rather than pictures: one SVG per icon, rasterised at load into a
# wx.BitmapBundle so that wx can ask for it again at 2x on a Retina screen
# instead of scaling a fixed-size PNG up.  See icons/README.md.

_ICON_DIR = os.path.join(_DIR, "icons")

# What every icon file is drawn in, and what gets swapped for the system's own
# text colour on the way through.  A literal rather than `currentColor`, which
# the SVG parser behind wx.BitmapBundle does not understand.
_ICON_INK = b"#111111"

# The size the toolbar asks for.  The bundle is resolution-independent, so this
# is a size in points rather than a count of pixels.
ICON_SIZE = 18

# Rasterised icons, keyed by name, size and ink: small, and rebuilt only when
# the GM switches their Mac between light and dark.
_iconCache = {}

# Everywhere an icon has been put, as (window, setter, name, size).  A
# light/dark switch has to repaint every one of them, and a bundle cannot carry
# both appearances, so the places are remembered rather than the bitmaps.
_iconTargets = []


def _inkColour():
	"""What to draw an icon in, so that it reads against whatever the toolbar
	   is painted in.  Alpha is dropped: it belongs to the text the colour was
	   meant for, and a half-faded icon just looks disabled."""
	colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
	return "#%02x%02x%02x" % (colour.Red(), colour.Green(), colour.Blue())


def icon(name, size=None):
	"""One of the toolbar icons, as a wx.BitmapBundle inked for the current
	   appearance.

	   A missing or unreadable file gives back an empty bundle rather than
	   raising: an icon is decoration, and a bad build should still put its
	   toolbar on the screen, just a blank one."""
	size = ICON_SIZE if (size is None) else size
	key = (name, size, _inkColour())
	bundle = _iconCache.get(key)
	if (bundle is None):
		try:
			with open(os.path.join(_ICON_DIR, name + ".svg"), "rb") as handle:
				svg = handle.read()
			svg = svg.replace(_ICON_INK, key[2].encode("ascii"))
			bundle = wx.BitmapBundle.FromSVG(svg, wx.Size(size, size))
		except Exception:
			bundle = wx.BitmapBundle()
		_iconCache[key] = bundle
	return bundle


def trackIcon(window, setter, name, size=None):
	"""Remember that `setter` is what puts `name` on `window`, so that a
	   light/dark switch can put it there again in the other ink.

	   The window is kept only to tell whether the icon is still on screen:
	   entries for windows that have since been destroyed are dropped the next
	   time round rather than unregistered by hand."""
	_iconTargets.append((window, setter, name, size))


def refreshIcons():
	"""Re-ink every tracked icon, after the appearance has changed.

	   Called from a wx.EVT_SYS_COLOUR_CHANGED handler.  macOS switches itself
	   between light and dark at sunset, so this is not only about the GM
	   flipping the setting by hand mid-session."""
	_iconCache.clear()
	live = []
	for entry in _iconTargets:
		window, setter, name, size = entry
		# A destroyed window leaves a Python wrapper around nothing, and
		# touching it raises rather than returning False.
		try:
			if (not window):
				continue
		except RuntimeError:
			continue
		try:
			setter(icon(name, size))
		except RuntimeError:
			continue
		live.append(entry)
	_iconTargets[:] = live
