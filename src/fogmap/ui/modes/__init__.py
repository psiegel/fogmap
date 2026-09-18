"""What the mouse does over the GM map, and what the toolbar offers while it
   is doing it.

   The left-most controls on the toolbar pick the mode: one icon each, as a
   group of radio tools.  The panel routes its mouse events to whichever one is
   current and lets it draw over the map; the toolbar shows that mode's own
   controls and hides the rest.

   Two of them paint a mask with a brush and share all of that in BrushMode:
   Fog mode decides what the players can see, Secret mode which of the map's
   two images they see it from.

   One mode is also lent out: holding Alt hands the mouse to ViewportMode from
   wherever the toolbar has it, for exactly as long as the key is down.  Which
   mode that is, is the frame's to say - the panel only knows that it has one
   to borrow.
"""
from .brushmode import BrushMode
from .drawmode import DrawMode
from .fogmode import FogMode
from .inputmode import (BORDER, IconRadioGroup, InputMode, addIcon,
						addIconButton)
from .secretmode import SecretMode
from .viewportmode import ViewportMode

# What the switcher offers, in the order it offers them.  The first is the
# mode a map opens in unless its file says otherwise.
# The two brushes first, since they are what the mouse is doing most of an
# evening, then the pen, and the viewport last - it is the one the toolbar
# matters least for, being a key-hold away from wherever you already are.
# Ctrl+Shift+1 to 4 follow the same order, so a button's place on the row and
# the number that picks it never disagree.
MODES = (FogMode, SecretMode, DrawMode, ViewportMode)

__all__ = ["BORDER", "BrushMode", "DrawMode", "FogMode", "IconRadioGroup",
		   "InputMode", "MODES", "SecretMode", "ViewportMode", "addIcon",
		   "addIconButton"]
