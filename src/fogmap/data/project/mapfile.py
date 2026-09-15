"""Reading and writing map files, including the older layouts.

   Kept apart from Map itself because most of what a project does with a map
   file never needs the image: the sidebar wants only its <imagePath>, and
   converting old fog is XML surgery."""
import copy
import os

from lxml import etree

from ..doc import Map, isLegacyMaskNode, readMaskNode, writeMaskNode


def readImagePath(path):
	"""The <imagePath> of a map file, without parsing the rest of it.

	   Map files run to tens of megabytes of base64 mask data and the sidebar
	   needs this for every map in the project.  Map.write puts the path node
	   ahead of the grid and the masks, so stopping at the first match reads
	   only the head of the file.  The tag filter finds it in the legacy
	   bare-<map> layout too."""
	try:
		for event, element in etree.iterparse(path, tag="imagePath", events=("end",)):
			text = element.text
			return text.strip() if (text is not None) else None
	except (etree.XMLSyntaxError, OSError):
		return None
	return None


def isLegacyMapFile(path):
	"""True if a map file still holds fog in the old byte-per-pixel format.

	   Asked of every map in a project the moment it is opened, so it reads
	   only the head of the file: <maskData> carries the format in its
	   attributes, and taking the start event rather than the end one means
	   its base64 payload is never pulled in.  An <alphaMaskData> at all dates
	   the file on its own."""
	try:
		for event, element in etree.iterparse(path,
											  tag=("maskData", "alphaMaskData"),
											  events=("start",)):
			if (element.tag == "alphaMaskData"):
				return True
			return isLegacyMaskNode(element)
	except (etree.XMLSyntaxError, OSError):
		# Not something we can read, so not something we can convert either.
		return False
	return False


def upgradeMapFile(path):
	"""Rewrite a map file's fog in the current format, in place.

	   Deliberately works on the XML rather than going through Map: converting
	   the fog has nothing to do with the image, and a project-wide Save All
	   should not have to decode every map image - nor fail on a map whose
	   image has since been moved."""
	root = etree.parse(path).getroot()
	if (root.tag == "map"):
		# Legacy bare root; give it the wrapper everything else expects.
		mapNode = root
		root = etree.Element("fogmap")
		root.append(mapNode)
	else:
		mapNode = root.find("map")
	if (mapNode is None):
		return False

	masks = mapNode.findall("maskData")
	if (not masks):
		return False
	for node in mapNode.findall("alphaMaskData"):
		mapNode.remove(node)
	for node in masks:
		mapNode.replace(node, writeMaskNode("maskData", readMaskNode(node)))

	with open(path, mode="wb") as f:
		f.write(etree.tostring(root, pretty_print=True))
	return True


def readMapFile(path, baseDir=None):
	"""Parse a map file into (Map, settings), handling both the <fogmap>
	   wrapper and the legacy bare <map> root.

	   baseDir is the folder a relative <imagePath> is read against.  It is
	   passed separately because a map restored from .fogmap/ has to resolve
	   against where the real file lives, not where the copy does.

	   The settings are copied out of the parsed tree so the tree itself - which
	   holds the whole base64 mask payload - can be released straight away."""
	if (baseDir is None):
		baseDir = os.path.dirname(os.path.abspath(path))
	root = etree.parse(path).getroot()
	if (root.tag == "map"):
		return Map.read(root, baseDir), None

	map = None
	settings = None
	for child in root:
		if (child.tag == "map"):
			map = Map.read(child, baseDir)
		elif (child.tag == "settings"):
			settings = copy.deepcopy(child)
	return map, settings


def writeMapFile(path, map, settings, baseDir=None):
	"""baseDir is the folder <imagePath> is written relative to.  It is separate
	   from path because a temp copy under .fogmap/ has to record the image the
	   way the real map file would, not the way the copy happens to sit."""
	if (baseDir is None):
		baseDir = os.path.dirname(os.path.abspath(path))

	root = etree.Element("fogmap")

	mapNode = etree.Element("map")
	map.write(mapNode, baseDir)
	root.append(mapNode)

	if (settings is not None):
		root.append(copy.deepcopy(settings))

	with open(path, mode="wb") as f:
		f.write(etree.tostring(root, pretty_print=True))


def spliceSettings(path, settings):
	"""Replace just the <settings> of an existing map file.

	   Used to commit a map whose only unsaved change is where the player view
	   is pointing: the mask data is passed through untouched rather than being
	   re-encoded, which is what keeps browsing a project cheap."""
	root = etree.parse(path).getroot()
	if (root.tag == "map"):
		# Legacy file with no wrapper; promote it so it has somewhere to go.
		mapNode = root
		root = etree.Element("fogmap")
		root.append(mapNode)
	else:
		for child in root.findall("settings"):
			root.remove(child)

	if (settings is not None):
		root.append(copy.deepcopy(settings))

	with open(path, mode="wb") as f:
		f.write(etree.tostring(root, pretty_print=True))
