"""The whiteboard the GM draws on over the map, and the strokes on it.

   Ephemeral by design: none of this is saved with a map, and all of it is
   thrown away when another map is opened or the application closes."""
from .stroke import Stroke
from .whiteboard import Whiteboard

__all__ = ["Stroke", "Whiteboard"]
