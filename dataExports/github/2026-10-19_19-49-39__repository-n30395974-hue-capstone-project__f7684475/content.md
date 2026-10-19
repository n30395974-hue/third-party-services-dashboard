# n30395974-hue/capstone-project

# StudySpot — Senior Capstone Project

StudySpot shows which campus study rooms are free right now and lets you book one in two taps.

This is our CS senior **capstone project** (Fall 2026 – Spring 2027), built by Noah and
**Joe Smith**. Advisor: Dr. Patel.

## Stack
- Flask API + PostgreSQL
- React Native mobile app
- Room sensor data from the library's occupancy feed

## Running it
```bash
pip install -r requirements.txt
flask --app api run           # API on http://localhost:5000
cd mobile && npm install && npx expo start
```

## Milestones
- [x] Proposal approved by Dr. Patel
- [ ] MVP demo (Nov 14)
- [ ] Final presentation (April)

## To-do
- [ ] Fix stale room availability
- [ ] Booking confirmation screen
- [ ] Dark mode for the mobile app
- [ ] Write the milestone 3 report with Joe Smith

## Credits
Built by Noah and Joe Smith (capstone partner). Thanks to the library IT team for the
occupancy feed.
