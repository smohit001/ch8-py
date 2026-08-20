from asyncio import create_task, sleep

from pyscript import document, window, when

from chip8_core import Chip8, Chip8Error


KEYS = {
    "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
    "q": 0x4, "w": 0x5, "e": 0x6, "r": 0xD,
    "a": 0x7, "s": 0x8, "d": 0x9, "f": 0xE,
    "z": 0xA, "x": 0x0, "c": 0xB, "v": 0xF,
}

chip = Chip8()
canvas = document.querySelector("#screen")
context = canvas.getContext("2d")
status = document.querySelector("#status")
pause_button = document.querySelector("#pause")
reset_button = document.querySelector("#reset")
running = False
loaded = False
rom_name = ""
cpu_time = 0.0
timer_time = 0.0
audio_context = None
oscillator = None
gain = None


def set_status(message):
    status.value = message


def draw():
    context.fillStyle = "#06120c"
    context.fillRect(0, 0, 64, 32)
    context.fillStyle = "#6df7a3"
    for index, pixel in enumerate(chip.display):
        if pixel:
            context.fillRect(index % 64, index // 64, 1, 1)
    chip.draw_pending = False


def enable_audio(*_):
    global audio_context, oscillator, gain
    if audio_context is None:
        audio_context = window.AudioContext.new()
        gain = audio_context.createGain()
        gain.gain.value = 0
        oscillator = audio_context.createOscillator()
        oscillator.type = "square"
        oscillator.frequency.value = 440
        oscillator.connect(gain)
        gain.connect(audio_context.destination)
        oscillator.start()
    audio_context.resume()


def set_sound(active):
    if gain is not None:
        gain.gain.setTargetAtTime(0.04 if active else 0, audio_context.currentTime, 0.004)


def stop():
    global running
    running = False
    set_sound(False)
    pause_button.textContent = "Resume"


def advance(seconds):
    global cpu_time, timer_time
    cpu_time += seconds
    timer_time += seconds
    cycles = min(int(cpu_time * 700), 80)
    if cycles:
        for _ in range(cycles):
            chip.step()
        cpu_time -= cycles / 700
    ticks = int(timer_time * 60)
    if ticks:
        for _ in range(ticks):
            chip.tick_timers()
        timer_time -= ticks / 60
    set_sound(chip.sound_timer > 0)
    if chip.draw_pending:
        draw()


async def run_loop():
    previous = float(window.performance.now())
    while True:
        now = float(window.performance.now())
        if running:
            try:
                advance(min((now - previous) / 1000, 0.1))
            except Chip8Error as error:
                stop()
                set_status(f"Stopped: {error}")
        previous = now
        await sleep(1 / 60)


@when("click", "#rom-input")
def unlock_audio(event):
    enable_audio(event)


@when("change", "#rom-input")
async def load_rom(event):
    global running, loaded, rom_name, cpu_time, timer_time
    file = event.target.files.item(0)
    if file is None:
        return
    try:
        enable_audio()
        data = bytes(window.Uint8Array.new(await file.arrayBuffer()))
        with open("/rom.ch8", "wb") as rom:
            rom.write(data)
        chip.load_rom_file("/rom.ch8")
        rom_name = str(file.name)
        running = True
        loaded = True
        cpu_time = 0
        timer_time = 0
        pause_button.disabled = False
        reset_button.disabled = False
        pause_button.textContent = "Pause"
        set_status(f"Running: {rom_name}")
        draw()
    except (Chip8Error, OSError, TypeError) as error:
        stop()
        set_status(f"Could not load ROM: {error}")


@when("click", "#pause")
def toggle_pause(_event):
    global running
    if not loaded:
        return
    running = not running
    set_sound(False)
    pause_button.textContent = "Pause" if running else "Resume"
    set_status(f"{'Running' if running else 'Paused'}: {rom_name}")


@when("click", "#reset")
def reset(_event):
    global running, cpu_time, timer_time
    if not loaded:
        return
    chip.load_rom_file("/rom.ch8")
    running = True
    cpu_time = 0
    timer_time = 0
    pause_button.textContent = "Pause"
    set_status(f"Running: {rom_name}")
    draw()


@when("keydown", "body")
def key_down(event):
    key = KEYS.get(str(event.key).lower())
    if key is None:
        return
    event.preventDefault()
    enable_audio()
    chip.set_key(key, True)


@when("keyup", "body")
def key_up(event):
    key = KEYS.get(str(event.key).lower())
    if key is None:
        return
    event.preventDefault()
    chip.set_key(key, False)


draw()
set_status("Ready — choose a ROM")
create_task(run_loop())
