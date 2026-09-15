"""What the mouse does over the GM map, and what the toolbar offers while it
   is doing it.

   The left-most controls on the toolbar pick the mode: one icon each, as a
   group of radio tools.  The panel routes its mouse events to whichever one is
   current and lets it draw over the map; the toolbar shows that mode's own
   controls and hides the rest.

   PlayerDriveMode is the odd one out: it is not on the switcher, because it
   lasts only as long as Alt is held.  The panel hands it the mouse for that
   long and then gives it straight back.
"""
from .drawmode import DrawMode
from .fogmode import FogMode
from .inputmode import (BORDER, IconRadioGroup, InputMode, addIcon,
						addIconButton)
from .playerdrivemode import PlayerDriveMode
from .viewportmode import ViewportMode

# What the switcher offers, in the order it offers them.  The first is the
# mode a map opens in unless its file says otherwise.
MODES = (FogMode, ViewportMode, DrawMode)

__all__ = ["BORDER", "DrawMode", "FogMode", "IconRadioGroup", "InputMode",
		   "MODES", "PlayerDriveMode", "ViewportMode", "addIcon",
		   "addIconButton"]
