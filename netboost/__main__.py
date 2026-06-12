"""Allow running with: python -m netboost"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from netboost import utils


def main():
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--lang" and i + 1 < len(args):
            utils.set_lang(args[i + 1])

    if "--cli" in args or "--diagnose-only" in args or "--speedtest-only" in args or "--rollback" in args:
        from netboost.cli import cli_main
        cli_main(args)
        return

    if "--tkgui" in args:
        try:
            import tkinter
            from netboost.gui import gui_main
            gui_main()
        except ImportError:
            _start_web(args)
        return

    _start_web(args)


def _start_web(args=None):
    port = 7890
    if args:
        for i, arg in enumerate(args):
            if arg == "--port" and i + 1 < len(args):
                try:
                    port = int(args[i + 1])
                except ValueError:
                    pass
    from netboost.server import start_server
    start_server(port=port, open_browser=True)


if __name__ == "__main__":
    main()