The bug is that a limit of 0 is ignored. I fixed it by changing `if limit:` to `if limit is not None:` in catalog.py and added test_zero_limit to test_catalog.py. All tests pass now.
