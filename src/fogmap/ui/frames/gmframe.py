import os

import wx
import wx.lib.scrolledpanel as scrolled

from ... import data
from ... import resources

from .. import mappanel
from .. import modes
from .. import projecttree

from ..griddialog import GridDialog
from .mappanelframe import MapPanelFrame


class GMFrame(MapPanelFrame):
	def __init__(self, *args, **kwargs):
		super(GMFrame, self).__init__(*args, **kwargs)

		self.__readConfig()

		# Built before anything that shows them: the menu lists them, and the
		# toolbar is laid out around the controls each one brings with it.
		# They reach the panel through the frame, so it can come later.
		self.modes = [cls(self) for cls in modes.MODES]
		self.altMode = modes.PlayerDriveMode(self)
		# Before the toolbar, which is laid out around controls that have to
		# start out showing whatever the GM last set them to.
		self.__readModeConfig()

		self.__createMenu()
		self.__rebuildRecentFilesMenu()
		self.__rebuildRecentProjectsMenu()

		sizer = wx.BoxSizer(wx.VERTICAL)

		self.toolBar = self.__createToolbar()
		self.toolBar.Realize()
		self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.onSysColourChanged)

		# The tree lives in the left half of a splitter that is left unsplit
		# until a project is opened, so opening a lone file looks as it always did.
		self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_LIVE_UPDATE | wx.SP_3DSASH)
		self.splitter.SetMinimumPaneSize(120)

		self.projectTree = projecttree.ProjectTreePanel(self.splitter)
		self.projectTree.setSelectionListener(self.onProjectFileSelected)
		self.projectTree.Hide()

		self.scrollPanel = scrolled.ScrolledPanel(self.splitter, -1)
		scrollSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.setPanel(mappanel.GMMapPanel(self.scrollPanel))
		scrollSizer.Add(self.panel, 1, wx.EXPAND)
		self.scrollPanel.SetSizer(scrollSizer)
		self.scrollPanel.SetupScrolling()
		self.panel.setModes(self.modes, self.altMode)
		self.panel.setModeListener(self.updateControlState)
		# The panel resizes itself as it zooms, and puts the scroll position
		# back afterwards, so it needs to know what it is being scrolled by.
		self.panel.setScroller(self.scrollPanel)
		self.panel.setZoomListener(self.updateZoomControl)
		self.panel.setMode(self.modes[0], user=False)

		self.splitter.Initialize(self.scrollPanel)
		sizer.Add(self.splitter, 1, wx.EXPAND)

		self.updateControlState()
		self.SetSizer(sizer)

	def setMap(self, map):
		super(GMFrame, self).setMap(map)
		self.scrollPanel.SetupScrolling()

	def hasGrid(self):
		return (self.panel != None) and \
			   (self.panel.map != None) and \
			   self.panel.map.editable and \
			   (self.panel.map.grid != None)

	# --- projects -------------------------------------------------------------

	def setProject(self, project):
		"""Show or hide the sidebar, depending on whether there is a project."""
		self.projectTree.setProject(project)
		if (project is None):
			if (self.splitter.IsSplit()):
				self.sashPos = self.splitter.GetSashPosition()
				self.splitter.Unsplit(self.projectTree)
		else:
			if (not self.splitter.IsSplit()):
				self.projectTree.Show()
				self.splitter.SplitVertically(self.projectTree, self.scrollPanel,
											  self.sashPos)
			self.__addToRecentProjects(project.root)
		self.updateTitle()

	def refreshProjectTree(self):
		self.projectTree.rebuild()
		self.refreshDirtyMarks()

	def refreshDirtyMarks(self):
		doc = wx.GetApp().doc
		path = doc.path if (doc != None) else None
		self.projectTree.refreshDirtyMarks(path, (doc != None) and doc.isDirty())
		self.updateTitle()

	def onProjectFileSelected(self, path):
		wx.GetApp().activateDocument(path)

	def onDocumentChanged(self):
		"""Bring the window into line with whatever document is now open."""
		self.updateControlState()
		doc = wx.GetApp().doc
		if ((doc != None) and (doc.path != None)):
			self.projectTree.selectPath(doc.path)
		self.refreshDirtyMarks()

	def updateTitle(self):
		app = wx.GetApp()
		title = "GM View"
		if (app.project != None):
			title += " - " + app.project.name
		if ((app.doc != None) and (app.doc.path != None)):
			title += " - " + app.doc.name
			if (app.doc.isDirty()):
				title += " *"
		self.SetTitle(title)

	def __createMenu(self):
		# Prepare the menu bar
		self.menuBar = wx.MenuBar()

		# File Menu
		fileMenu = wx.Menu()
		fileMenu.Append(101, "&New\tCTRL+N", "Create a new map from an existing image.")
		self.Bind(wx.EVT_MENU, self.onFileNew, id=101)
		fileMenu.Append(102, "&Open\tCTRL+O", "Open an existing map.")
		self.Bind(wx.EVT_MENU, self.onFileOpen, id=102)
		self.recentFilesMenu = wx.Menu()
		fileMenu.AppendSubMenu(self.recentFilesMenu, "Open Recent")
		self.menuBar.Append(fileMenu, "&File")

		fileMenu.AppendSeparator()
		fileMenu.Append(107, "Open &Project\tCTRL+SHIFT+O",
						"Open a folder of maps and images.")
		self.Bind(wx.EVT_MENU, self.onOpenProject, id=107)
		self.recentProjectsMenu = wx.Menu()
		fileMenu.AppendSubMenu(self.recentProjectsMenu, "Open Recent Project")
		fileMenu.Append(108, "&Close Project", "Close the current project.")
		self.Bind(wx.EVT_MENU, self.onCloseProject, id=108)
		self.Bind(wx.EVT_UPDATE_UI, self.onProjectOpenUpdate, id=108)

		fileMenu.AppendSeparator()
		fileMenu.Append(104, "&Save\tCTRL+S", "Save the current map.")
		self.Bind(wx.EVT_MENU, self.onFileSave, id=104)
		self.Bind(wx.EVT_UPDATE_UI, self.onEditableDocUpdate, id=104)
		fileMenu.Append(109, "Save A&ll\tCTRL+SHIFT+S",
						"Save every map in the project with unsaved changes.")
		self.Bind(wx.EVT_MENU, self.onFileSaveAll, id=109)
		self.Bind(wx.EVT_UPDATE_UI, self.onSaveAllUpdate, id=109)
		fileMenu.Append(105, "Save &As\tCTRL+A", "Save the current map to a new file.")
		self.Bind(wx.EVT_MENU, self.onFileSaveAs, id=105)
		self.Bind(wx.EVT_UPDATE_UI, self.onEditableDocUpdate, id=105)
		fileMenu.Append(106, "S&wap Image\tCTRL+W", "Change image of existing map.")
		self.Bind(wx.EVT_MENU, self.onSwapImage, id=106)
		self.Bind(wx.EVT_UPDATE_UI, self.onEditableDocUpdate, id=106)

		# Grid Menu
		gridMenu = wx.Menu()
		gridMenu.Append(201, "Show Grid", "Toggle display of the current grid.", wx.ITEM_CHECK)
		self.Bind(wx.EVT_UPDATE_UI, self.onGridVisibleUpdate, id=201)
		self.Bind(wx.EVT_MENU, self.onGridToggle, id=201)
		gridMenu.Append(202, "Grid Settings", "Change grid settings.")
		self.Bind(wx.EVT_MENU, self.onGridSettings, id=202)
		self.Bind(wx.EVT_UPDATE_UI, self.onGridSettingsUpdate, id=202)
		self.menuBar.Append(gridMenu, "Grid")

		# View Menu.  Well clear of the 301+ range the recent files menu uses.
		viewMenu = wx.Menu()
		# What the mouse is for comes first: it is the biggest thing about this
		# window, and the toolbar switcher sits at the far left for the same
		# reason.  One item per mode, so a new mode needs nothing here.
		for index, mode in enumerate(self.modes):
			menuId = GMFrame.FIRST_MODE_ID + index
			label = mode.label + " Mode"
			if (mode.hotkey != None):
				label += "\t" + mode.hotkey
			viewMenu.Append(menuId, label, mode.help, wx.ITEM_RADIO)
			self.Bind(wx.EVT_MENU,
					  lambda evt, mode=mode: self.setMode(mode), id=menuId)
			self.Bind(wx.EVT_UPDATE_UI, self.onModeMenuUpdate, id=menuId)
		viewMenu.AppendSeparator()
		viewMenu.Append(1002, "Fit Player View to Map\tCTRL+0",
						"Zoom the player view out until the whole map fits.")
		self.Bind(wx.EVT_MENU, self.onFitPlayerView, id=1002)
		self.Bind(wx.EVT_UPDATE_UI, self.onPlayerViewUpdate, id=1002)
		viewMenu.AppendSeparator()
		viewMenu.Append(1003, "Zoom &In\tCTRL+=", "Zoom the GM map in one level.")
		self.Bind(wx.EVT_MENU, self.onZoomIn, id=1003)
		self.Bind(wx.EVT_UPDATE_UI, self.onZoomUpdate, id=1003)
		viewMenu.Append(1004, "Zoom &Out\tCTRL+-", "Zoom the GM map out one level.")
		self.Bind(wx.EVT_MENU, self.onZoomOut, id=1004)
		self.Bind(wx.EVT_UPDATE_UI, self.onZoomUpdate, id=1004)
		viewMenu.Append(1005, "&Actual Size\tCTRL+1", "Show the GM map at 100%.")
		self.Bind(wx.EVT_MENU, self.onZoomActual, id=1005)
		self.Bind(wx.EVT_UPDATE_UI, self.onZoomUpdate, id=1005)
		viewMenu.Append(1006, "&Fit Map to Window\tCTRL+9",
						"Zoom the GM map out until the whole of it fits.")
		self.Bind(wx.EVT_MENU, self.onZoomFit, id=1006)
		self.Bind(wx.EVT_UPDATE_UI, self.onZoomUpdate, id=1006)
		self.menuBar.Append(viewMenu, "View")

		self.SetMenuBar(self.menuBar)

		# CTRL+B used to toggle the player viewport overlay, from before it
		# became a mode of its own.  Kept working, as a jump into that mode and
		# back out again; no menu item claims it, so it lives in a table here.
		self.Bind(wx.EVT_MENU, self.onToggleViewportMode, id=GMFrame.TOGGLE_VIEWPORT_ID)
		self.SetAcceleratorTable(wx.AcceleratorTable([
			wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("B"), GMFrame.TOGGLE_VIEWPORT_ID)]))

	def __createToolbar(self):
		"""Mode first, then whatever that mode brings with it, then the GM's own
		   zoom - which belongs to the window rather than to any one mode, and so
		   stays put on the right whatever is being shown in the middle.

		   Icons and tooltips rather than captions and labelled drop-downs: the
		   toolbar is one row across a window whose whole point is the map under
		   it, and text spends that row faster than anything else."""
		tb = self.CreateToolBar(wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT |
								wx.TB_TEXT)
		tb.SetToolBitmapSize(wx.Size(resources.ICON_SIZE, resources.ICON_SIZE))

		for index, mode in enumerate(self.modes):
			toolId = GMFrame.FIRST_MODE_TOOL_ID + index
			tb.AddTool(toolId, mode.label, resources.icon(mode.icon), mode.help,
					   wx.ITEM_RADIO)
			self.Bind(wx.EVT_TOOL,
					  lambda evt, mode=mode: self.onModeTool(mode), id=toolId)
			resources.trackIcon(
				tb,
				lambda bundle, toolId=toolId: tb.SetToolNormalBitmap(toolId, bundle),
				mode.icon)

		tb.AddSeparator()

		# One page per mode, rather than showing and hiding controls in place:
		# the book is as wide as its widest page whichever is showing, so
		# switching modes does not shuffle the zoom box about.
		self.modeBook = wx.Simplebook(tb, -1)
		for mode in self.modes:
			page = wx.Panel(self.modeBook, -1)
			pageSizer = wx.BoxSizer(wx.HORIZONTAL)
			mode.buildControls(page, pageSizer)
			page.SetSizerAndFit(pageSizer)
			self.modeBook.AddPage(page, mode.label)
		# A toolbar takes a control at the size it already is, and a book that
		# has never been laid out is a few pixels square.  Size it to the
		# largest page here, which is also what keeps the width steady.
		sizes = [page.GetBestSize() for page in self.modeBook.GetChildren()]
		if (sizes):
			self.modeBook.SetInitialSize(wx.Size(max(size.width for size in sizes),
												 max(size.height for size in sizes)))
		tb.AddControl(self.modeBook)

		tb.AddSeparator()

		self.__addIconTool(tb, 1004, "zoom-out", "Zoom the GM map out one level.")

		# Fixed levels rather than a free scale, so this box can always show
		# exactly where the zoom is, however it was last changed.
		self.zoomChoice = wx.Choice(tb, -1, choices=[GMFrame.zoomLabel(level)
							for level in mappanel.GMMapPanel.ZOOM_LEVELS])
		self.zoomChoice.SetToolTip("How big the GM's own map is drawn.  Does not "
								   "affect what the players see.")
		self.Bind(wx.EVT_CHOICE, self.onZoomChoice, self.zoomChoice)
		tb.AddControl(self.zoomChoice)

		self.__addIconTool(tb, 1003, "zoom-in", "Zoom the GM map in one level.")

		return tb

	def __addIconTool(self, tb, toolId, name, tip):
		"""A toolbar tool that shows its icon and no caption, and that keeps
		   that icon in step with a light/dark switch."""
		tb.AddTool(toolId, "", resources.icon(name), tip)
		resources.trackIcon(
			tb,
			lambda bundle, toolId=toolId: tb.SetToolNormalBitmap(toolId, bundle),
			name)

	def onSysColourChanged(self, evt):
		"""The icons are line art inked for one appearance or the other, and
		   macOS switches itself between the two at sunset - so this is not
		   only about the GM changing the setting by hand mid-session."""
		resources.refreshIcons()
		self.toolBar.Refresh()
		evt.Skip()

	def doClose(self):
		self.Destroy()
		wx.GetApp().ExitMainLoop()

	def onClose(self, evt):
		if (not wx.GetApp().confirmDiscardChanges()):
			if (evt.CanVeto()):
				evt.Veto()
			return
		self.__writeConfig()
		super(GMFrame, self).onClose(evt)

	def onFileNew(self, evt):
		path = self.__askForImage("Select a Map Image")
		if (path is None):
			return
		app = wx.GetApp()
		if (not app.newMap(path)):
			return
		if (app.project != None):
			# Give it a home in the project straight away, so switching files
			# never has to worry about an unsaved document with nowhere to go.
			self.onFileSaveAs(evt)

	def onFileOpen(self, evt):
		defaultDir, defaultFile = self.defaultDirAndFile()
		dlg = wx.FileDialog(self, 
							message="Choose a map", 
							defaultDir=defaultDir,
							defaultFile=defaultFile,
							wildcard="Map files (*.map)|*.map|All files (*.*)|*.*",
							style=wx.FD_OPEN | wx.FD_CHANGE_DIR)
		if (dlg.ShowModal() == wx.ID_OK):
			if (wx.GetApp().activateDocument(dlg.GetPath())):
				self.__addToRecentFiles(dlg.GetPath())
		dlg.Destroy()

	def onFileOpenRecent(self, evt, path):
		if os.path.exists(path):
			wx.GetApp().activateDocument(path)
		else:
			self.recentFiles.remove(path)
			self.__rebuildRecentFilesMenu()
			self.__writeConfig()

	def onOpenProject(self, evt):
		dlg = wx.DirDialog(self, message="Choose a project folder",
						   defaultPath=self.defaultDirAndFile()[0],
						   style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
		if (dlg.ShowModal() == wx.ID_OK):
			wx.GetApp().openProject(dlg.GetPath())
		dlg.Destroy()

	def onOpenRecentProject(self, evt, path):
		if os.path.isdir(path):
			wx.GetApp().openProject(path)
		else:
			self.recentProjects.remove(path)
			self.__rebuildRecentProjectsMenu()
			self.__writeConfig()

	def onCloseProject(self, evt):
		wx.GetApp().closeProject()

	def onProjectOpenUpdate(self, evt):
		evt.Enable(wx.GetApp().project != None)

	def onFileSave(self, evt):
		app = wx.GetApp()
		if ((app.doc != None) and (app.doc.path != None)):
			app.saveDocument()
		else:
			self.onFileSaveAs(evt)

	def onFileSaveAs(self, evt):
		defaultDir, defaultFile = self.defaultDirAndFile()
		dlg = wx.FileDialog(self, 
							message="Save map", 
							defaultDir=defaultDir,
							defaultFile=defaultFile,
							wildcard="Map files (*.map)|*.map|All files (*.*)|*.*",
							style=wx.FD_SAVE | wx.FD_CHANGE_DIR)
		if (dlg.ShowModal() == wx.ID_OK):
			wx.GetApp().saveDocument(dlg.GetPath())
			self.__addToRecentFiles(dlg.GetPath())
		dlg.Destroy()

	def onFileSaveAll(self, evt):
		wx.GetApp().saveAll()

	def onSaveAllUpdate(self, evt):
		evt.Enable(wx.GetApp().hasUnsavedChanges())

	def onEditableDocUpdate(self, evt):
		"""Saving and image swapping mean nothing for a plain image handout."""
		doc = wx.GetApp().doc
		evt.Enable((doc != None) and doc.editable)

	def onSwapImage(self, evt):
		path = self.__askForImage("Select a Map Image")
		if (path != None):
			wx.GetApp().swapMapImage(path)

	def __askForImage(self, message):
		defaultDir, defaultFile = self.defaultDirAndFile()
		wildcard = "All files (*.*)|*.*|"\
				 "BMP Image (*.bmp)|*.bmp|"\
				 "GIF Image (*.gif)|*.gif|" \
				 "JPEG Image (*.jpg)|*.jpg|" \
				 "PNG Image (*.png)|*.png"
		dlg = wx.FileDialog(self, 
							message=message, 
							defaultDir=defaultDir,
							defaultFile=defaultFile,
							wildcard=wildcard,
							style=wx.FD_OPEN | wx.FD_CHANGE_DIR)
		path = dlg.GetPath() if (dlg.ShowModal() == wx.ID_OK) else None
		dlg.Destroy()
		return path

	def defaultDirAndFile(self):
		app = wx.GetApp()
		if ((app.doc != None) and (app.doc.path != None)):
			return os.path.split(app.doc.path)
		if (app.project != None):
			return app.project.root, ""
		lastPath = app.lastSavePath
		if lastPath is None:
			return os.getcwd(), ""
		return os.path.split(lastPath)

	def onGridToggle(self, evt):
		if (self.hasGrid()):
			self.panel.map.grid.visible = evt.IsChecked()

	def onGridVisibleUpdate(self, evt):		
		gridExists = self.hasGrid() and (self.panel.map.grid.type != data.Grid.GRID_NONE)
		evt.Enable(gridExists)
		evt.Check(gridExists and self.panel.map.grid.visible)

	def onGridSettings(self, evt):
		if (not self.hasGrid()):
			return
		currentGrid = self.panel.map.grid.copy()
		dlg = GridDialog(self.panel.map.grid, self, -1, "Grid Settings")
		dlg.CenterOnParent()
		if (dlg.ShowModal() != wx.ID_OK):
			self.panel.map.grid = currentGrid
		dlg.Destroy()
		
	def onGridSettingsUpdate(self, evt):
		evt.Enable(self.hasGrid())

	def hasPlayerView(self):
		return (self.panel != None) and (self.panel.playerPanel != None)

	# --- modes ------------------------------------------------------------------

	# Mode menu ids, and the id CTRL+B carries.  Well clear of 1001-1006, and
	# of the 301+ and 401+ ranges the two recent menus use.
	FIRST_MODE_ID = 1010
	TOGGLE_VIEWPORT_ID = 1009

	# The switcher's own ids, one per mode, kept apart from the menu's so that
	# a tool and its menu item can be enabled and checked independently.
	FIRST_MODE_TOOL_ID = 1030

	def setMode(self, mode):
		if (self.panel != None):
			self.panel.setMode(mode)

	def onModeTool(self, mode):
		self.setMode(mode)
		# The panel has the last word on which mode it is in - an unavailable
		# one falls back - so let it say which tool should end up pressed.
		self.updateControlState()

	def onModeMenuUpdate(self, evt):
		mode = self.modes[evt.GetId() - GMFrame.FIRST_MODE_ID]
		evt.Enable(mode.isAvailable())
		evt.Check((self.panel != None) and (self.panel.mode is mode))

	def onToggleViewportMode(self, evt):
		"""CTRL+B, which used to switch the overlay on and off: into the
		   viewport mode, or back to the main one if that is where we are."""
		mode = self.panel.modeByKey(modes.ViewportMode.key)
		self.setMode(self.modes[0] if (self.panel.mode is mode) else mode)

	def updateControlState(self):
		"""Keep the toolbar in step however the mode got changed - the
		   switcher, the menu, or a setting read back from a map file - and
		   with what the open document allows."""
		mode = self.panel.mode if (self.panel != None) else None
		if (mode in self.modes):
			self.modeBook.SetSelection(self.modes.index(mode))
		for index, each in enumerate(self.modes):
			toolId = GMFrame.FIRST_MODE_TOOL_ID + index
			# One tool per mode means each can be enabled on its own, the way
			# the View menu always has: the viewport mode cannot be entered
			# without a player window, which the single drop-down could only
			# say by greying out every mode at once.
			self.toolBar.EnableTool(toolId,
									(self.panel != None) and each.isAvailable())
			self.toolBar.ToggleTool(toolId, each is mode)
		for each in self.modes:
			each.updateControls()
		self.updateZoomControl()

	def onPlayerViewUpdate(self, evt):
		evt.Enable(self.hasPlayerView())

	def onFitPlayerView(self, evt):
		if (self.hasPlayerView() and (self.panel.map != None)):
			w, h = self.panel.map.size
			self.panel.playerPanel.showMapRect((0, 0, w, h))

	# --- zoom -----------------------------------------------------------------

	@staticmethod
	def zoomLabel(scale):
		return "%d%%" % round(scale * 100)

	def updateZoomControl(self):
		"""Keep the toolbar box showing whatever the zoom actually is, however
		   it got there - the box, the menu, the wheel, or a level read back
		   out of a map file."""
		if (self.panel is None):
			return
		self.zoomChoice.Enable(self.panel.map != None)
		self.zoomChoice.SetStringSelection(GMFrame.zoomLabel(self.panel.scale))

	def onZoomChoice(self, evt):
		index = self.zoomChoice.GetSelection()
		if (index != wx.NOT_FOUND):
			self.panel.zoomTo(mappanel.GMMapPanel.ZOOM_LEVELS[index])

	def onZoomIn(self, evt):
		self.panel.zoomStep(1)

	def onZoomOut(self, evt):
		self.panel.zoomStep(-1)

	def onZoomActual(self, evt):
		self.panel.zoomTo(mappanel.GMMapPanel.DEFAULT_ZOOM)

	def onZoomFit(self, evt):
		self.panel.zoomTo(self.panel.fitZoomLevel())

	def onZoomUpdate(self, evt):
		evt.Enable((self.panel != None) and (self.panel.map != None))

	# Both recent lists are capped so their menu ids cannot run into the next
	# range: files use 301+, projects 401+.
	MAX_RECENT = 10

	def __addToRecentFiles(self, path):
		self.recentFiles = self.__addToRecent(self.recentFiles, path)
		self.__rebuildRecentFilesMenu()
		self.__writeConfig()

	def __addToRecentProjects(self, path):
		self.recentProjects = self.__addToRecent(self.recentProjects, path)
		self.__rebuildRecentProjectsMenu()
		self.__writeConfig()

	def __addToRecent(self, paths, path):
		if path in paths:
			paths.remove(path)
		paths.insert(0, path)
		return paths[:GMFrame.MAX_RECENT]

	def __readConfig(self):
		config = wx.Config("fogmap")
		self.recentFiles = self.__readPathGroup(config, "/RecentFiles")
		self.recentProjects = self.__readPathGroup(config, "/RecentProjects")
		config.SetPath("/")
		self.sashPos = config.ReadInt("ProjectSashPos", 220)

	def __readModeConfig(self, config=None):
		"""A mode's own settings - the pen and how long its ink lasts - belong
		   to the GM rather than to any one map, so they are kept here rather
		   than in a map file.  One group each, named for the mode."""
		config = wx.Config("fogmap") if (config is None) else config
		for mode in self.modes:
			config.SetPath("/Modes/" + mode.key)
			mode.readConfig(config)
		config.SetPath("/")

	def __writeModeConfig(self, config):
		for mode in self.modes:
			config.SetPath("/Modes/" + mode.key)
			mode.writeConfig(config)
		config.SetPath("/")

	def __readPathGroup(self, config, group):
		paths = []
		config.SetPath(group)
		more, value, index = config.GetFirstEntry()
		while more:
			paths.append(config.Read(value))
			more, value, index = config.GetNextEntry(index)
		return paths[:GMFrame.MAX_RECENT]

	def __writeConfig(self):
		config = wx.Config("fogmap")
		self.__writePathGroup(config, "/RecentFiles", self.recentFiles)
		self.__writePathGroup(config, "/RecentProjects", self.recentProjects)
		config.SetPath("/")
		if (self.splitter.IsSplit()):
			self.sashPos = self.splitter.GetSashPosition()
		config.WriteInt("ProjectSashPos", self.sashPos)
		self.__writeModeConfig(config)
		config.Flush()

	def __writePathGroup(self, config, group, paths):
		config.DeleteGroup(group)
		config.SetPath(group)
		for index, path in enumerate(paths):
			config.Write(str(index), path)

	def __rebuildRecentFilesMenu(self):
		self.__rebuildRecentMenu(self.recentFilesMenu, self.recentFiles, 301,
								 self.onFileOpenRecent)

	def __rebuildRecentProjectsMenu(self):
		self.__rebuildRecentMenu(self.recentProjectsMenu, self.recentProjects, 401,
								 self.onOpenRecentProject)

	def __rebuildRecentMenu(self, menu, paths, firstId, handler):
		for item in menu.GetMenuItems():
			self.Unbind(wx.EVT_MENU, id=item.GetId())
			menu.Remove(item)
		for idx, path in enumerate(paths):
			menuId = firstId + idx
			menu.Append(menuId, path)
			self.Bind(wx.EVT_MENU,
					  lambda evt, path=path: handler(evt, path),
					  id=menuId)


