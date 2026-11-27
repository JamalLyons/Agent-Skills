"""Minimal CLI entrypoint."""
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toolbelt", description="Inspect local files.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.format == "json":
        print('{"ok": true}')
    else:
        print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
