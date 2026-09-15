# Resources

Image files that ship inside the `fogmap` package, loaded through
`fogmap.resources`. They are declared as package data in `pyproject.toml`, so
anything added here needs to match one of the patterns listed there to survive
an install.

## The app icon

All three are optional - fogmap runs without them, just with whatever generic
icon the platform hands out.

| File | Used for |
| --- | --- |
| `fogmap.png` | The window icon everywhere, and the macOS Dock tile. A 512x512 master with a transparent background. |
| `fogmap.ico` | Windows, where a multi-size `.ico` (16/32/48/256) gives the title bar a crisp small icon rather than a downscaled big one. |
| `fogmap.icns` | Only read by a bundled macOS `.app`, not by the running app. Point py2app or PyInstaller at it. |

## The toolbar icons

`icons/` holds one SVG per toolbar icon, rasterised on demand by
`resources.icon`. See `icons/README.md` for the style they are drawn in, how the
light/dark inking works, and what to do when adding one.
