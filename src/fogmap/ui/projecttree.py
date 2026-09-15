"""The project sidebar in the GM window.

A map's own image is nested underneath it rather than sitting beside it, so
showing the players an unmasked map takes a deliberate expand-and-click.
"""
import os
import wx

from .. import data


class ProjectTreePanel(wx.Panel):
	def __init__(self, parent):
		super(ProjectTreePanel, self).__init__(parent, -1)

		self.project = None
		self.selectionListener = None
		self.itemsByPath = {}
		# Set while the app is driving the selection, so echoing it back as a
		# file-open request does not fight whatever the app is in the middle of.
		self.settingSelection = False

		self.tree = wx.TreeCtrl(self, -1,
								style=wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS |
									  wx.TR_SINGLE | wx.TR_LINES_AT_ROOT |
									  wx.BORDER_NONE)
		self.__createIcons()

		self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.onSelectionChanged)
		self.tree.Bind(wx.EVT_CHAR_HOOK, self.onChar)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.tree, 1, wx.EXPAND)
		self.SetSizer(sizer)

	def setSelectionListener(self, listener):
		"""Called with the path of a file the GM picked out of the tree."""
		self.selectionListener = listener

	def setProject(self, project):
		self.project = project
		self.rebuild()

	def rebuild(self):
		selected = self.selectedPath()
		self.tree.DeleteAllItems()
		self.itemsByPath = {}
		root = self.tree.AddRoot("project")
		if (self.project is not None):
			for node in self.project.scan():
				self.__addNode(root, node)
		if (selected is not None):
			self.selectPath(selected)

	def selectedPath(self):
		item = self.tree.GetSelection()
		if ((not item.IsOk()) or (item == self.tree.GetRootItem())):
			return None
		return self.tree.GetItemData(item)

	def selectPath(self, path):
		item = self.itemsByPath.get(self.__key(path))
		if (item is None):
			return
		self.settingSelection = True
		try:
			self.tree.EnsureVisible(item)
			self.tree.SelectItem(item)
		finally:
			self.settingSelection = False

	def setDirty(self, path, dirty):
		item = self.itemsByPath.get(self.__key(path))
		if (item is not None):
			self.__markItem(item, dirty)

	def refreshDirtyMarks(self, activePath=None, activeDirty=False):
		for key, item in self.itemsByPath.items():
			path = self.tree.GetItemData(item)
			dirty = (self.project is not None) and self.project.isDirty(path)
			if ((activePath is not None) and (key == self.__key(activePath))):
				dirty = activeDirty
			self.__markItem(item, dirty)

	def onSelectionChanged(self, evt):
		if (self.settingSelection):
			return
		item = evt.GetItem()
		if (not item.IsOk()):
			return
		path = self.tree.GetItemData(item)
		# Folders are for expanding, not opening.
		if ((path is None) or os.path.isdir(path)):
			return
		if (self.selectionListener is not None):
			self.selectionListener(path)

	def onChar(self, evt):
		if (evt.GetKeyCode() == wx.WXK_F5):
			self.rebuild()
		else:
			evt.Skip()

	def __addNode(self, parent, node):
		if (node.isDir):
			icon = self.folderIcon
		elif (data.isMapPath(node.path)):
			icon = self.mapIcon
		else:
			icon = self.imageIcon

		item = self.tree.AppendItem(parent, node.name, image=icon)
		self.tree.SetItemData(item, node.path)
		if (node.isDir):
			self.tree.SetItemImage(item, self.folderOpenIcon, wx.TreeItemIcon_Expanded)
		else:
			self.itemsByPath[self.__key(node.path)] = item
			if ((self.project is not None) and self.project.isDirty(node.path)):
				self.__markItem(item, True)

		for child in node.children:
			self.__addNode(item, child)

		# Folders open up; a map stays shut so its image is not one click away.
		if (node.isDir):
			self.tree.Expand(item)

	def __markItem(self, item, dirty):
		name = os.path.basename(self.tree.GetItemData(item))
		self.tree.SetItemText(item, ("* " + name) if dirty else name)
		self.tree.SetItemBold(item, dirty)

	def __createIcons(self):
		size = (16, 16)
		images = wx.ImageList(*size)
		def art(id):
			return images.Add(wx.ArtProvider.GetBitmap(id, wx.ART_OTHER, size))
		self.folderIcon = art(wx.ART_FOLDER)
		self.folderOpenIcon = art(wx.ART_FOLDER_OPEN)
		self.mapIcon = art(wx.ART_NORMAL_FILE)
		self.imageIcon = art(wx.ART_HELP_PAGE)
		self.tree.AssignImageList(images)

	def __key(self, path):
		return os.path.normcase(os.path.abspath(path)).lower()
