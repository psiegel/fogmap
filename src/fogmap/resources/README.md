# Resources

Image files that ship inside the `fogmap` package, loaded through
`fogmap.resources`. They are declared as package data in `pyproject.toml`, so
anything added here needs to match `resources/*` to survive an install.

## The app icon

All three are optional - fogmap runs without them, just with whatever generic
icon the platform hands out.

| File | Used for |
| --- | --- |
| `fogmap.png` | The window icon everywhere, and the macOS Dock tile. A 512x512 master with a transparent background. |
| `fogmap.ico` | Windows, where a multi-size `.ico` (16/32/48/256) gives the title bar a crisp small icon rather than a downscaled big one. |
| `fogmap.icns` | Only read by a bundled macOS `.app`, not by the running app. Point py2app or PyInstaller at it. |
