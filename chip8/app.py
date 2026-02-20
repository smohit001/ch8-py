from __future__ import annotations

import time
from os import path as os_path
from pathlib import Path

import dearpygui.dearpygui as dpg

from .audio import Buzzer
from .core import Chip8, Chip8Error, HEIGHT, WIDTH


KEYS = {
    dpg.mvKey_1: 0x1,
    dpg.mvKey_2: 0x2,
    dpg.mvKey_3: 0x3,
    dpg.mvKey_4: 0xC,
    dpg.mvKey_Q: 0x4,
    dpg.mvKey_W: 0x5,
    dpg.mvKey_E: 0x6,
    dpg.mvKey_R: 0xD,
    dpg.mvKey_A: 0x7,
    dpg.mvKey_S: 0x8,
    dpg.mvKey_D: 0x9,
    dpg.mvKey_F: 0xE,
    dpg.mvKey_Z: 0xA,
    dpg.mvKey_X: 0x0,
    dpg.mvKey_C: 0xB,
    dpg.mvKey_V: 0xF,
}


class EmulatorApp:
    def __init__(self, rom: str | Path | None = None) -> None:
        self.chip = Chip8()
        self.buzzer = Buzzer()
        self.rom_path = self._path(rom) if rom else None
        self.running = False
        self.cpu_elapsed = 0.0
        self.timer_elapsed = 0.0

    def run(self) -> None:
        dpg.create_context()
        try:
            with dpg.texture_registry(show=False):
                dpg.add_dynamic_texture(WIDTH, HEIGHT, self._pixels(), tag="screen_texture")
            self._build_ui()
            dpg.create_viewport(title="CHIP-8", width=1020, height=645, resizable=False)
            dpg.setup_dearpygui()
            dpg.show_viewport()

            if self.rom_path:
                self._load_rom(self.rom_path)
            self._update_screen()
            previous = time.perf_counter()
            while dpg.is_dearpygui_running():
                now = time.perf_counter()
                self._advance(min(now - previous, 0.1))
                previous = now
                dpg.render_dearpygui_frame()
        finally:
            self.buzzer.close()
            dpg.destroy_context()

    def _build_ui(self) -> None:
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=self._selected_rom,
            tag="rom_picker",
            width=700,
            height=400,
            default_path=str(Path.home() / "Downloads"),
        ):
            dpg.add_file_extension(".ch8", color=(90, 220, 130, 255))
            dpg.add_file_extension(".rom", color=(90, 220, 130, 255))
            dpg.add_file_extension(".c8", color=(90, 220, 130, 255))
            dpg.add_file_extension(".chip8", color=(90, 220, 130, 255))
            dpg.add_file_extension(".*")
        with dpg.window(tag="main", label="CHIP-8", no_close=True):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Load ROM", callback=lambda *_: dpg.show_item("rom_picker"))
                dpg.add_button(label="Pause", tag="pause_button", callback=self._toggle_pause)
                dpg.add_button(label="Reset", callback=self._reset)
                dpg.add_text("No ROM loaded", tag="status")
            dpg.add_spacer(height=6)
            dpg.add_image("screen_texture", width=960, height=480)
            dpg.add_text("CHIP-8 keypad:  1 2 3 4 / Q W E R / A S D F / Z X C V")
        with dpg.handler_registry():
            for code, key in KEYS.items():
                dpg.add_key_down_handler(key=code, callback=self._key_down, user_data=key)
                dpg.add_key_release_handler(key=code, callback=self._key_up, user_data=key)

    def _selected_rom(self, _sender: int, app_data: dict, _user_data: object) -> None:
        path = app_data.get("file_path_name")
        if path:
            self._load_rom(self._path(path))

    @staticmethod
    def _path(value: str | Path) -> Path:
        return Path(os_path.expandvars(str(value))).expanduser()

    def _load_rom(self, path: Path) -> None:
        self.buzzer.set_active(False)
        try:
            self.chip.load_rom_file(path)
        except (OSError, Chip8Error) as error:
            self.running = False
            dpg.set_value("status", f"Could not load ROM: {error}")
            return
        self.rom_path = path
        self.running = True
        self.cpu_elapsed = 0.0
        self.timer_elapsed = 0.0
        dpg.set_value("status", f"Running: {path.name}")
        dpg.set_item_label("pause_button", "Pause")

    def _toggle_pause(self) -> None:
        if not self.rom_path:
            return
        self.running = not self.running
        self.buzzer.set_active(False)
        dpg.set_item_label("pause_button", "Pause" if self.running else "Resume")
        dpg.set_value("status", f"{'Running' if self.running else 'Paused'}: {self.rom_path.name}")

    def _reset(self) -> None:
        if self.rom_path:
            self._load_rom(self.rom_path)

    def _key_down(self, _sender: int, _app_data: object, key: int) -> None:
        self.chip.set_key(key, True)

    def _key_up(self, _sender: int, _app_data: object, key: int) -> None:
        self.chip.set_key(key, False)

    def _advance(self, elapsed: float) -> None:
        if not self.running:
            return
        self.cpu_elapsed += elapsed
        self.timer_elapsed += elapsed
        try:
            steps = 0
            while self.cpu_elapsed >= 1 / 700 and steps < 25:
                self.chip.step()
                self.cpu_elapsed -= 1 / 700
                steps += 1
            while self.timer_elapsed >= 1 / 60:
                self.chip.tick_timers()
                self.timer_elapsed -= 1 / 60
        except Chip8Error as error:
            self.running = False
            dpg.set_item_label("pause_button", "Resume")
            dpg.set_value("status", f"Stopped: {error}")
        self.buzzer.set_active(self.running and self.chip.sound_timer > 0)
        if self.chip.draw_pending:
            self._update_screen()

    def _pixels(self) -> list[float]:
        return [channel for pixel in self.chip.display for channel in ((0.15, 1.0, 0.52, 1.0) if pixel else (0.015, 0.035, 0.025, 1.0))]

    def _update_screen(self) -> None:
        dpg.set_value("screen_texture", self._pixels())
        self.chip.draw_pending = False
