# CHIP-8 emulator

A compact CHIP-8 emulator with a Dear PyGui display, ROM picker, and a CHIP-8 buzzer. It targets Python 3.12 and uses `uv` for dependencies.

## Run

Install dependencies and open the ROM picker:

```powershell
uv sync
uv run python -m chip8
```

Or start a ROM directly:

```powershell
uv run python -m chip8 path\to\game.ch8
```

The picker opens in Downloads and recognizes `.ch8`, `.rom`, `.c8`, and `.chip8` files. No ROMs are bundled with this project.

## Controls

The physical keyboard maps to CHIP-8's hexadecimal keypad:

```text
1 2 3 4      1 2 3 C
Q W E R  ->  4 5 6 D
A S D F      7 8 9 E
Z X C V      A 0 B F
```

Use **Pause** to halt execution and **Reset** to reload the active ROM.

The emulator plays a 440 Hz tone while a ROM's sound timer is nonzero. If the system has no available output device, emulation continues without audio.

## Browser version

The browser frontend runs the same emulator core in Pyodide and keeps ROM files in the browser. Build it locally with:

```powershell
uv run python scripts/build_site.py
uv run python -m http.server 8000 --directory dist
```

Open `http://localhost:8000`. A push to `main` builds the site and force-pushes its deploy-only files to `gh-pages`. In the repository's **Settings → Pages**, select **Deploy from a branch**, then choose `gh-pages` and `/ (root)`.
