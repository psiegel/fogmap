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
| Toolbar | Brush type (None / Round / Square / Grid) and size |
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+A` | New / Open / Save / Save As |
| `Ctrl+W` | Swap the underlying image, keeping the revealed mask |
| Grid menu | Toggle the grid and change its type (None / Square / Hex) and size |

The Grid brush follows whichever grid is enabled, so it reveals whole squares or
whole hexes. It is only selectable while a grid is active.

**Player View**

| Action | Effect |
| --- | --- |
| Mouse wheel, `PageUp` / `PageDown` | Zoom |
| Right drag | Pan |
| Right double-click | Recentre |
| Arrow keys | Pan one grid cell (hold `Shift` for one pixel) |
| `Ctrl+F` | Mirror horizontally, for projecting onto a table from below |
| Double-click | Toggle full screen |

The GM window forwards key presses to the Player View, so the GM can zoom and pan
what the players see without leaving their own window.

## File format

A `.map` file is XML holding a *path* to the map image plus the two reveal masks
(base64 PNG-less raw bytes). The image itself is not embedded, so moving a map
between machines means keeping the image at the same path, or using
**Swap Image** to re-point it.
