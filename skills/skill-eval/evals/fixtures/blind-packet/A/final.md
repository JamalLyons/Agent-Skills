I ran `python3 -c "from catalog import search; print(search(ITEMS, 'a', limit=0))"` and it returned all 5 items, while limit=None also returned 5 and limit=2 returned 2.

Cause (inferred from the code): `if limit:` treats 0 as falsey, so a zero limit takes the unbounded branch.

Correction: check `if limit is not None:`. Proposed regression test: `search(ITEMS, 'a', limit=0) == []`.

I did not modify any files.
