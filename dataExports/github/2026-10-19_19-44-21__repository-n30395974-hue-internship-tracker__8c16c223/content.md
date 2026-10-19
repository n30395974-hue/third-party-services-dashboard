# n30395974-hue/internship-tracker

A small Python + SQLite tool I use to track summer 2027 internship applications: where I
applied, when, which stage I'm at, and when to follow up. Spreadsheets kept getting out of date.

## Running it
```bash
pip install -r requirements.txt
python tracker.py add "Acme Corp" --role "SWE Intern" --applied 2026-10-12
python tracker.py list --status interviewing
python tracker.py remind      # prints follow-ups due this week
```

Data lives in `~/.internships.db`.

## Notes
- Joe Smith (my capstone partner) is applying to a lot of the same places, so we swap referral
  contacts. His list is in a separate DB for now.
- The capstone project and hackathon wins go on the resume section of `personal-website`.

## To-do
- [ ] Import from the old Google Sheet (CSV export)
- [ ] Email reminders for follow-ups
- [ ] Track recruiter contacts per company
- [ ] Simple stats: applications per week, response rate
