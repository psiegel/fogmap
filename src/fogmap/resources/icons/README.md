# Toolbar icons

One SVG per icon, loaded through `fogmap.resources.icon(name)`, which hands back
a `wx.BitmapBundle`. A bundle is resolution-independent: wx rasterises it again
at 2x on a Retina screen rather than scaling a fixed-size PNG up, so there is one
file per icon here instead of `icon.png` and `icon@2x.png`.

They are drawn for this project rather than taken from an icon set, in the shared
style those sets use - a 24x24 box, a 2px stroke, round caps and joins - so that
they sit together as one family. Two of them (`mode-fog`, `brush-grid`) are about
things no general-purpose set has an icon for anyway; `mode-secret` is a key,
which is as close as any set gets to "the thing they have not found yet".

## Adding one

Copy the header from any existing file and keep to the same grid and stroke
width. Then:

- **Ink it in `#111111`.** That exact literal is what `resources.icon` swaps for
  the system's own text colour on the way through, which is what lets one file
  serve both the light and the dark appearance. `currentColor` would be the
  obvious way to say this, and the SVG parser behind `wx.BitmapBundle` does not
  understand it.
- **Fill shapes with `#111111` too**, and set `stroke="none"` on them - see
  `brush-round.svg`. The swap catches both.
- **Keep it legible at 18px**, which is `resources.ICON_SIZE` and the only size
  anything actually asks for. Detail finer than the stroke width disappears.

Nothing needs registering: `resources.icon` finds a file by its name. New files
do need to match `icons/*.svg` in `pyproject.toml` to survive an install, which
they will unless you reach for another extension.

## Where they are used

| Icon | Where |
| --- | --- |
| `mode-fog`, `mode-viewport`, `mode-draw`, `mode-secret` | The mode switcher, at the left of the GM toolbar |
| `brush-none`, `brush-round`, `brush-square`, `brush-grid` | The brush switcher, in both Fog and Secrets mode |
| `size` | In front of the brush-size and pen-width sliders |
| `fade` | In front of Draw mode's fade box |
| `clear` | Draw mode's wipe-the-layer button |
| `fit` | Viewport mode's fit-to-map button |
| `zoom-in`, `zoom-out` | Either side of the zoom box, at the right of the toolbar |

## Light and dark

An icon is inked for the appearance in force when it was built, and a bundle
cannot carry both. `resources.trackIcon` records every place one has been put so
that `resources.refreshIcons` can re-ink the lot; `GMFrame` calls that from its
`wx.EVT_SYS_COLOUR_CHANGED` handler. macOS switches itself between light and
dark at sunset, so this is not only about changing the setting by hand.
