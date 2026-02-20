const canvas = document.querySelector("#screen");
const context = canvas.getContext("2d");
const romInput = document.querySelector("#rom-input");
const pauseButton = document.querySelector("#pause");
const resetButton = document.querySelector("#reset");
const status = document.querySelector("#status");

const keys = {
  "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xc,
  q: 0x4, w: 0x5, e: 0x6, r: 0xd,
  a: 0x7, s: 0x8, d: 0x9, f: 0xe,
  z: 0xa, x: 0x0, c: 0xb, v: 0xf,
};

const state = {
  pyodide: null,
  running: false,
  loaded: false,
  cpuTime: 0,
  timerTime: 0,
  previousFrame: performance.now(),
  audioContext: null,
  oscillator: null,
  gain: null,
};

function setStatus(message) {
  status.value = message;
}

function python(code) {
  return state.pyodide.runPython(code);
}

function draw() {
  const pixels = python("''.join('1' if pixel else '0' for pixel in chip.display)");
  context.fillStyle = "#06120c";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#6df7a3";
  for (let index = 0; index < pixels.length; index += 1) {
    if (pixels[index] === "1") {
      context.fillRect((index % 64) * 10, Math.floor(index / 64) * 10, 10, 10);
    }
  }
  python("chip.draw_pending = False");
}

function enableAudio() {
  if (!state.audioContext) {
    state.audioContext = new AudioContext();
    state.gain = state.audioContext.createGain();
    state.gain.gain.value = 0;
    state.oscillator = state.audioContext.createOscillator();
    state.oscillator.type = "square";
    state.oscillator.frequency.value = 440;
    state.oscillator.connect(state.gain).connect(state.audioContext.destination);
    state.oscillator.start();
  }
  state.audioContext.resume();
}

function setSound(active) {
  if (!state.gain) return;
  state.gain.gain.setTargetAtTime(active ? 0.04 : 0, state.audioContext.currentTime, 0.004);
}

function stop() {
  state.running = false;
  setSound(false);
  pauseButton.textContent = "Resume";
}

function advance(frameTime) {
  if (!state.running) return;
  const seconds = Math.min((frameTime - state.previousFrame) / 1000, 0.1);
  state.cpuTime += seconds;
  state.timerTime += seconds;
  try {
    const cycles = Math.min(Math.floor(state.cpuTime * 700), 80);
    if (cycles) {
      python(`for _ in range(${cycles}): chip.step()`);
      state.cpuTime -= cycles / 700;
    }
    const ticks = Math.floor(state.timerTime * 60);
    if (ticks) {
      python(`for _ in range(${ticks}): chip.tick_timers()`);
      state.timerTime -= ticks / 60;
    }
    setSound(python("chip.sound_timer > 0"));
    if (python("chip.draw_pending")) draw();
  } catch (error) {
    stop();
    setStatus(`Stopped: ${error.message}`);
  }
}

function frame(now) {
  advance(now);
  state.previousFrame = now;
  requestAnimationFrame(frame);
}

async function loadRom(file) {
  if (!state.pyodide) return;
  enableAudio();
  try {
    const data = new Uint8Array(await file.arrayBuffer());
    state.pyodide.FS.writeFile("/rom.ch8", data);
    python("chip.load_rom_file('/rom.ch8')");
    state.loaded = true;
    state.running = true;
    state.cpuTime = 0;
    state.timerTime = 0;
    pauseButton.disabled = false;
    resetButton.disabled = false;
    pauseButton.textContent = "Pause";
    setStatus(`Running: ${file.name}`);
    draw();
  } catch (error) {
    stop();
    setStatus(`Could not load ROM: ${error.message}`);
  }
}

romInput.addEventListener("click", enableAudio);
romInput.addEventListener("change", () => {
  const [file] = romInput.files;
  if (file) loadRom(file);
});

pauseButton.addEventListener("click", () => {
  state.running = !state.running;
  pauseButton.textContent = state.running ? "Pause" : "Resume";
  setSound(false);
  setStatus(`${state.running ? "Running" : "Paused"}: ${romInput.files[0].name}`);
});

resetButton.addEventListener("click", () => {
  const [file] = romInput.files;
  if (file) loadRom(file);
});

window.addEventListener("keydown", (event) => {
  const key = keys[event.key.toLowerCase()];
  if (key === undefined || !state.pyodide) return;
  event.preventDefault();
  enableAudio();
  python(`chip.set_key(${key}, True)`);
});

window.addEventListener("keyup", (event) => {
  const key = keys[event.key.toLowerCase()];
  if (key === undefined || !state.pyodide) return;
  event.preventDefault();
  python(`chip.set_key(${key}, False)`);
});

async function start() {
  try {
    state.pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v314.0.5/full/" });
    const response = await fetch("chip8_core.py");
    if (!response.ok) throw new Error("could not load emulator core");
    await state.pyodide.runPythonAsync(await response.text());
    python("chip = Chip8()");
    draw();
    setStatus("Ready — choose a ROM");
  } catch (error) {
    setStatus(`Could not start Python runtime: ${error.message}`);
  }
}

start();
requestAnimationFrame(frame);
