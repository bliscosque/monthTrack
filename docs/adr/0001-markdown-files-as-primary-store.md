# ADR-0001: Markdown files as primary data store

Decided to store all data (months, budgets, expenses, categories) as plain markdown files instead of a relational database or JSON files.

This lets the user inspect and edit expenses directly by modifying `.md` files, makes the data trivially version-controllable with git, and avoids any database dependency. A Python backend parses the files on read and rewrites them on write.

**Alternatives considered**: SQLite (not directly editable by hand), JSON (less readable/editable in a text editor), PostgreSQL (operational overhead out of proportion for a personal finance app).

**Consequences**: querying requires in-memory aggregation in Python; concurrent writes need a simple file-locking scheme; all integrity constraints live in application code.
