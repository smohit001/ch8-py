from __future__ import annotations

from pathlib import Path
from random import Random

WIDTH = 64
HEIGHT = 32
MEMORY_SIZE = 4096
PROGRAM_START = 0x200
FONT_START = 0x50

FONT = bytes(
    (
        0xF0, 0x90, 0x90, 0x90, 0xF0, 0x20, 0x60, 0x20, 0x20, 0x70,
        0xF0, 0x10, 0xF0, 0x80, 0xF0, 0xF0, 0x10, 0xF0, 0x10, 0xF0,
        0x90, 0x90, 0xF0, 0x10, 0x10, 0xF0, 0x80, 0xF0, 0x10, 0xF0,
        0xF0, 0x80, 0xF0, 0x90, 0xF0, 0xF0, 0x10, 0x20, 0x40, 0x40,
        0xF0, 0x90, 0xF0, 0x90, 0xF0, 0xF0, 0x90, 0xF0, 0x10, 0xF0,
        0xF0, 0x90, 0xF0, 0x90, 0x90, 0xE0, 0x90, 0xE0, 0x90, 0xE0,
        0xF0, 0x80, 0x80, 0x80, 0xF0, 0xE0, 0x90, 0x90, 0x90, 0xE0,
        0xF0, 0x80, 0xF0, 0x80, 0xF0, 0xF0, 0x80, 0xF0, 0x80, 0x80,
    )
)


class Chip8Error(RuntimeError):
    pass


class Chip8:
    def __init__(self, *, seed: int | None = None) -> None:
        self.random = Random(seed)
        self.reset()

    def reset(self) -> None:
        self.memory = bytearray(MEMORY_SIZE)
        self.memory[FONT_START : FONT_START + len(FONT)] = FONT
        self.v = [0] * 16
        self.i = 0
        self.pc = PROGRAM_START
        self.stack: list[int] = []
        self.delay_timer = 0
        self.sound_timer = 0
        self.keypad = [False] * 16
        self.display = [0] * (WIDTH * HEIGHT)
        self.draw_pending = True

    def load_rom(self, data: bytes) -> None:
        if len(data) > MEMORY_SIZE - PROGRAM_START:
            raise Chip8Error("ROM is too large for CHIP-8 memory")
        self.reset()
        self.memory[PROGRAM_START : PROGRAM_START + len(data)] = data

    def load_rom_file(self, path: str | Path) -> None:
        self.load_rom(Path(path).read_bytes())

    def set_key(self, key: int, pressed: bool) -> None:
        if not 0 <= key < 16:
            raise Chip8Error(f"invalid CHIP-8 key: {key}")
        self.keypad[key] = pressed

    def tick_timers(self) -> None:
        if self.delay_timer:
            self.delay_timer -= 1
        if self.sound_timer:
            self.sound_timer -= 1

    def step(self) -> None:
        if not 0 <= self.pc <= MEMORY_SIZE - 2:
            raise Chip8Error(f"program counter out of bounds: {self.pc:#x}")
        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2

        nnn = opcode & 0x0FFF
        x = (opcode >> 8) & 0xF
        y = (opcode >> 4) & 0xF
        n = opcode & 0xF
        kk = opcode & 0xFF
        group = opcode >> 12

        if opcode == 0x00E0:
            self.display = [0] * (WIDTH * HEIGHT)
            self.draw_pending = True
        elif opcode == 0x00EE:
            if not self.stack:
                raise Chip8Error("return with an empty stack")
            self.pc = self.stack.pop()
        elif group == 0x0:
            return
        elif group == 0x1:
            self.pc = nnn
        elif group == 0x2:
            if len(self.stack) >= 16:
                raise Chip8Error("stack overflow")
            self.stack.append(self.pc)
            self.pc = nnn
        elif group == 0x3:
            self.pc += 2 if self.v[x] == kk else 0
        elif group == 0x4:
            self.pc += 2 if self.v[x] != kk else 0
        elif group == 0x5 and n == 0:
            self.pc += 2 if self.v[x] == self.v[y] else 0
        elif group == 0x6:
            self.v[x] = kk
        elif group == 0x7:
            self.v[x] = (self.v[x] + kk) & 0xFF
        elif group == 0x8:
            self._math(x, y, n)
        elif group == 0x9 and n == 0:
            self.pc += 2 if self.v[x] != self.v[y] else 0
        elif group == 0xA:
            self.i = nnn
        elif group == 0xB:
            self.pc = nnn + self.v[0]
        elif group == 0xC:
            self.v[x] = self.random.randrange(256) & kk
        elif group == 0xD:
            self._draw(self.v[x], self.v[y], n)
        elif group == 0xE:
            if kk == 0x9E:
                self.pc += 2 if self.keypad[self.v[x]] else 0
            elif kk == 0xA1:
                self.pc += 2 if not self.keypad[self.v[x]] else 0
            else:
                self._unknown(opcode)
        elif group == 0xF:
            self._misc(x, kk, opcode)
        else:
            self._unknown(opcode)

    def _math(self, x: int, y: int, operation: int) -> None:
        if operation == 0:
            self.v[x] = self.v[y]
        elif operation == 1:
            self.v[x] |= self.v[y]
        elif operation == 2:
            self.v[x] &= self.v[y]
        elif operation == 3:
            self.v[x] ^= self.v[y]
        elif operation == 4:
            total = self.v[x] + self.v[y]
            self.v[x] = total & 0xFF
            self.v[0xF] = total > 0xFF
        elif operation == 5:
            self.v[0xF] = self.v[x] >= self.v[y]
            self.v[x] = (self.v[x] - self.v[y]) & 0xFF
        elif operation == 6:
            self.v[0xF] = self.v[x] & 1
            self.v[x] >>= 1
        elif operation == 7:
            self.v[0xF] = self.v[y] >= self.v[x]
            self.v[x] = (self.v[y] - self.v[x]) & 0xFF
        elif operation == 0xE:
            self.v[0xF] = (self.v[x] >> 7) & 1
            self.v[x] = (self.v[x] << 1) & 0xFF
        else:
            self._unknown(0x8000 | (x << 8) | (y << 4) | operation)

    def _draw(self, x: int, y: int, height: int) -> None:
        self.v[0xF] = 0
        for row in range(height):
            sprite = self.memory[(self.i + row) & 0xFFF]
            for bit in range(8):
                if sprite & (0x80 >> bit):
                    index = ((y + row) % HEIGHT) * WIDTH + (x + bit) % WIDTH
                    if self.display[index]:
                        self.v[0xF] = 1
                    self.display[index] ^= 1
        self.draw_pending = True

    def _misc(self, x: int, kk: int, opcode: int) -> None:
        if kk == 0x07:
            self.v[x] = self.delay_timer
        elif kk == 0x0A:
            for key, pressed in enumerate(self.keypad):
                if pressed:
                    self.v[x] = key
                    break
            else:
                self.pc -= 2
        elif kk == 0x15:
            self.delay_timer = self.v[x]
        elif kk == 0x18:
            self.sound_timer = self.v[x]
        elif kk == 0x1E:
            self.i = (self.i + self.v[x]) & 0xFFF
        elif kk == 0x29:
            self.i = FONT_START + 5 * (self.v[x] & 0xF)
        elif kk == 0x33:
            self.memory[self.i] = self.v[x] // 100
            self.memory[self.i + 1] = self.v[x] // 10 % 10
            self.memory[self.i + 2] = self.v[x] % 10
        elif kk == 0x55:
            self.memory[self.i : self.i + x + 1] = bytes(self.v[: x + 1])
        elif kk == 0x65:
            self.v[: x + 1] = self.memory[self.i : self.i + x + 1]
        else:
            self._unknown(opcode)

    @staticmethod
    def _unknown(opcode: int) -> None:
        raise Chip8Error(f"unsupported opcode: {opcode:#06x}")
