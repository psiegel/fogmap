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
| `Ctrl+B` | Show or hide the player viewport (suspends the brush) |
| Drag, viewport shown | Move the players' visible area |
| Drag an edge / corner, viewport shown | Resize the players' visible area |
| `Ctrl+0` | Zoom the Player View out to the whole map |
| Toolbar | Brush type (None / Round / Square / Grid) and size |
| **Player Viewport** button | Toggle player viewport mode (same as `Ctrl+B`) |
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

## The player viewport outline

The **Player Viewport** button on the toolbar, **View > Show Player Viewport**, and
`Ctrl+B` all do the same thing and stay in step with each other. It is off by
default. When on, the GM map is overlaid with a cyan
rectangle marking exactly what the players can currently see, with a handle on
each corner and edge.

The rectangle is never stored anywhere. It is derived from the Player View's own
zoom and pan every time it is drawn, so it cannot fall out of sync with what the
players are looking at, and it updates live as the view moves.

While it is on, the overlay owns the mouse and **the brush is suspended** - the
brush controls grey out, and no click will paint or un-paint the fog. Instead:

- **Drag anywhere** to move the players' visible area. The rectangle follows the
  cursor one-for-one and the zoom is untouched. The cursor is a hand to show this.
- **Drag an edge or corner** to resize it. The cursor becomes a resize arrow.

Either drag runs the derivation backwards: the new rectangle is fitted to the
Player View, which is the same as zooming and panning to frame it. A resize always
holds the opposite edge or corner still, and the result is locked to the aspect
ratio of the player window, so the players never see bars or a stretched map. A
corner follows whichever axis you dragged further. Resizing is bounded by the same
zoom limits as the mouse wheel, so a handle cannot be dragged past them.

Switch the overlay off to get the brush back. The setting starts off and is saved
with the map.

## File format

A `.map` file is XML holding a *path* to the map image plus the two reveal masks
(base64 PNG-less raw bytes), plus the Player View's zoom and pan and the GM's
overlay setting. The image itself is not embedded, so moving a map between
machines means keeping the image at the same path, or using **Swap Image** to
re-point it.
