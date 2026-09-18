"""What the mouse does over the GM map, and what the toolbar offers while it
   is doing it.

   The left-most controls on the toolbar pick the mode: one icon each, as a
   group of radio tools.  The panel routes its mouse events to whichever one is
   current and lets it draw over the map; the toolbar shows that mode's own
   controls and hides the rest.

   One mode is also lent out: holding Alt hands the mouse to ViewportMode from
   wherever the toolbar has it, for exactly as long as the key is down.  Which
   mode that is, is the frame's to say - the panel only knows that it has one
   to borrow.
"""
from .drawmode import DrawMode
from .fogmode import FogMode
from .inputmode import (BORDER, IconRadioGroup, InputMode, addIcon,
						addIconButton)
from .viewportmode import ViewportMode

# What the switcher offers, in the order it offers them.  The first is the
# mode a map opens in unless its file says otherwise.
MODES = (FogMode, ViewportMode, DrawMode)

__all__ = ["BORDER", "DrawMode", "FogMode", "IconRadioGroup", "InputMode",
		   "MODES", "ViewportMode", "addIcon", "addIconButton"]
