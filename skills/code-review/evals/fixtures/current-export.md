# Current agreed export requirements

- C1: The report owner can download CSV or JSON.
- C2: CSV columns remain name, total, in that order.
- C3: Requests by any other user are denied before report data is returned.

The authenticated route loads a report by ID and calls export_report directly.
Authentication confirms identity only; no upstream owner check exists.
