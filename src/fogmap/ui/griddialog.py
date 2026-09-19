"""The grid settings dialog.

   What a grid is made of is the grid's own business: the dialog asks the type
   the GM has picked which settings it has and builds a field for each one, so
   a new kind of grid with different measurements needs nothing here.  See
   data.doc.grid for the options themselves."""
import wx

from ..data import doc

from .numericfield import HGAP, VGAP, NumericField


class GridDialog(wx.Dialog):
	def __init__(self, grid, *args, **kwargs):
		super(GridDialog, self).__init__(*args, **kwargs)

		self.grid = grid
		self.grid.visible = True
		self.fields = {}

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

		# The settings the chosen type has, on a panel of their own: changing
		# type throws the whole lot away and builds the next type's instead.
		self.optionsPanel = self.__buildOptions()
		self.sizer.Add(self.optionsPanel, 0, wx.GROW|wx.ALL, 5)

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

	def __buildOptions(self):
		"""A panel of fields, one per setting the current grid type has.  A
		   type with nothing to set - no grid at all - gets an empty one, which
		   takes up no room."""
		panel = wx.Panel(self, -1)
		sizer = wx.FlexGridSizer(cols=3, vgap=VGAP, hgap=HGAP)
		# The sliders take whatever width is going; the labels and the boxes
		# they are typed into keep theirs.
		sizer.AddGrowableCol(2, 1)

		self.fields = {}
		for option in self.grid.options:
			field = NumericField(panel, sizer, option.label,
								 self.grid.getOption(option.key),
								 option.minValue, option.maxValue, option.step,
								 option.tip,
								 lambda value, key=option.key:
									 self.onOptionChanged(key, value))
			self.fields[option.key] = field

		panel.SetSizer(sizer)
		return panel

	def onTypeChanged(self, evt):
		self.grid.type = self.gridType.GetStringSelection()

		# The new type's settings are not the old one's, so the fields go with
		# it.  The dialog is resized to whatever the new set needs.
		panel = self.__buildOptions()
		self.sizer.Replace(self.optionsPanel, panel)
		self.optionsPanel.Destroy()
		self.optionsPanel = panel
		self.Layout()
		self.sizer.Fit(self)

	def onOptionChanged(self, key, value):
		# Straight onto the grid, which repaints both windows as it goes: the
		# point of the dialog is seeing the grid land on the map while it is
		# being set.  Cancel puts back the copy the caller kept.
		self.grid.setOption(key, value)
