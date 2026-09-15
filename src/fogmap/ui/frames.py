import os
import copy
import wx
import wx.lib.scrolledpanel as scrolled

from .. import data
from .. import resources

from . import mappanel
from . import projecttree
from . import tools

class MapPanelFrame(wx.Frame):	
	def __init__(self, *args, **kwargs):	
		super(MapPanelFrame, self).__init__(*args, **kwargs)
		icons = resources.appIcons()
		if (icons is not None):
			# No effect on the Mac, which has no per-window icons; the Dock tile
			# is set once for the whole app instead.  See FogMapApp.OnInit.
			self.SetIcons(icons)
		self.Bind(wx.EVT_CLOSE, self.onClose)		

	def setPanel(self, mapPanel):
		self.panel = mapPanel

	def setMap(self, map):
		self.panel.reset()
		self.panel.setMap(map)

	def onClose(self, evt):
		canClose = True
		if (self.panel != None):
			canClose = self.panel.onClose(evt)
		if (canClose):
			self.doClose()

	def doClose(self):
		self.Destroy()


class PlayerFrame(MapPanelFrame):
	def __init__(self, *args, **kwargs):
		super(PlayerFrame, self).__init__(*args, **kwargs)			
		self.setPanel(mappanel.PlayerMapPanel(self))	

		box = wx.BoxSizer(wx.HORIZONTAL)
		box.Add(self.panel, 1, wx.EXPAND)
		self.panel.Bind(wx.EVT_LEFT_DCLICK, self.onLeftDClick)
		self.SetSizer(box)

	def onLeftDClick(self, evt):
		self.ShowFullScreen(not self.IsFullScreen())


class GMFrame(MapPanelFrame):
	def __init__(self, *args, **kwargs):
		super(GMFrame, self).__init__(*args, **kwargs)

		self.__readConfig()
		self.__createMenu()
		self.__rebuildRecentFilesMenu()
		self.__rebuildRecentProjectsMenu()

		sizer = wx.BoxSizer(wx.VERTICAL)

		self.brushBar = self.__createBrushToolbar()
		self.brushBar.Realize()

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
		self.panel.setViewportListener(self.updateControlState)
		# The panel resizes itself as it zooms, and puts the scroll position
		# back afterwards, so it needs to know what it is being scrolled by.
		self.panel.setScroller(self.scrollPanel)
		self.panel.setZoomListener(self.updateZoomControl)

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
		# The panel drops its brush when the map changes, so the toolbar has to
		# agree or the GM is left with a brush type selected and no brush.
		self.brushType.SetStringSelection("None")
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
		viewMenu.Append(1001, "Show Player Viewport\tCTRL+B",
						"Outline the area the players can currently see.", wx.ITEM_CHECK)
		self.Bind(wx.EVT_MENU, self.onViewportToggle, id=1001)
		self.Bind(wx.EVT_UPDATE_UI, self.onViewportUpdate, id=1001)
		viewMenu.Append(1002, "Fit Player View to Map\tCTRL+0",
						"Zoom the player view out until the whole map fits.")
		self.Bind(wx.EVT_MENU, self.onFitPlayerView, id=1002)
		self.Bind(wx.EVT_UPDATE_UI, self.onViewportUpdate, id=1002)
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

	def __createBrushToolbar(self):
		tb = self.CreateToolBar(wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)

		tb.AddControl(wx.StaticText(tb, -1, "Brush Type: "))

		brushTypes = ["None", "Round", "Square", "Grid"]
		self.brushType = wx.Choice(tb, -1, (100, 50), choices=brushTypes)
		self.Bind(wx.EVT_CHOICE, self.onBrushTypeChanged, self.brushType)
		tb.AddControl(self.brushType)

		tb.AddSeparator()

		tb.AddControl(wx.StaticText(tb, -1, "Brush Size: "))

		self.brushSize = wx.Slider(tb, -1, 1, 1, 100, size=(100, -1), style=wx.SL_HORIZONTAL)
		self.Bind(wx.EVT_SLIDER, self.onBrushSizeChanged, self.brushSize)
		tb.AddControl(self.brushSize)

		tb.AddSeparator()

		# A plain control rather than a check tool, so it needs no bitmap and
		# matches how the brush controls above are added.
		self.viewportToggle = wx.ToggleButton(tb, -1, "Player Viewport")
		self.viewportToggle.SetToolTip("Show the players' visible area and drag it "
									   "around.  Suspends the brush.")
		self.Bind(wx.EVT_TOGGLEBUTTON, self.onViewportButton, self.viewportToggle)
		tb.AddControl(self.viewportToggle)

		tb.AddSeparator()

		tb.AddControl(wx.StaticText(tb, -1, "Zoom: "))

		# Fixed levels rather than a free scale, so this box can always show
		# exactly where the zoom is, however it was last changed.
		self.zoomChoice = wx.Choice(tb, -1, choices=[GMFrame.zoomLabel(level)
							for level in mappanel.GMMapPanel.ZOOM_LEVELS])
		self.zoomChoice.SetToolTip("How big the GM's own map is drawn.  Does not "
								   "affect what the players see.")
		self.Bind(wx.EVT_CHOICE, self.onZoomChoice, self.zoomChoice)
		tb.AddControl(self.zoomChoice)

		return tb

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
		dlg = tools.GridDialog(self.panel.map.grid, self, -1, "Grid Settings")
		dlg.CenterOnParent()
		if (dlg.ShowModal() != wx.ID_OK):
			self.panel.map.grid = currentGrid
		dlg.Destroy()
		
	def onGridSettingsUpdate(self, evt):
		evt.Enable(self.hasGrid())

	def hasPlayerView(self):
		return (self.panel != None) and (self.panel.playerPanel != None)

	def updateControlState(self):
		"""Keep the toolbar in step however the overlay got toggled - button,
		   menu, or a setting read back from a map file - and with whether the
		   open document can be painted on at all."""
		active = (self.panel != None) and self.panel.showViewport
		self.viewportToggle.SetValue(active)
		self.viewportToggle.Enable(self.hasPlayerView())
		# The overlay takes over the mouse, and a plain image has no fog, so
		# either way the brush is unavailable.
		canPaint = (self.panel != None) and self.panel.canPaint() and (not active)
		self.brushType.Enable(canPaint)
		self.brushSize.Enable(canPaint)
		self.updateZoomControl()

	def onViewportButton(self, evt):
		self.panel.setShowViewport(self.viewportToggle.GetValue())

	def onViewportToggle(self, evt):
		self.panel.setShowViewport(evt.IsChecked())

	def onViewportUpdate(self, evt):
		evt.Enable(self.hasPlayerView())
		if (evt.GetId() == 1001):
			evt.Check(self.hasPlayerView() and self.panel.showViewport)

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

	def onBrushTypeChanged(self, evt):
		if (not self.panel.canPaint()):
			return
		brush = None
		brushType = self.brushType.GetStringSelection()
		self.updateBrushSizeSlider(brushType == "Grid")
		if (brushType == "Round"):
			brush = data.RoundFreehandBrush(self.getBrushSize())
		elif (brushType == "Square"):
			# TODO: We could support rects if we wanted
			size = self.getBrushSize()
			brush = data.SquareFreehandBrush(size, size)
		elif (brushType == "Grid"):
			if (self.panel.map.grid.type == data.Grid.GRID_NONE):
				dlg = wx.MessageDialog(self, 'Cannot set brush type to grid unless grid is enabled.', 'Bad Brush Choice', wx.OK | wx.ICON_ERROR)
				dlg.ShowModal()
				dlg.Destroy()
				self.brushType.SetStringSelection("None")
			elif (self.panel.map.grid.type == data.Grid.GRID_SQUARE):
				brush = data.SquareGridBrush(self.panel.map.grid.size, self.getBrushSize())
			elif (self.panel.map.grid.type == data.Grid.GRID_HEX):
				brush = data.HexGridBrush(self.panel.map.grid.size, self.getBrushSize())
		self.panel.setBrush(brush)
		self.panel.Refresh()

	def onBrushSizeChanged(self, evt):
		if (self.panel.brush != None):
			size = self.getBrushSize()
			self.panel.brush.setSize(size)
			self.panel.Refresh()

	def getBrushSize(self):
		return self.brushSize.GetValue() 
	
	def updateBrushSizeSlider(self, isGrid):
		if (isGrid):
			newValue = (self.brushSize.GetValue() * 10 // self.brushSize.GetMax())
			self.brushSize.SetRange(1, 10)
			self.brushSize.SetValue(newValue)
		else:
			newValue = 5 + (self.brushSize.GetValue() * 495 // self.brushSize.GetMax())			
			self.brushSize.SetRange(5, 500)
			self.brushSize.SetValue(newValue)

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

	