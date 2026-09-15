import wx

from .. import mappanel

from .mappanelframe import MapPanelFrame


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
