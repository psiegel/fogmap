# fogmap

A fog-of-war map tool for tabletop games. It opens two windows:

- **Player View** — the map as the players see it, with unrevealed areas blacked out.
  Intended for a second monitor or projector.
- **GM View** — the full map at half brightness, where the GM paints areas to reveal
  or re-hide with the mouse.

## Setup

Requires Python 3.9+ (developed against 3.11).

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```sh
source .venv/bin/activate
python app.py                # start empty; use File > New to pick a map image
python app.py -f test.map    # open an existing .map file
```

## Controls

**GM View**

| Action | Effect |
| --- | --- |
| Left click / drag | Reveal with the current brush |
| Right click / drag | Re-hide with the current brush |
| Shift / Ctrl while dragging | Lock the brush to one axis |
| **Hold Alt** | Drive the Player View with the mouse instead of the brush |
| Alt + drag (either button) | Pan the Player View |
| Alt + wheel | Zoom the Player View about the map point under the cursor |
| Alt + right double-click | Recentre the Player View |
| Toolbar | Brush type (None / Round / Square / Grid) and size |
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+A` | New / Open / Save / Save As |
| `Ctrl+W` | Swap the underlying image, keeping the revealed mask |
| Grid menu | Toggle the grid and change its type (None / Square / Hex) and size |

The Grid brush follows whichever grid is enabled, so it reveals whole squares or
whole hexes. It is only selectable while a grid is active.

**Player View**

| Action | Effect |
| --- | --- |
| Mouse wheel | Zoom about the point under the cursor |
| `PageUp` / `PageDown` | Zoom about the centre of the view |
| Right drag | Pan; the map follows the cursor |
| Right double-click | Recentre |
| Arrow keys | Pan one grid cell (hold `Shift` for one pixel) |
| `Ctrl+F` | Mirror horizontally, for projecting onto a table from below |
| Double-click | Toggle full screen |

The GM window forwards key presses to the Player View, so the GM can zoom and pan
what the players see without leaving their own window. Holding **Alt** forwards the
mouse as well: the brush is suspended, the cursor turns into a hand, and dragging or
scrolling over the GM map pans and zooms what the players are looking at. Because the
GM map is drawn 1:1, Alt + wheel zooms the Player View around whichever map feature
the GM is pointing at.

## File format

A `.map` file is XML holding a *path* to the map image plus the two reveal masks
(base64 PNG-less raw bytes). The image itself is not embedded, so moving a map
between machines means keeping the image at the same path, or using
**Swap Image** to re-point it.
