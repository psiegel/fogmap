"""Projects: a folder of maps and images the GM can click between.

Only the document being looked at is held in memory.  A map with unsaved
changes is flushed to a temp copy under <root>/.fogmap/ when the GM switches
away from it, in exactly the same format as a real map file, so bringing it
back is a plain parse and committing it is a plain file copy.

Because a clean exit always empties .fogmap/, anything found in there when a
project is opened is left over from a crash.
"""
import copy
import os
import shutil

from lxml import etree

from .doc import Map, readMaskNode, writeMaskNode, isLegacyMaskNode

TEMP_DIR_NAME = ".fogmap"

MAP_EXTS = (".map", ".xml")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp")


def isMapPath(path):
	return os.path.splitext(path)[1].lower() in MAP_EXTS

def isImagePath(path):
	return os.path.splitext(path)[1].lower() in IMAGE_EXTS

def isProjectFile(path):
	return isMapPath(path) or isImagePath(path)


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


class Node(object):
	"""One row of the sidebar tree."""

	def __init__(self, path, isDir, children=None):
		self.path = path
		self.isDir = isDir
		self.children = children if (children is not None) else []

	name = property(lambda x: os.path.basename(x.path))


class DirtyEntry(object):
	"""What is outstanding for one file.

	   hasTemp means the fog, grid or image changed and a full copy is sitting
	   in .fogmap/.  legacy means nothing was edited at all - the file is
	   simply still in the old mask format and wants rewriting in place.
	   Without either, only the player view moved and the settings held here
	   are the whole of the change."""

	def __init__(self, rel, hasTemp, settings, legacy=False):
		self.rel = rel
		self.hasTemp = hasTemp
		self.settings = settings
		self.legacy = legacy


class Project(object):
	def __init__(self, root):
		self.root = os.path.abspath(root)
		self.dirty = {}
		self.settings = {}

	name = property(lambda x: os.path.basename(x.root) or x.root)

	def relPath(self, path):
		return os.path.relpath(os.path.abspath(path), self.root)

	def contains(self, path):
		if (path is None):
			return False
		rel = self.relPath(path)
		return not (rel == os.pardir or rel.startswith(os.pardir + os.sep))

	def tempRoot(self):
		return os.path.join(self.root, TEMP_DIR_NAME)

	def tempPathFor(self, path):
		return os.path.join(self.tempRoot(), self.relPath(path))

	def hasTemp(self, path):
		entry = self.__entry(path)
		return (entry is not None) and entry.hasTemp

	def isDirty(self, path):
		return self.__entry(path) is not None

	def dirtyCount(self):
		return len(self.dirty)

	# --- remembering where the player view was left ---------------------------

	def remember(self, path, settings):
		"""Keep a file's player view position for the rest of the session, so
		   coming back to it lands where the GM left off.  Costs a few hundred
		   bytes, unlike keeping the document itself."""
		if (self.contains(path) and (settings is not None)):
			self.settings[self.__key(path)] = copy.deepcopy(settings)

	def rememberedSettings(self, path):
		return self.settings.get(self.__key(path))

	# --- dirty bookkeeping ----------------------------------------------------

	def writeTemp(self, path, map, settings):
		"""Flush a modified map to its temp copy and mark it outstanding."""
		temp = self.tempPathFor(path)
		os.makedirs(os.path.dirname(temp), exist_ok=True)
		writeMapFile(temp, map, settings, os.path.dirname(os.path.abspath(path)))
		self.__setEntry(path, True, settings)

	def markViewDirty(self, path, settings):
		"""Nothing but the player view moved, so no mask data needs writing."""
		entry = self.__entry(path)
		if ((entry is not None) and (entry.hasTemp or entry.legacy)):
			# Something already covers the mask data; keep it, but with the
			# new view.  Splicing settings alone would leave the old format in
			# place, which is the one thing a legacy entry exists to fix.
			entry.settings = copy.deepcopy(settings)
			return
		self.__setEntry(path, False, settings)

	def markLegacyMaps(self):
		"""Flag every map still in the old format as outstanding, so the next
		   Save All converts the whole project in one go.

		   Nothing is read beyond each file's head, and nothing is written
		   until the GM asks for it - but the maps do show up starred in the
		   tree, and they do count towards the unsaved-changes prompt.
		   Returns how many were found."""
		found = 0
		for folder, dirs, files in os.walk(self.root):
			# Skips .fogmap/ along with anything else hidden, matching scan().
			dirs[:] = [d for d in dirs if not d.startswith(".")]
			for name in files:
				if (name.startswith(".") or not isMapPath(name)):
					continue
				full = os.path.join(folder, name)
				if (self.isDirty(full)):
					# Already outstanding for a better reason, and whatever
					# gets written back will be in the current format anyway.
					continue
				if (isLegacyMapFile(full)):
					self.dirty[self.__key(full)] = DirtyEntry(self.relPath(full),
															  False, None, legacy=True)
					found += 1
		return found

	def takeOver(self, path):
		"""Hand a file's outstanding change to the document that has just opened
		   it.  The temp copy is deliberately left on disk - nothing else can
		   recover those changes if the app dies while the file is open."""
		self.dirty.pop(self.__key(path), None)

	def clearDirty(self, path):
		"""Forget any outstanding change and delete the temp copy.  Used once a
		   file has been written back for real."""
		if (not self.contains(path)):
			return
		self.dirty.pop(self.__key(path), None)
		self.__removeTemp(self.relPath(path))
		self.__pruneTempRoot()

	def commitAll(self):
		"""Write every outstanding change back over its original file."""
		for entry in list(self.dirty.values()):
			self.__commit(entry)
		self.dirty = {}
		self.__pruneTempRoot()

	def __commit(self, entry):
		original = os.path.join(self.root, entry.rel)
		if (entry.hasTemp):
			temp = self.tempPathFor(original)
			if (os.path.exists(temp)):
				shutil.copyfile(temp, original)
				self.__removeTemp(entry.rel)
		elif (not os.path.exists(original)):
			return
		elif (entry.legacy):
			upgradeMapFile(original)
			if (entry.settings is not None):
				spliceSettings(original, entry.settings)
		else:
			spliceSettings(original, entry.settings)

	# --- crash leftovers ------------------------------------------------------

	def findLeftoverTemps(self):
		"""Temp copies left behind by a crash, as relative paths.  Copies whose
		   original has since gone are dropped rather than reported."""
		tempRoot = self.tempRoot()
		if (not os.path.isdir(tempRoot)):
			return []
		leftovers = []
		for folder, dirs, files in os.walk(tempRoot):
			for name in files:
				rel = os.path.relpath(os.path.join(folder, name), tempRoot)
				if (os.path.exists(os.path.join(self.root, rel))):
					leftovers.append(rel)
				else:
					self.__removeTemp(rel)
		return sorted(leftovers)

	def adoptTemps(self, relPaths):
		"""Treat recovered temp copies as outstanding changes."""
		for rel in relPaths:
			self.dirty[rel.lower()] = DirtyEntry(rel, True, None)

	def discardTemps(self):
		self.dirty = {}
		shutil.rmtree(self.tempRoot(), ignore_errors=True)

	# --- the sidebar tree -----------------------------------------------------

	def scan(self):
		return self.__scanFolder(self.root)

	def __scanFolder(self, folder):
		try:
			entries = sorted(os.listdir(folder), key=str.lower)
		except OSError:
			return []

		dirs = []
		maps = []
		images = []
		for name in entries:
			if (name.startswith(".")):
				# Hides .fogmap/ along with everything else the GM can't use.
				continue
			full = os.path.join(folder, name)
			if (os.path.isdir(full)):
				children = self.__scanFolder(full)
				if (children):
					dirs.append(Node(full, True, children))
			elif (isMapPath(full)):
				maps.append(Node(full, False))
			elif (isImagePath(full)):
				images.append(Node(full, False))

		images = self.__nestMapImages(folder, maps, images)
		return dirs + maps + images

	def __nestMapImages(self, folder, maps, images):
		"""Tuck a map's own image underneath it.

		   Clicking the bare image beside a map would throw the whole unmasked
		   map onto the players' screen, which is the one accident this tool
		   exists to prevent.  Nesting it means reaching the image takes a
		   deliberate expand.  Only same-folder images are hidden this way,
		   since adjacency is where the misclick happens."""
		byPath = {}
		for image in images:
			byPath[self.__key(image.path)] = image

		nested = set()
		for mapNode in maps:
			imgPath = readImagePath(mapNode.path)
			if (imgPath is None):
				continue
			# join() leaves an absolute stored path alone, so both forms work.
			key = self.__key(os.path.join(folder, imgPath))
			image = byPath.get(key)
			if (image is not None):
				mapNode.children.append(Node(image.path, False))
				nested.add(key)

		return [i for i in images if self.__key(i.path) not in nested]

	# --- internals ------------------------------------------------------------

	def __key(self, path):
		if (os.path.isabs(path)):
			path = self.relPath(path)
		return os.path.normpath(path).lower()

	def __entry(self, path):
		if (not self.contains(path)):
			return None
		return self.dirty.get(self.__key(path))

	def __setEntry(self, path, hasTemp, settings):
		rel = self.relPath(path)
		self.dirty[self.__key(path)] = DirtyEntry(rel, hasTemp, copy.deepcopy(settings))

	def __removeTemp(self, rel):
		try:
			os.remove(os.path.join(self.tempRoot(), rel))
		except OSError:
			pass

	def __pruneTempRoot(self):
		"""Leave nothing behind once everything is committed, so the next open
		   does not mistake an empty tree for a crash."""
		tempRoot = self.tempRoot()
		if (not os.path.isdir(tempRoot)):
			return
		for folder, dirs, files in os.walk(tempRoot, topdown=False):
			if (not os.listdir(folder)):
				try:
					os.rmdir(folder)
				except OSError:
					pass


class Document(object):
	"""The one file currently open.  Everything else in the project lives on
	   disk, either as its original or as a temp copy."""

	def __init__(self, path, map, project=None, settings=None):
		self.path = path
		self.map = map
		self.project = project
		self.settings = settings
		self.viewDirty = False

	editable = property(lambda x: x.map.editable)
	name = property(lambda x: os.path.basename(x.path) if (x.path is not None) else "Untitled")

	def isDirty(self):
		return self.editable and (self.map.contentDirty or self.viewDirty)

	def markClean(self):
		self.map.contentDirty = False
		self.viewDirty = False

	@staticmethod
	def open(path, project=None):
		if (isImagePath(path)):
			doc = Document(path, Map.forImage(path), project)
		else:
			source = path
			fromTemp = (project is not None) and project.hasTemp(path)
			if (fromTemp):
				source = project.tempPathFor(path)
			map, settings = readMapFile(source, os.path.dirname(os.path.abspath(path)))
			doc = Document(path, map, project, settings)
			# An old-format file counts as unsaved from the outset: saving it
			# is what converts it, whether or not the GM paints on it.
			doc.map.contentDirty = fromTemp or map.legacyFormat

		if (project is not None):
			remembered = project.rememberedSettings(path)
			if (remembered is not None):
				doc.settings = remembered
			doc.viewDirty = project.isDirty(path) and not doc.map.contentDirty
		return doc

	@staticmethod
	def createNew(imagePath, project=None):
		doc = Document(None, Map.createNew(imagePath), project)
		# Nothing of it exists on disk yet, so it is unsaved from the outset.
		doc.map.contentDirty = True
		return doc

	def write(self, path):
		writeMapFile(path, self.map, self.settings)
