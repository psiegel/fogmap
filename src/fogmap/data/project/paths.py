"""Which files in a project folder are maps, and which are images."""
import os


MAP_EXTS = (".map", ".xml")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp")


def isMapPath(path):
	return os.path.splitext(path)[1].lower() in MAP_EXTS


def isImagePath(path):
	return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def isProjectFile(path):
	return isMapPath(path) or isImagePath(path)
