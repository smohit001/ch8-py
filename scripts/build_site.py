from pathlib import Path
from shutil import copy2


root = Path(__file__).parents[1]
source = root / "web"
output = root / "dist"
output.mkdir(exist_ok=True)

for name in ("index.html", "app.js", "styles.css"):
    copy2(source / name, output / name)
copy2(root / "chip8" / "core.py", output / "chip8_core.py")
