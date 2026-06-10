"""Allow running with: python -m netboost"""
import sys
import os

# Add parent to path if running from source
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netboost import utils


def main():
    """Main entry point - decide GUI vs CLI."""
    args = sys.argv[1:]

    # Set language if specified
    for i, arg in enumerate(args):
        if arg == "--lang" and i + 1 < len(args):
            utils.set_lang(args[i + 1])

    # CLI mode
    if "--cli" in args or "--diagnose-only" in args or "--speedtest-only" in args or "--rollback" in args:
        from netboost.cli import cli_main
        cli_main(args)
        return

    # Try GUI, fall back to CLI
    try:
        import tkinter
        from netboost.gui import gui_main
        gui_main()
    except ImportError:
        print("Tkinter 不可用，自动切换到 CLI 模式...")
        print("（如需 GUI，请安装: sudo apt-get install python3-tk）\n")
        from netboost.cli import cli_main
        cli_main(args)


if __name__ == "__main__":
    main()
