"""The grid settings dialog: a kind of grid to pick, and that kind's own
   settings underneath it.

   A grid never changes its kind - picking another one makes a new grid and
   hands it to the map.  What the settings are is the panel's business; see
   ui.gridpanels."""
import wx

from ..data import doc

from .gridpanels import GridSettingsPanel, HexGridPanel, SquareGridPanel


class GridDialog(wx.Dialog):
	# Which panel goes with which kind of grid.  A kind not listed gets the
	# bare one, which has nothing on it: a map with no grid has nothing to set.
	PANELS = {
		doc.SquareGrid: SquareGridPanel,
		doc.HexGrid: HexGridPanel,
	}

	def __init__(self, grid, setGrid, *args, **kwargs):
		"""setGrid is how a grid of another kind reaches the map it belongs
		   to, since picking one is not something the grid in hand can do to
		   itself."""
		super(GridDialog, self).__init__(*args, **kwargs)		
		
		self.grid = grid
		self.setGrid = setGrid
		self.grid.visible = True
		# The grids made while this dialog has been open, by kind.  Trying
		# hexes and going back to squares finds the squares as they were left,
		# and they go no further than here: the map holds the one grid it has,
		# and that is all its file has ever held.
		self.grids = {grid.type: grid}
		
		self.__layoutUI()
		
	def __layoutUI(self):
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		
		label = wx.StaticText(self, -1, "Grid Settings")
		self.sizer.Add(label, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
		
		box = wx.BoxSizer(wx.HORIZONTAL)		
		label = wx.StaticText(self, -1, "Grid Type:")
		box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
		
		gridTypes = [doc.Grid.GRID_NONE, doc.Grid.GRID_SQUARE, doc.Grid.GRID_HEX]
		self.gridType = wx.Choice(self, -1, (100, 50), choices=gridTypes)
		self.gridType.SetStringSelection(self.grid.type)
		self.Bind(wx.EVT_CHOICE, self.onTypeChanged, self.gridType)
		box.Add(self.gridType, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
		
		self.sizer.Add(box, 0, wx.GROW|wx.ALL, 5)
		
		self.settings = self.__settingsPanel()
		self.sizer.Add(self.settings, 0, wx.GROW|wx.ALL, 5)
		
		btnsizer = wx.StdDialogButtonSizer()
		
		btn = wx.Button(self, wx.ID_OK)
		btn.SetDefault()
		btnsizer.AddButton(btn)
		
		btn = wx.Button(self, wx.ID_CANCEL)
		btnsizer.AddButton(btn)
		btnsizer.Realize()
		
		self.sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
		
		self.SetSizer(self.sizer)
		self.sizer.Fit(self)
		
	def __settingsPanel(self):
		panelClass = GridDialog.PANELS.get(type(self.grid), GridSettingsPanel)
		return panelClass(self, self.grid)
		
	def onTypeChanged(self, evt):
		self.grid = self.__gridOfType(self.gridType.GetStringSelection())
		self.grid.visible = True
		# Onto the map, which draws the new grid in place of the old one.
		self.setGrid(self.grid)
		
		# Its settings are not the last kind's, so the whole panel goes with
		# it.  The dialog is resized to whatever the new one needs.
		panel = self.__settingsPanel()
		self.sizer.Replace(self.settings, panel)
		self.settings.Destroy()
		self.settings = panel
		self.Layout()
		self.sizer.Fit(self)
		
	def __gridOfType(self, type):
		grid = self.grids.get(type)
		if (grid is None):
			grid = doc.gridForType(type)
			self.grids[type] = grid
		return grid
