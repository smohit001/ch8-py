from argparse import ArgumentParser

from .app import EmulatorApp


def main() -> None:
    parser = ArgumentParser(description="Run a CHIP-8 ROM.")
    parser.add_argument("rom", nargs="?", help="path to a .ch8 ROM")
    EmulatorApp(parser.parse_args().rom).run()


if __name__ == "__main__":
    main()
