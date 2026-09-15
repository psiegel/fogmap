"""What the mouse does over the GM map, and what the toolbar offers while it
   is doing it.

   The left-most control on the toolbar picks the mode.  The panel routes its
   mouse events to whichever one is current and lets it draw over the map; the
   toolbar shows that mode's own controls and hides the rest.

   PlayerDriveMode is the odd one out: it is not on the switcher, because it
   lasts only as long as Alt is held.  The panel hands it the mouse for that
   long and then gives it straight back.
"""
from .fogmode import FogMode
from .inputmode import BORDER, InputMode, addLabel
from .playerdrivemode import PlayerDriveMode
from .viewportmode import ViewportMode

# What the switcher offers, in the order it offers them.  The first is the
# mode a map opens in unless its file says otherwise.
MODES = (FogMode, ViewportMode)

__all__ = ["BORDER", "FogMode", "InputMode", "MODES", "PlayerDriveMode",
		   "ViewportMode", "addLabel"]
