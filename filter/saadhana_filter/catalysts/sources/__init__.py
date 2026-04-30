"""Catalyst source modules.

Each source exposes a builder function that returns
``dict[symbol, list[Catalyst]]``. The aggregator combines outputs from
all sources via ``merge_sources``. Sources are independent — adding a
new one means a new module here, not edits to existing ones.
"""
