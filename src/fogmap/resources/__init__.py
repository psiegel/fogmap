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
