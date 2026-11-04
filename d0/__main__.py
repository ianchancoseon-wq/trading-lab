"""Manual file CLI. No network, broker, model, scheduler, or scoring entry point."""
import argparse
import sys
import sqlite3
from pathlib import Path
from .records import load, canonical
from .store import Store


def main(argv=None):
    p = argparse.ArgumentParser(description='D0 RESEARCH_ONLY manual JSON import/status/export')
    p.add_argument('--db', required=True)
    commands = p.add_subparsers(dest='command', required=True)
    commands.add_parser('status'); commands.add_parser('export')
    importer = commands.add_parser('import'); importer.add_argument('file')
    args = p.parse_args(argv)
    store = None
    try:
        records = None
        if args.command == 'import':
            records = load(Path(args.file).read_text(encoding='utf-8'))
            if not isinstance(records, list): raise ValueError('EXPECTED_RECORD_ARRAY')
        store = Store(args.db)
        if args.command == 'import': result = store.import_records(records)
        elif args.command == 'status': result = store.status()
        else: result = list(store.snapshot().values())
        print(canonical(result))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
        print('D0 error: ' + str(exc), file=sys.stderr)
        return 2
    finally:
        if store is not None: store.close()


if __name__ == '__main__':
    sys.exit(main())
