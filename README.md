# fogmap

A fog-of-war map tool for tabletop games. It opens two windows:

- **Player View** — the map as the players see it, with unrevealed areas blacked out.
  Intended for a second monitor or projector.
- **GM View** — the full map at half brightness, where the GM paints areas to reveal
  or re-hide with the mouse, at whatever zoom suits the map.

## Layout

```
pyproject.toml         packaging and dependencies
requirements.txt       pinned versions of those dependencies
src/fogmap/            the application
  app.py                 the wx.App: holds the project and the open document
  gfx.py  hex.py         image helpers and hex geometry
  data/                  maps, masks, brushes, projects - no UI
  ui/                    frames, panels, the project tree, the toolbar
  resources/             the app icon, shipped inside the package
tests/data/            a sample map and its image
```

The app icon is `src/fogmap/resources/fogmap.png`, loaded by `fogmap.resources`
and set on both windows. On Windows and Linux that is the title-bar and taskbar
icon; macOS has no per-window icons, so the same image is put on the Dock tile
instead, for the life of the run. A Finder icon needs a bundled `.app` built
around a `.icns` - see `src/fogmap/resources/README.md`.

## Setup

Requires Python 3.9+ (developed against 3.11).

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # pinned versions
pip install -e .                  # then fogmap itself, editable
```

## Running

```sh
source .venv/bin/activate
fogmap                          # start empty; use File > New to pick a map image
fogmap -f tests/data/test.map   # open an existing .map file
fogmap -p ~/campaign            # open a folder of maps as a project
```

`python -m fogmap` does the same thing and takes the same options, for when you
would rather not install the console script.

## Projects

A project is just a folder of maps and images. **File > Open Project** puts a tree
of it down the left of the GM window, and clicking a file opens it:

- a `.map` or `.xml` file opens as a map, with its fog and its grid;
- an image (PNG, JPG, GIF, BMP, TIFF, WEBP) is shown to the players whole and
  **unmasked**, for handouts and battle maps that need no fog. The brush and the
  grid controls grey out, and there is nothing to save.

The GM can click back and forth freely. Unsaved fog stays put: switching away from
a map you have painted on keeps those changes, and clicking back returns the map
exactly as you left it, including where the Player View was pointing.

**Save** (`Ctrl+S`) writes the map you are looking at. **Save All**
(`Ctrl+Shift+S`) writes every map in the project that has unsaved changes, whether
or not it is the one on screen. Modified files are shown in bold with a `*`, both
in the tree and in the title bar.

### A map's image is nested under it

If a map's image sits in the same folder as the map, the tree tucks it underneath
the map rather than listing it alongside:

```
dungeon/
  dungeon.map            <- click this for the fogged map
    +-- dungeon.jpg      <- collapsed; expand to show the players the whole thing
  handout-letter.png     <- an image no map uses, listed normally
```

That is deliberate. Clicking the bare image would throw the entire unmasked map
onto the players' screen, so reaching it takes a decision rather than a stray
click. Expand the map and click the image when you really do want to show the
whole map at once.

Press `F5` over the tree to re-read the folder after adding files on disk.

### Unsaved changes and crashes

Only the map being looked at is held in memory - a big map is tens of megabytes,
and a session can cover a lot of them. When you switch away from a map with
unsaved fog, it is written to a temporary copy in a hidden `.fogmap/` folder at
the project root, in the same format as a real map file. Save All then just copies
those over the originals.

A clean exit always empties `.fogmap/`, so if fogmap is killed or crashes, the
copies left in there are offered back the next time that project is opened.

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
| `Ctrl+=` / `Ctrl+-` | Zoom the GM map in or out one level |
| `Ctrl+1` / `Ctrl+9` | GM map at 100% / zoomed out until all of it fits |
| `Ctrl` + wheel | Zoom the GM map about the point under the cursor |
| Toolbar | Brush type (None / Round / Square / Grid) and size, and the GM zoom |
| **Player Viewport** button | Toggle player viewport mode (same as `Ctrl+B`) |
| `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+A` | New / Open / Save / Save As |
| `Ctrl+Shift+O` / `Ctrl+Shift+S` | Open Project / Save All |
| `Ctrl+W` | Swap the underlying image, keeping the revealed mask |
| Click a file in the sidebar | Open it; `F5` re-reads the folder |
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
scrolling over the GM map pans and zooms what the players are looking at. Alt + wheel
zooms the Player View around whichever map feature the GM is pointing at, whatever
zoom the GM's own map happens to be at.

## Zooming the GM map

The **Zoom** box on the toolbar, the View menu and `Ctrl` + the wheel all set how
big the GM's own map is drawn, from 10% to 400%. It is entirely separate from the
Player View: changing it does not move, resize or otherwise touch what the players
are looking at. Zoom out to find your way around a map far larger than the window,
zoom in to paint a doorway one square at a time.

The zoom is a ladder of fixed levels rather than a free scale, so the toolbar box
always names exactly where the view is however it was last changed. **Fit Map to
Window** (`Ctrl+9`) picks the largest level that shows all of the map at once.

Zooming holds still whatever you were already looking at: the wheel keeps the point
under the cursor where it is, and the menu and the toolbar hold the centre of the
window. Everything else carries on working in map pixels, so the brush paints where
its cursor is at any zoom, and the player viewport outline stays a thin rectangle
with grabbable handles however far the map is zoomed out.

The level is saved with the map, so a map comes back at the zoom you left it at -
which, like moving the Player View, counts as a change worth saving.

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

A `.map` file is XML holding a *path* to the map image plus the reveal mask,
plus the Player View's zoom and pan and the GM's own zoom and overlay setting.
The image itself is not embedded.

The mask is one bit per pixel — set where the map shows through — packed,
deflated and base64'd. The two alphas the app actually draws with (transparent
or opaque for the players, dimmed or opaque for the GM) are both derived from
that single bit on the way to the screen, so they cannot drift apart.

Older map files hold the mask twice over, a byte per pixel each and
uncompressed, which is most of the weight of such a file — a 800×600 map came
to 1.3 MB where it now comes to well under a kilobyte. Those files are still
read, and **opening a project marks every one of them as unsaved**, so a single
**Save All** converts the whole folder. Maps that have not been opened are
converted straight on disk without their images ever being loaded, so a map
whose image has gone missing converts too.

The path is stored **relative to the `.map` file**, so a project folder can be
copied or moved between machines as a unit and its maps still find their images.
An image outside the project is stored relative too (`../../art/keep.jpg`), which
survives the project moving only if the image moves with it.

Older map files hold an absolute path. Those are still read as they stand, and are
converted to a relative one the next time that map is saved — so a map keeps
behaving exactly as it did until you save it. For an absolute path that has gone
stale, **Swap Image** re-points it.
