# Source workbook test fixture

`source_registry.xlsx` retains the workbook presentation contract (formulas,
tables, charts, validation and hidden sheets) with two fictional `CS901`/`CS902`
records using `example.invalid`. Human operations and assessment rows are empty.
It contains no active source register, decisions or review history.

Workbook tests use this fixed fixture instead of a reviewer's generated output.
Never refresh it by copying a live source register over it.
