import os
import copy
import wx
import wx.lib.scrolledpanel as scrolled

import data

from . import mappanel
from . import tools

class MapPanelFrame(wx.Frame):	
	def __init__(self, *args, **kwargs):	
		super(MapPanelFrame, self).__init__(*args, **kwargs)
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

		self.__readRecentPaths()
		self.__createMenu()
		self.__rebuildRecentFilesMenu()

		sizer = wx.BoxSizer(wx.VERTICAL)

		self.brushBar = self.__createBrushToolbar()
		self.brushBar.Realize()

		self.scrollPanel = scrolled.ScrolledPanel(self, -1)
		scrollSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.setPanel(mappanel.GMMapPanel(self.scrollPanel))
		scrollSizer.Add(self.panel, 1, wx.EXPAND)
		self.scrollPanel.SetSizer(scrollSizer)
		self.scrollPanel.SetupScrolling()
		self.panel.setViewportListener(self.onViewportChanged)
		self.onViewportChanged()
		sizer.Add(self.scrollPanel, 1, wx.EXPAND)

		self.SetSizer(sizer)

	def setMap(self, map):
		super(GMFrame, self).setMap(map)
		self.scrollPanel.SetupScrolling()

	def hasGrid(self):
		return (self.panel != None) and \
			   (self.panel.map != None) and \
			   (self.panel.map.grid != None)

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
		fileMenu.Append(104, "&Save\tCTRL+S", "Save the current map.")
		self.Bind(wx.EVT_MENU, self.onFileSave, id=104)
		fileMenu.Append(105, "Save &As\tCTRL+A", "Save the current map to a new file.")
		self.Bind(wx.EVT_MENU, self.onFileSaveAs, id=105)
		fileMenu.Append(106, "S&wap Image\tCTRL+W", "Change image of existing map.")
		self.Bind(wx.EVT_MENU, self.onSwapImage, id=106)

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

		return tb

	def doClose(self):
		self.Destroy()
		wx.GetApp().ExitMainLoop()

	def onFileNew(self, evt):
		defaultDir, defaultFile = self.defaultDirAndFile()
		wildcard = "All files (*.*)|*.*|"\
				 "BMP Image (*.bmp)|*.bmp|"\
				 "GIF Image (*.gif)|*.gif|" \
				 "JPEG Image (*.jpg)|*.jpg|" \
				 "PNG Image (*.png)|*.png"
		dlg = wx.FileDialog(self, 
							message="Select a Map Image", 
							defaultDir=defaultDir,
							defaultFile=defaultFile,
							wildcard=wildcard,
							style=wx.FD_OPEN | wx.FD_CHANGE_DIR)
		if (dlg.ShowModal() == wx.ID_OK):
			app = wx.GetApp()
			app.newMap(dlg.GetPath())
		dlg.Destroy()

	def onFileOpen(self, evt):
		defaultDir, defaultFile = self.defaultDirAndFile()
		dlg = wx.FileDialog(self, 
							message="Choose a map", 
							defaultDir=defaultDir,
							defaultFile=defaultFile,
							wildcard="Map files (*.map)|*.map|All files (*.*)|*.*",
							style=wx.FD_OPEN | wx.FD_CHANGE_DIR)
		if (dlg.ShowModal() == wx.ID_OK):
			app = wx.GetApp()
			app.loadMap(dlg.GetPath())
			self.__addToRecentFiles(dlg.GetPath())
		dlg.Destroy()

	def onFileOpenRecent(self, evt, path):
		if os.path.exists(path):
			wx.GetApp().loadMap(path)
		else:
			self.recentFiles.remove(path)
			self.__rebuildRecentFilesMenu()
			self.__writeRecentPaths()

	def onFileSave(self, evt):
		lastPath = wx.GetApp().lastSavePath
		if (lastPath is not None):
			app = wx.GetApp()
			app.saveMap(lastPath)
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
			app = wx.GetApp()
			app.saveMap(dlg.GetPath())
			self.__addToRecentFiles(dlg.GetPath())
		dlg.Destroy()

	def onSwapImage(self, evt):
		defaultDir, defaultFile = self.defaultDirAndFile()
		wildcard = "All files (*.*)|*.*|"\
				 "BMP Image (*.bmp)|*.bmp|"\
				 "GIF Image (*.gif)|*.gif|" \
				 "JPEG Image (*.jpg)|*.jpg|" \
				 "PNG Image (*.png)|*.png"
		dlg = wx.FileDialog(self, 
							message="Select a Map Image", 
							defaultDir=defaultDir,
							defaultFile=defaultFile,
							wildcard=wildcard,
							style=wx.FD_OPEN | wx.FD_CHANGE_DIR)
		if (dlg.ShowModal() == wx.ID_OK):
			app = wx.GetApp()
			app.swapMapImage(dlg.GetPath())
		dlg.Destroy()

	def defaultDirAndFile(self):
		lastPath = wx.GetApp().lastSavePath
		if lastPath is None:
			return os.getcwd(), ""
		return os.path.split(lastPath)

	def onGridToggle(self, evt):
		self.panel.map.grid.visible = evt.IsChecked()

	def onGridVisibleUpdate(self, evt):		
		gridExists = self.hasGrid() and (self.panel.map.grid.type != data.Grid.GRID_NONE)
		evt.Enable(gridExists)
		evt.Check(gridExists and self.panel.map.grid.visible)

	def onGridSettings(self, evt):
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

	def onViewportChanged(self):
		"""Keep the toolbar in step however the overlay got toggled - button,
		   menu, or a setting read back from a map file."""
		active = (self.panel != None) and self.panel.showViewport
		self.viewportToggle.SetValue(active)
		# The overlay takes over the mouse, so the brush is unavailable.
		self.brushType.Enable(not active)
		self.brushSize.Enable(not active)

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

	def onBrushTypeChanged(self, evt):
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

	def __addToRecentFiles(self, path):
		if path in self.recentFiles:
			self.recentFiles.remove(path)
		self.recentFiles.insert(0, path)
		self.__rebuildRecentFilesMenu()
		self.__writeRecentPaths()

	def __readRecentPaths(self):
		self.recentFiles = []
		config = wx.Config("fogmap")
		config.SetPath("/RecentFiles")
		more, value, index = config.GetFirstEntry()
		while more:
			path = config.Read(value)
			self.recentFiles.append(path)
			more, value, index = config.GetNextEntry(index)

	def __writeRecentPaths(self):
		config = wx.Config("fogmap")
		config.DeleteGroup("/RecentFiles")
		config.SetPath("/RecentFiles")
		for index, path in enumerate(self.recentFiles):
			config.Write(str(index), path)
		config.Flush()

	def __rebuildRecentFilesMenu(self):
		items = self.recentFilesMenu.GetMenuItems()
		for item in items:
			self.Unbind(wx.EVT_MENU, id=item.GetId())
			self.recentFilesMenu.Remove(item)
		for idx, path in enumerate(self.recentFiles):
			menuId = 301 + idx
			self.__createRecentFileMenuItem(menuId, path)

	def __createRecentFileMenuItem(self, menuId, path):
		self.recentFilesMenu.Append(menuId, path)
		self.Bind(wx.EVT_MENU, lambda evt: self.onFileOpenRecent(evt, path), id=menuId)

	