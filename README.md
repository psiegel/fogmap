# fogmap

A fog-of-war map tool for tabletop games. It opens two windows:

- **Player View** — the map as the players see it, with unrevealed areas blacked out.
  Intended for a second monitor or projector.
- **GM View** — the full map at half brightness, where the GM paints areas to reveal
  or re-hide with the mouse, at whatever zoom suits the map.

There is also a whiteboard layer over both, for drawing on and pointing at the map
while the game is going on. Nothing drawn on it is ever saved.

## Layout

```
pyproject.toml         packaging and dependencies
requirements.txt       pinned versions of those dependencies
src/fogmap/            the application
  app.py                 the wx.App: holds the project and the open document
  gfx.py  hex.py         image helpers and hex geometry
  data/                  maps, masks, brushes, projects - no UI
    board/                 the whiteboard layer and the strokes on it
    brush/                 the shapes the GM paints fog with
    doc/                   a map: its image, its mask, its grid
    project/               a folder of maps, and the one open document
  ui/
    frames/                the two windows
    mappanel/              the player view and the GM's own view of a map
    modes/                 what the mouse is for, and the toolbar that goes with it
    grid/                  grids drawn over the map
    viewport.py            the player-viewport rectangle and its handles
    board.py               the whiteboard's strokes, and the GM's pointer
    projecttree.py         the sidebar
    griddialog.py          the grid settings dialog
  resources/             the app icon, shipped inside the package
tests/data/            a sample map and its image
```

Each of those packages holds one class per file, named for the class in lower
case, and re-exports them from its `__init__.py` - so callers say
`ui.modes.FogMode`, not `ui.modes.fogmode.FogMode`, and moving a class between
files is nobody else's business. Modules that are a set of functions rather
than a class - `gfx`, `hex`, `ui/viewport.py`, `ui/board.py` - stay single files.

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

### Modes

The three buttons at the left of the GM toolbar say what the mouse is for, and
exactly one of them is pressed at a time. Everything between them and the
**Zoom** box belongs to whichever mode is picked and changes with it; the zoom
past that is the GM's own and stays where it is.

The toolbar is icons and tooltips rather than captions and labelled drop-downs -
it is one row across the top of a window whose whole point is the map under it.
The mode buttons keep their names; everything else says what it is when the
mouse rests on it, and the menus spell all of it out in full.

| Mode | What the mouse does | Its own toolbar controls |
| --- | --- | --- |
| **Fog** | Reveals and re-hides the map with the brush | Brush shape and brush size |
| **Viewport** | Moves and resizes what the players can see | **Fit to Map** |
| **Draw** | Draws on the whiteboard layer, and points at the map | Colour, size, fade and **Clear** |

`Ctrl+Shift+1`, `Ctrl+Shift+2` and `Ctrl+Shift+3` pick them, as do
**View > Fog Mode**, **View > Viewport Mode** and **View > Draw Mode**.

Whichever mode is picked, **View > Show Player Viewport** (`Ctrl+B`) outlines
what the players can currently see - see [Seeing where the players are
looking](#seeing-where-the-players-are-looking).

The mode is saved with the map, so a map comes back the way it was left.

Holding **Alt** drops into Viewport mode whichever mode is selected: the overlay
comes up with the key and takes the mouse, so the players' view can be moved and
resized without putting the brush or the pen down, and the mode on the toolbar
gets the mouse back the moment the key comes up.

**GM View**

| Action | Effect |
| --- | --- |
| **Fog mode** | |
| Left click / drag | Reveal with the current brush |
| Right click / drag | Re-hide with the current brush |
| Shift / Ctrl while dragging | Lock the brush to one axis |
| Toolbar | Brush shape (none / round / square / grid) and size |
| **Viewport mode** | |
| Drag | Move the players' visible area |
| Drag an edge / corner | Resize the players' visible area |
| **Fit** button | Zoom the Player View out to the whole map (same as `Ctrl+0`) |
| **Draw mode** | |
| Move the mouse | The players see an arrow where the GM is pointing |
| Left drag | Draw on the whiteboard layer, in both views |
| Right click / drag | Rub out whatever the pen would have covered |
| Toolbar | Pen colour and size, how long a stroke lasts, and **Clear** |
| **Clear** button | Wipe the whole layer at once |
| **Any mode** | |
| `Ctrl+Shift+1` / `Ctrl+Shift+2` / `Ctrl+Shift+3` | Fog / Viewport / Draw mode |
| `Ctrl+B` | Outline what the players can see, or take the outline off again |
| **Hold Alt** | Viewport mode for as long as the key is down |
| Alt + drag (either button) | Move the players' visible area |
| Alt + drag an edge / corner | Resize the players' visible area |
| `Ctrl+0` | Zoom the Player View out to the whole map |
| `Ctrl+=` / `Ctrl+-` | Zoom the GM map in or out one level |
| `Ctrl+1` / `Ctrl+9` | GM map at 100% / zoomed out until all of it fits |
| `Ctrl` + wheel | Zoom the GM map about the point under the cursor |
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
what the players see without leaving their own window. The mouse does it a
different way: holding **Alt** over the GM map borrows Viewport mode for as long
as the key is down, whatever the toolbar is set to, and dragging the rectangle
that comes up moves and resizes what the players are looking at. See
[Viewport mode](#viewport-mode).

## Zooming the GM map

The **Zoom** box on the toolbar, the **&minus;** and **+** buttons either side of
it, the View menu and `Ctrl` + the wheel all set how big the GM's own map is
drawn, from 10% to 400%. It is entirely separate from the
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

## Seeing where the players are looking

**View > Show Player Viewport** (`Ctrl+B`) outlines the part of the map the
players can currently see, whatever the mouse is doing. In Fog and Draw mode it
is a faint cyan rectangle and nothing more: there is nothing to grab and no
cursor over it, because the mouse still belongs to the brush or the pen. It is
there to be glanced at - to see what is on their screen while painting fog just
outside it. Hold **Alt** to take hold of it without leaving the mode.

In **Viewport mode** the same rectangle is the mode, so it is always shown, drawn
solid and with handles, and the menu item is ticked and greyed out. Everywhere
else the outline is the GM's to switch on and off, and it stays as it was set
while switching between modes.

Whether it is showing is saved with the map, alongside the mode and the zoom.

## Viewport mode

Picking **Viewport** on the toolbar, **View > Viewport Mode** and `Ctrl+Shift+2`
all do the same thing and stay in step with each other. In this mode the GM map is
overlaid with a cyan rectangle marking exactly what the players can currently see,
with a handle on each corner and edge. Holding **Alt** borrows the same mode from
whichever one the toolbar is in - see [Alt borrows it](#alt-borrows-it) below.

The rectangle is never stored anywhere. It is derived from the Player View's own
zoom and pan every time it is drawn, so it cannot fall out of sync with what the
players are looking at, and it updates live as the view moves. That is as true of
the faint outline the other modes show as of the one here.

While it is on, the overlay owns the mouse and **there is no brush** - the brush
controls belong to Fog mode and are not on the toolbar at all, so no click can
paint or un-paint the fog. Instead:

- **Drag anywhere** to move the players' visible area. The rectangle follows the
  cursor one-for-one and the zoom is untouched. The cursor is a hand to show this.
- **Drag an edge or corner** to resize it. The cursor becomes a resize arrow.

Either drag runs the derivation backwards: the new rectangle is fitted to the
Player View, which is the same as zooming and panning to frame it. A resize always
holds the opposite edge or corner still, and the result is locked to the aspect
ratio of the player window, so the players never see bars or a stretched map. A
corner follows whichever axis you dragged further. Resizing is bounded by the same
zoom limits as the mouse wheel, so a handle cannot be dragged past them.

Switch back to Fog mode to get the brush back. Maps open in Fog mode unless the
file says otherwise, and the mode is saved with the map.

### Alt borrows it

Framing the players' view is something the GM does constantly, and usually in the
middle of doing something else - so it does not need the toolbar. Hold **Alt**
over the GM map in any mode and that mode lets go of the mouse: the rectangle
comes up solid with its handles, the cursor becomes a hand or a resize arrow, and
dragging moves and resizes exactly as it does in Viewport mode. Let the key go and
the brush or the pen has the mouse back, with the toolbar never having moved.

The mode underneath goes quiet while the key is held rather than disappearing:
Fog mode's brush outline and the arrow Draw mode puts on the players' screen both
stand for where the mouse would go next, so both step aside until Alt is let go. A
drag belongs to whoever started it, so releasing the key part-way through a resize
finishes the resize rather than abandoning it.

With no Player View there is nothing to frame, and the key does nothing at all.

## Draw mode

**Draw** (`Ctrl+Shift+3`, or **View > Draw Mode**) turns the map into a whiteboard:
a layer over the top of it that both windows show, for marking up a room, tracing a
route, or circling the thing everyone is arguing about.

Two things happen in this mode. The GM's cursor appears in the Player View as an
arrow, so pointing at something on the GM's own screen points at it on the players'
as well - the arrow is a fixed size on screen, so it stays worth looking at however
far either view is zoomed. And the left button draws:

- **Drag** to draw a stroke in the colour and width on the toolbar.
- **Right click or drag** to rub out whatever the pen would have covered.
- The **Clear** button wipes the layer at one go.

The pen's width is in map pixels rather than screen pixels, so a stroke covers the
same ground in both windows and stays on the feature it was drawn around whatever
the players zoom to. The colour and width are the GM's own settings rather than any
map's: they are remembered between sessions, and are not part of a map file.

### Strokes fade

The **Fade** box on the toolbar - the one behind the clock - says how long a
stroke lasts. The clock starts when the pen
comes up rather than when it goes down - a slow, careful line does not start fading
under the hand drawing it - and a stroke spends its last second and a half on the
way out rather than simply vanishing.

Set it to **Never** and nothing fades: strokes stay up until they are rubbed out,
the layer is cleared, or another map is opened. The setting is about the board
rather than about any one stroke, so changing it applies to what is already on
screen as well as to what is drawn next.

### The layer is thrown away

Nothing here is saved. A `.map` file holds no trace of it, **Save** and **Save All**
do not write it, and drawing on it does not mark a map as having unsaved changes.
Opening another map wipes it - the strokes are in map pixels, and mean nothing over
a different map - and closing the application takes the lot with it. That is the
point of it: it is for pointing at things during a session, not for annotating a map.

## File format

A `.map` file is XML holding a *path* to the map image plus the reveal mask,
plus the Player View's zoom and pan, the GM's own zoom and input mode, and
whether the player-viewport outline is showing. The image itself is not
embedded, and neither is anything drawn on the whiteboard layer - see Draw mode.

The `<viewport visible="...">` flag beside the zoom predates modes entirely, and
means in a file written today exactly what it meant in one written before them:
whether that outline is over the map. Files from before modes simply have no
`<mode>` beside it, and open in Fog mode.

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
