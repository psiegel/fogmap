import argparse
import os
import wx
import wx.adv
from lxml import etree

from . import data
from . import resources
from . import ui
from . import __version__


class FogMapApp(wx.App):
	"""Holds the project and the one document currently being looked at.

	   Everything else in the project stays on disk: a map with unsaved changes
	   is flushed to a temp copy when the GM switches away from it, so a session
	   spent jumping between big maps costs one map's worth of memory rather
	   than all of them."""

	# Class defaults, so the update-UI handlers the frames install can safely
	# run before __init__ has finished.
	project = None
	doc = None
	lastSavePath = None
	dirtyShown = False
	dockIcon = None
	whiteboard = None
	boardTimer = None

	# How often the fading of the whiteboard is stepped on.  Often enough to
	# read as a fade rather than as a stutter, and running only while there is
	# something on its way out.
	BOARD_TICK_MS = 66

	def __init__(self, file=None, project=None):
		super(FogMapApp, self).__init__(0)
		if (project is not None):
			self.openProject(project)
		if (file is not None):
			self.activateDocument(file)

	def OnInit(self):
		self.__setDockIcon()

		self.playerFrame = ui.PlayerFrame(None, -1, "Player View", size=(800, 600))
		self.__showPlayerScreen(self.playerFrame)

		self.gmFrame = ui.GMFrame(None, -1, "GM View", size=(800, 600))
		self.gmFrame.Show(True)

		self.gmFrame.panel.setPlayerPanel(self.playerFrame.panel)
		self.playerFrame.panel.setUserViewListener(self.onPlayerViewChanged)

		# One drawing layer, shown by both windows and belonging to neither, so
		# that a stroke the GM makes is already on the players' screen.  It is
		# no part of a map: nothing here is ever written to a file, and it is
		# wiped when another map is opened.
		self.whiteboard = data.Whiteboard()
		self.whiteboard.setTickListener(self.__wakeBoardClock)
		self.gmFrame.panel.setWhiteboard(self.whiteboard)
		self.playerFrame.panel.setWhiteboard(self.whiteboard)
		self.boardTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.onBoardTick, self.boardTimer)

		return True

	# --- the whiteboard -------------------------------------------------------

	def __wakeBoardClock(self):
		"""Something on the board has gained a deadline, so the clock has work
		   to do again."""
		if ((self.boardTimer is not None) and (not self.boardTimer.IsRunning())):
			self.boardTimer.Start(FogMapApp.BOARD_TICK_MS)

	def onBoardTick(self, evt):
		# Stopped the moment nothing is left on a deadline, so a board that is
		# empty, or set never to fade, costs nothing at all.
		if (not self.whiteboard.tick()):
			self.boardTimer.Stop()

	def __showPlayerScreen(self, frame):
		display = self.__playerDisplay()
		if (display is not None):
			frame.SetSize(display.GetClientArea())
		frame.Show(True)
		if (display is not None):
			frame.Maximize(True)

	def __playerDisplay(self):
		"""The first display that is not the primary one, or None."""
		for i in range(wx.Display.GetCount()):
			display = wx.Display(i)
			if (not display.IsPrimary()):
				return display
		return None

	def __setDockIcon(self):
		"""On the Mac the icon belongs to the process rather than to any window,
		   so the frames' own SetIcons does nothing and the Dock shows a generic
		   Python icon.  This replaces it for the life of the run; a Finder icon
		   needs a real .app bundle built around resources/fogmap.icns."""
		if (wx.Platform != "__WXMAC__"):
			return
		icon = resources.largestIcon()
		if (icon is None):
			return
		# Held onto: collecting the TaskBarIcon takes the Dock tile with it.
		self.dockIcon = wx.adv.TaskBarIcon(wx.adv.TBI_DOCK)
		self.dockIcon.SetIcon(icon)

	def OnExit(self):
		if (self.boardTimer is not None):
			self.boardTimer.Stop()
		# wx complains if a TaskBarIcon outlives the app.
		if (self.dockIcon is not None):
			self.dockIcon.Destroy()
			self.dockIcon = None
		return super(FogMapApp, self).OnExit()

	# --- projects -------------------------------------------------------------

	def openProject(self, path):
		if (not self.closeProject()):
			return False

		project = data.Project(path)
		# A clean exit always empties .fogmap/, so anything still in there was
		# left behind by a crash.
		leftovers = project.findLeftoverTemps()
		if (leftovers):
			if (self.__confirmRestore(leftovers)):
				project.adoptTemps(leftovers)
			else:
				project.discardTemps()

		# Maps still holding the old two-mask fog are marked unsaved here, so
		# one Save All converts the whole folder.  Reads only each file's head.
		project.markLegacyMaps()

		self.project = project
		if (self.doc is not None):
			self.doc.project = project
			if (self.doc.map.legacyFormat and (self.doc.path is not None)):
				# Already open, so saving the document is what converts it.
				# Leaving the project's own entry would count it twice in the
				# unsaved-changes prompt and write it twice on Save All.
				project.takeOver(self.doc.path)
		self.gmFrame.setProject(project)
		return True

	def closeProject(self):
		"""Returns False if the GM cancelled out of the unsaved changes prompt.

		   The open document stays open, just no longer part of a project."""
		if (self.project is None):
			return True
		if (not self.confirmDiscardChanges()):
			return False
		self.project = None
		if (self.doc is not None):
			self.doc.project = None
		self.gmFrame.setProject(None)
		return True

	# --- documents ------------------------------------------------------------

	def activateDocument(self, path):
		path = os.path.abspath(path)
		if ((self.doc is not None) and (self.doc.path is not None) and
			(os.path.abspath(self.doc.path) == path)):
			return True
		if (not os.path.exists(path)):
			self.__error("%s no longer exists." % path, "File Not Found")
			self.gmFrame.onDocumentChanged()
			return False

		if (not self.__confirmLeavingUntitled()):
			self.gmFrame.onDocumentChanged()
			return False

		# Capture before opening: the panels still hold the outgoing document's
		# view, and opening can fail without having disturbed anything.
		self.captureSettings()
		try:
			doc = data.Document.open(path, self.project)
		except Exception as err:
			self.__error("Could not open %s:\n\n%s" % (path, err), "Open Failed")
			self.gmFrame.onDocumentChanged()
			return False

		self.__releaseDocument()
		self.__installDocument(doc)
		return True

	def newMap(self, imagePath):
		if (not self.__confirmLeavingUntitled()):
			return False
		self.captureSettings()
		try:
			doc = data.Document.createNew(imagePath, self.project)
		except Exception as err:
			self.__error("Could not read %s:\n\n%s" % (imagePath, err), "New Map Failed")
			return False
		self.__releaseDocument()
		self.__installDocument(doc)
		return True

	def swapMapImage(self, imagePath):
		if ((self.doc is None) or (not self.doc.editable)):
			return
		try:
			self.doc.map.replaceImage(imagePath)
		except Exception as err:
			self.__error("Could not read %s:\n\n%s" % (imagePath, err), "Swap Image Failed")
			return
		# The panels cache the image, so they have to be rebuilt around it.
		self.playerFrame.setMap(self.doc.map)
		self.gmFrame.setMap(self.doc.map)
		self.noteDirty()

	def __installDocument(self, doc):
		# The whiteboard is drawn in map pixels, and means nothing over any map
		# but the one it was drawn on.  It goes no further than that map, and
		# never onto disk.
		if (self.whiteboard is not None):
			self.whiteboard.clear()
		self.doc = doc
		self.dirtyShown = False
		self.playerFrame.setMap(doc.map)
		self.gmFrame.setMap(doc.map)
		doc.map.addUpdateListener(self.noteDirty)
		if ((self.project is not None) and (doc.path is not None)):
			# The document now owns whatever was outstanding for this file.  Its
			# temp copy is left on disk until the next flush replaces it, so a
			# crash while it is open still has something to recover.
			self.project.takeOver(doc.path)
		self.__applySettings(doc)
		if (doc.path is not None):
			self.lastSavePath = doc.path
		self.gmFrame.onDocumentChanged()

	def __releaseDocument(self):
		"""Push the open document's changes out to disk, or to the project's
		   memory of where its view was, and let go of its pixels."""
		doc = self.doc
		if (doc is None):
			return
		if ((self.project is not None) and self.project.contains(doc.path)):
			self.project.remember(doc.path, doc.settings)
			if (doc.map.contentDirty):
				try:
					self.project.writeTemp(doc.path, doc.map, doc.settings)
				except OSError as err:
					self.__error("Could not hold onto unsaved changes to %s:\n\n%s"
								 % (doc.name, err), "Save Failed")
			elif (doc.viewDirty):
				# Nothing but the player view moved, so there is no mask data
				# worth writing; the settings are the whole of the change.
				self.project.markViewDirty(doc.path, doc.settings)
		doc.map.removeUpdateListener(self.noteDirty)
		self.doc = None

	def __confirmLeavingUntitled(self):
		"""A new map that has never been saved has no file to be flushed to."""
		doc = self.doc
		if ((doc is None) or (doc.path is not None) or (not doc.isDirty())):
			return True
		dlg = wx.MessageDialog(self.gmFrame,
							   "The new map has not been saved yet, and cannot be "
							   "kept in the background.\n\nSave it now?",
							   "Unsaved New Map",
							   wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)
		dlg.SetYesNoCancelLabels("Save", "Discard", "Cancel")
		result = dlg.ShowModal()
		dlg.Destroy()
		if (result == wx.ID_YES):
			self.gmFrame.onFileSaveAs(None)
			return self.doc.path is not None
		return result == wx.ID_NO

	# --- saving ---------------------------------------------------------------

	def saveDocument(self, path=None):
		doc = self.doc
		if ((doc is None) or (not doc.editable)):
			return False
		target = path if (path is not None) else doc.path
		if (target is None):
			return False

		self.captureSettings()
		try:
			doc.write(target)
		except (OSError, IOError) as err:
			self.__error("Could not save %s:\n\n%s" % (target, err), "Save Failed")
			return False

		oldPath = doc.path
		doc.path = os.path.abspath(target)
		doc.markClean()
		self.dirtyShown = False
		self.lastSavePath = doc.path

		if (self.project is not None):
			if (oldPath is not None):
				self.project.clearDirty(oldPath)
			self.project.clearDirty(doc.path)
			self.project.remember(doc.path, doc.settings)
			if (oldPath != doc.path):
				# Saved somewhere new, which may have put a file in the tree.
				self.gmFrame.refreshProjectTree()
		self.gmFrame.onDocumentChanged()
		return True

	def saveAll(self):
		"""Commit the open document plus every other map holding changes."""
		if ((self.doc is not None) and self.doc.editable and self.doc.isDirty()):
			if (self.doc.path is None):
				self.gmFrame.onFileSaveAs(None)
			else:
				self.saveDocument()
		if (self.project is not None):
			try:
				self.project.commitAll()
			except (OSError, IOError) as err:
				self.__error("Could not save every map:\n\n%s" % err, "Save All Failed")
		self.gmFrame.refreshDirtyMarks()

	def hasUnsavedChanges(self):
		return (((self.doc is not None) and self.doc.isDirty()) or
				((self.project is not None) and (self.project.dirtyCount() > 0)))

	def confirmDiscardChanges(self):
		"""Returns False only if the GM wants to stay where they are."""
		if (not self.hasUnsavedChanges()):
			return True

		count = self.project.dirtyCount() if (self.project is not None) else 0
		if ((self.doc is not None) and self.doc.isDirty()):
			count += 1
		dlg = wx.MessageDialog(self.gmFrame,
							   "%d map%s unsaved changes." %
							   (count, " has" if (count == 1) else "s have"),
							   "Unsaved Changes",
							   wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)
		dlg.SetYesNoCancelLabels("Save All", "Discard", "Cancel")
		result = dlg.ShowModal()
		dlg.Destroy()

		if (result == wx.ID_YES):
			self.saveAll()
			return not self.hasUnsavedChanges()
		if (result == wx.ID_NO):
			if (self.doc is not None):
				self.doc.markClean()
			if (self.project is not None):
				self.project.discardTemps()
			self.dirtyShown = False
			return True
		return False

	# --- change tracking ------------------------------------------------------

	def onPlayerViewChanged(self):
		"""Where the players are looking is part of what a map file holds, so
		   moving it counts as a change worth keeping."""
		if ((self.doc is None) or (not self.doc.editable) or self.doc.viewDirty):
			return
		self.doc.viewDirty = True
		self.noteDirty()

	def noteDirty(self, rect=None):
		"""Mark the document modified in the tree and title bar, once.

		   rect is which part of the map changed, which matters to the panels
		   but not here."""
		if (self.dirtyShown or (self.doc is None) or (not self.doc.isDirty())):
			return
		self.dirtyShown = True
		self.gmFrame.refreshDirtyMarks()

	# --- settings -------------------------------------------------------------

	def captureSettings(self):
		"""Take the player view and the GM's overlay state off the panels and
		   onto the document, so they come back when the GM does."""
		if (self.doc is None):
			return
		settings = etree.Element("settings")
		self.writeSettings(settings)
		self.doc.settings = settings

	def __applySettings(self, doc):
		if (doc.settings is not None):
			self.readSettings(doc.settings)
		elif (not doc.editable):
			# A handout the GM has not looked at yet: show the players all of it.
			wx.CallAfter(self.fitPlayerView, False)

	def fitPlayerView(self, user=True):
		if (self.doc is None):
			return
		w, h = self.doc.map.size
		self.playerFrame.panel.showMapRect((0, 0, w, h), user)

	def readSettings(self, settings):
		for child in settings:
			if ((child.tag == "player") and (self.playerFrame != None)):
				self.playerFrame.panel.readSettings(child)
			elif ((child.tag == "gm") and (self.gmFrame != None)):
				self.gmFrame.panel.readSettings(child)

	def writeSettings(self, settings):
		playerSettings = etree.Element("player")
		if (self.playerFrame != None):
			self.playerFrame.panel.writeSettings(playerSettings)
		settings.append(playerSettings)

		gmSettings = etree.Element("gm")
		if (self.gmFrame != None):
			self.gmFrame.panel.writeSettings(gmSettings)
		settings.append(gmSettings)

	# --- internals ------------------------------------------------------------

	def __confirmRestore(self, leftovers):
		shown = "\n".join("    " + rel for rel in leftovers[:10])
		if (len(leftovers) > 10):
			shown += "\n    ...and %d more" % (len(leftovers) - 10)
		dlg = wx.MessageDialog(self.gmFrame,
							   "fogmap did not shut down cleanly.  Unsaved changes "
							   "were found for:\n\n%s\n\nRestore them?  Choosing No "
							   "throws them away and opens the saved versions."
							   % shown,
							   "Restore Unsaved Changes",
							   wx.YES_NO | wx.ICON_QUESTION)
		result = dlg.ShowModal()
		dlg.Destroy()
		return result == wx.ID_YES

	def __error(self, message, title):
		dlg = wx.MessageDialog(self.gmFrame, message, title, wx.OK | wx.ICON_ERROR)
		dlg.ShowModal()
		dlg.Destroy()


def main(argv=None):
	parser = argparse.ArgumentParser(prog='fogmap', description='Fog of war map tool.')
	parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
	parser.add_argument('-f', '--file', dest='file', default=None, metavar='FILE', help='Map file to open')
	parser.add_argument('-p', '--project', dest='project', default=None, metavar='DIR', help='Project folder to open')
	options = parser.parse_args(argv)

	app = FogMapApp(options.file, options.project)
	app.MainLoop()
	return 0
