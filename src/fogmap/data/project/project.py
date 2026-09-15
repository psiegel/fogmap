import copy
import os
import shutil

from .dirtyentry import DirtyEntry
from .mapfile import (isLegacyMapFile, readImagePath, spliceSettings,
					  upgradeMapFile, writeMapFile)
from .node import Node
from .paths import isImagePath, isMapPath


TEMP_DIR_NAME = ".fogmap"


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
