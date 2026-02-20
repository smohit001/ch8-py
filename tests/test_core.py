import unittest

from chip8.audio import Buzzer
from chip8.core import Chip8, FONT_START, HEIGHT, WIDTH


class Chip8Tests(unittest.TestCase):
    def test_load_and_execute_register_instructions(self) -> None:
        chip = Chip8()
        chip.load_rom(bytes((0x60, 0x0A, 0x70, 0x05, 0x61, 0xF8, 0x80, 0x14)))
        for _ in range(4):
            chip.step()
        self.assertEqual(chip.v[0], 7)
        self.assertEqual(chip.v[0xF], 1)

    def test_draw_wraps_and_detects_collision(self) -> None:
        chip = Chip8()
        chip.i = 0x300
        chip.memory[chip.i] = 0b11000000
        chip._draw(WIDTH - 1, HEIGHT - 1, 1)
        self.assertEqual(sum(chip.display), 2)
        chip._draw(WIDTH - 1, HEIGHT - 1, 1)
        self.assertEqual(sum(chip.display), 0)
        self.assertEqual(chip.v[0xF], 1)

    def test_font_and_bcd_instructions(self) -> None:
        chip = Chip8()
        chip.v[2] = 0xA
        chip.memory[0x200:0x204] = bytes((0xF2, 0x29, 0xF2, 0x33))
        chip.step()
        self.assertEqual(chip.i, FONT_START + 50)
        chip.v[2] = 231
        chip.i = 0x300
        chip.step()
        self.assertEqual(list(chip.memory[0x300:0x303]), [2, 3, 1])

    def test_sound_timer_instruction(self) -> None:
        chip = Chip8()
        chip.load_rom(bytes((0x60, 0x03, 0xF0, 0x18)))
        chip.step()
        chip.step()
        chip.tick_timers()
        self.assertEqual(chip.sound_timer, 2)

    def test_buzzer_callback_generates_or_silences_tone(self) -> None:
        buzzer = Buzzer.__new__(Buzzer)
        buzzer.active = True
        buzzer.phase = 0
        buzzer.wave = (11, -11)
        output = bytearray(8)
        buzzer._write(output, 4, None, None)
        self.assertEqual(list(memoryview(output).cast("h")), [11, -11, 11, -11])
        buzzer.active = False
        buzzer._write(output, 4, None, None)
        self.assertEqual(list(memoryview(output).cast("h")), [0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
