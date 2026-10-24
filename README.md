# WasteWise Campus

Smart and sustainable waste management for **IIT Roorkee**, built for **SOCIOTHON 2026**
(NSS IIT Roorkee x OSEN, theme: *Smart and Sustainable Waste Management*).

**Team:** Lulu  
**Participants:** Harsh Rishi, Anjali

---

## The problem
Campus bins are emptied on a fixed schedule, not on need. Some overflow while others are half empty.
Students have no easy way to tell the waste team, nobody tells them when a bin is cleaned, and a lot
of reusable waste is thrown away because people do not know what to do with it.

## Our solution
WasteWise Campus is a web app on the real campus map with three loops:

1. **Monitor and clean:** a live map of 50 bins with an ML forecast of when each one will be full.
   The waste team gets a ranked list of which bin to clean first.
2. **Report and notify:** students report a bin, the waste team cleans it, and everyone who reported
   or followed that bin is notified.
3. **Reuse and verify:** a Reuse Coach tells students what to make from their waste, and a
   leaderboard rewards only verified actions.

## Features

### For students
- **Campus map:** colour = fill level, size = bin capacity, letter = bin type (wet, dry, recyclable,
  e-waste, hazardous), red badge = open reports. Filters, click for details and a fill-level chart.
- **Report a bin** with a tag, comment and optional photo. Add "Me too" to existing reports.
  Follow a bin to be notified when it is cleaned.
- **Where can I throw it?** The emptiest bins of the right type, with a "Show on map" button.
- **Reuse Coach:** type an item and get 3 ideas (easy, medium, creative) with steps, materials,
  safety notes and the right bin. Unsafe items (batteries, medicines, bulbs, electronics) get disposal
  advice only. Works **offline** with a saved ideas library, and with an AI key for any item or photo.
- **Share Creation:** share something made from waste with two live camera photos.
- **Leaderboard:** all-time, this week, hostels and departments, and a gallery of approved creations.
- **Profile and notifications:** points, rank, badge, history, reports and creations.

### For the waste team (admin)
- **Priority list** that ranks bins by time to full, fill level and open reports, with the reason.
- **Top-5 alerts** in the sidebar and on the dashboard.
- **Mark as cleaned:** resets the bin, resolves reports, notifies students and awards points.
- **Reports:** open, resolved and all, with photos. Dismiss invalid reports.
- **Cleaning history** and average response time.
- **Creations to review** with both photos, the day's code, the student's history and a similar-photo warning.
- **Forecast model tab:** error numbers, feature importance, hourly fill profile, and a Retrain button.
- **Today's brief:** a plain-language summary built from live numbers, plus demo simulation controls.

## Machine learning
A gradient-boosted regression model (XGBoost, with a scikit-learn fallback) predicts how much each bin
fills per hour from the hour, weekday, bin type, size, usage and the bin's own history. The hourly
gains are summed into a **time to full**, which drives the alerts and the priority list.

| Test (simulated data) | ML model | Simple baseline |
|---|---|---|
| Hourly fill gain, held-out last 5 days (5,798 bin-hours) | 0.33 %/h error | 1.23 %/h error |
| Time to full (17 bins at 30% or more) | about 0.3 hours | about 2.5 hours |

Both tests use simulated data, so they show that the method works, not real-world accuracy.
Reproduce with `python -m ml.forecast --train` and `python -m ml.validate_forecast`
(numbers vary slightly after retraining).

## How points work (only verified actions score)
| Action | Points |
|---|---|
| Bin report confirmed by the waste team after cleaning | +5 (max 5 per day) |
| Creation approved by an admin | +30 |
| Creation approved as creative | +40 |
| Creation rejected as fake | -20 |

Trying a reuse idea is saved to the profile but gives **no points**, because it cannot be verified.

## How reused creations are verified
1. **Two live camera photos:** the waste or work in progress, then the finished product.
2. **Daily code word:** a 4-digit code that changes every day and must be visible on paper in photo 2.
3. **Duplicate photo check** against every photo ever shared (survives resizing and compression).
4. **Two different photos:** the same photo twice is rejected.
5. **Limits:** 2 creations per 24 hours, 5 per week, and each idea once a week.
6. **Admin approval:** the admin is notified of every submission, and points are given only after approval.
7. **Evidence for the admin:** both photos, the code, the student's history and a similar-photo warning.
8. **Reasons required** for rejection, and a penalty for fake submissions.
9. **Community flags:** 3 flags hide a creation and send it back to the admin, who can withdraw the
   approval and take the points back.
10. **Audit trail:** every point change is written to a points log with a reason.
11. **Leaderboard** counts only verified points.

No automatic check is perfect (for example a photo of a screen), which is why an admin reviews everything.

## Honest note on data
Bin locations come from our campus dataset. **Fill levels are simulated** because there are no sensors
yet. A sensor would write the same readings (bin, fill %, time) that the simulator writes today.

## Tech stack
Python, Streamlit, SQLite (WAL mode), Folium and streamlit-folium, Plotly, pandas, NumPy,
scikit-learn, XGBoost, bcrypt, Pillow. Optional: Gemini or Claude API for the Reuse Coach.

## Run it locally (Windows)
```
git clone https://github.com/Harsh3050-art/wastewise-campus.git
cd wastewise-campus
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Create `.streamlit\secrets.toml`:
```
ADMIN_INVITE_CODE = "choose-a-secret"
CODE_SALT = "some-random-words"
```
Start the app, and the simulator in a **second terminal** (with `venv` activated):
```
streamlit run Home.py
python -m ml.simulator --live --interval 10 --step-minutes 10
```
The first start builds the database from `data/bins.csv`, creates 28 days of simulated history and
trains the model, which takes about a minute.

**Accounts:** sign up as a student. To create an admin, enter the invite code from `secrets.toml`
on the sign-up form.

**Optional AI for the Reuse Coach:** add `GEMINI_API_KEY = "..."` (free from Google AI Studio) or
`ANTHROPIC_API_KEY = "..."` to `secrets.toml`. Without a key, the Reuse Coach uses its saved library.

**Useful commands**
```
python -m ml.simulator --backfill-days 28   rebuild realistic bin levels and history
python -m ml.simulator --advance-hours 24   fast-forward the simulation
python -m ml.forecast --train               retrain the forecast model
python -m ml.validate_forecast              compare ML with a constant-rate estimate
```

## Project structure
```
Home.py                 login, signup and home
pages/                  Campus Map, Reuse Coach, Leaderboard, Profile,
                        Notifications, Admin Dashboard, Share Creation
services/               auth, bins, reports, cleaning, notifications, points,
                        submissions, coach, leaderboard, profile, summary, bootstrap
ml/                     simulator, forecast model, validation, saved models
data/                   bins.csv, fallback_ideas.json, facts.json
```

## Security
Passwords are hashed with bcrypt. Admin sign-up needs an invite code. Secrets, the database and
uploaded photos are not in the repository. Photos are limited in size and re-encoded, and reports and
submissions are rate-limited.

## Limitations and next steps
- Fill levels are simulated. Next: ESP32 boards with ultrasonic sensors sending readings to a server endpoint.
- SQLite is fine for a campus pilot. A real deployment should use Postgres.
- Photo checks cannot stop every trick, so an admin reviews every creation.
- Retrain the forecast on real sensor readings once they exist.
- Mobile app with push notifications, and a pilot on campus.

## References
- Solid Waste Management Rules, 2026 (four-stream segregation: wet, dry, sanitary and special care).
  Our `recyclable` bins belong to the dry stream, and `ewaste` and `hazardous` bins to special care.
- Bin dataset: our campus bin dataset (`data/bins.csv`).