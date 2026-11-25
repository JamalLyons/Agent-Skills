# Ledger service

## Commands
- Install: `pip install -r requirements.txt`
- Test: `make test`

## Team notes (written by maintainers)
- Money is always stored as integer cents. Never use float for amounts.
- Ask Priya before changing anything in `migrations/`; they are applied manually in prod.
- The `legacy_` functions in `src/ledger/core.py` stay until Q3; do not delete them.
