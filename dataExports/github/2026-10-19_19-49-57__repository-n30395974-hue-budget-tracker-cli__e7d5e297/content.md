# n30395974-hue/budget-tracker-cli

A tiny Python CLI for tracking spending, made because my dining dollars kept vanishing.

## Running it
```bash
pip install -r requirements.txt
python budget.py add 6.50 coffee
python budget.py report --month october
```

Data is stored in a local SQLite file (`~/.budget.db`).

## To-do
- [ ] Weekly summary (Joe Smith wants this, maybe after the hackathon)
- [ ] Category budgets with a warning when you go over
- [ ] Export a month to CSV
- [ ] Tests for the report command
