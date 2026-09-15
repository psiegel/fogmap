import wx

from ..data import doc

class GridDialog(wx.Dialog):
	def __init__(self, grid, *args, **kwargs):
		super(GridDialog, self).__init__(*args, **kwargs)		
		
		self.grid = grid
		self.grid.visible = True
		
		self.__layoutUI()
		
	def __layoutUI(self):
		sizer = wx.BoxSizer(wx.VERTICAL)
		
		label = wx.StaticText(self, -1, "Grid Settings")
		sizer.Add(label, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
		
		box = wx.BoxSizer(wx.HORIZONTAL)		
		label = wx.StaticText(self, -1, "Grid Type:")
		box.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
		
		gridTypes = [doc.Grid.GRID_NONE, doc.Grid.GRID_SQUARE, doc.Grid.GRID_HEX]
		self.gridType = wx.Choice(self, -1, (100, 50), choices=gridTypes)
		self.gridType.SetStringSelection(self.grid.type)
		self.Bind(wx.EVT_CHOICE, self.onTypeChanged, self.gridType)
		box.Add(self.gridType, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
		
		sizer.Add(box, 0, wx.GROW|wx.ALL, 5)
		
		label = wx.StaticText(self, -1, "Grid Size:")
		sizer.Add(label, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
		
		self.slider = wx.Slider(self, -1, self.grid.size, 10, 256, style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
		self.slider.SetTickFreq(5)
		self.Bind(wx.EVT_SLIDER, self.onSizeChanged, self.slider)
		sizer.Add(self.slider, 0, wx.GROW|wx.ALL, 5)
		
		btnsizer = wx.StdDialogButtonSizer()
		
		btn = wx.Button(self, wx.ID_OK)
		btn.SetDefault()
		btnsizer.AddButton(btn)
		
		btn = wx.Button(self, wx.ID_CANCEL)
		btnsizer.AddButton(btn)
		btnsizer.Realize()
		
		sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
		
		self.SetSizer(sizer)
		sizer.Fit(self)
		
	def onTypeChanged(self, evt):
		self.grid.type = self.gridType.GetStringSelection()
	
	def onSizeChanged(self, evt):
		# Less than 4 pixels is really too small, plus hexes require increments of 4.
		self.grid.size = self.slider.GetValue()
