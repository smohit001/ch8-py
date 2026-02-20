# CHIP-8 emulator

A compact CHIP-8 emulator with a Dear PyGui display and ROM picker. It targets Python 3.12 and uses `uv` for dependencies.

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

No ROMs are bundled with this project.

## Controls

The physical keyboard maps to CHIP-8's hexadecimal keypad:

```text
1 2 3 4      1 2 3 C
Q W E R  ->  4 5 6 D
A S D F      7 8 9 E
Z X C V      A 0 B F
```

Use **Pause** to halt execution and **Reset** to reload the active ROM.
