"""Projects: a folder of maps and images the GM can click between.

Only the document being looked at is held in memory.  A map with unsaved
changes is flushed to a temp copy under <root>/.fogmap/ when the GM switches
away from it, in exactly the same format as a real map file, so bringing it
back is a plain parse and committing it is a plain file copy.

Because a clean exit always empties .fogmap/, anything found in there when a
project is opened is left over from a crash.
"""
from .dirtyentry import DirtyEntry
from .document import Document
from .mapfile import (isLegacyMapFile, readImagePaths, readMapFile,
					  spliceSettings, upgradeMapFile, writeMapFile)
from .node import Node
from .paths import (IMAGE_EXTS, MAP_EXTS, isImagePath, isMapPath,
					isProjectFile)
from .project import TEMP_DIR_NAME, Project

__all__ = ["DirtyEntry", "Document", "IMAGE_EXTS", "MAP_EXTS", "Node",
		   "Project", "TEMP_DIR_NAME", "isImagePath", "isLegacyMapFile",
		   "isMapPath", "isProjectFile", "readImagePaths", "readMapFile",
		   "spliceSettings", "upgradeMapFile", "writeMapFile"]
