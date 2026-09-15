import wx

from ... import resources


class MapPanelFrame(wx.Frame):	
	# A class default, so the update-UI handlers a frame installs can safely
	# run before its panel has been built.
	panel = None

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
