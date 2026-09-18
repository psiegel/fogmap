"""Where a map's images actually live.

   A path is stored relative to the map file, so a project folder can be copied
   or moved between machines as a unit and its maps still find their images.
   Shared by the map's own image and by the secret layers over it, which are
   stored and resolved in exactly the same way."""
import os


def resolveImagePath(imgPath, baseDir):
	"""Where the image actually is.

	   The path is stored relative to the map file, so it is read against the
	   folder that file lives in.  Absolute paths, which is what older map
	   files hold, are used as they stand."""
	if ((imgPath is not None) and (baseDir is not None) and
		(not os.path.isabs(imgPath))):
		return os.path.normpath(os.path.join(baseDir, imgPath))
	return imgPath


def relativeImagePath(imgPath, baseDir):
	"""How the path is written back: relative to the map file, so a project
	   folder keeps working when it is copied or moved somewhere else."""
	if ((imgPath is None) or (baseDir is None)):
		return imgPath
	try:
		return os.path.relpath(imgPath, baseDir)
	except ValueError:
		# No common root to be relative to, so there is nothing to shorten.
		return imgPath
