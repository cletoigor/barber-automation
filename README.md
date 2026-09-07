# barber-automation

Automates weekly beard appointment booking at [the barbershop](https://agendamentos.bestbarbers.app/barbershop/id/12345) via the BestBarbers API. Finds the next available Friday slot within preferred hours (09:30–11:00), books it, and optionally updates a Google Calendar event when the time differs from the default.

## Scripts

### `schedule_recurring.py`
The main automation. Finds the next available Friday, checks that the week isn't already booked, creates the appointment, and triggers a Google Calendar update if needed. If no slot is available, it creates a warning event on the calendar instead.

```bash
python3 schedule_recurring.py           # book the next available Friday
python3 schedule_recurring.py --all     # attempt to book all upcoming Fridays
python3 schedule_recurring.py --dry-run # simulate without creating any appointment
```

### `book.py`
Lower-level script for on-demand booking. Searches across any barber and day range.

```bash
python3 book.py                         # next available slot (default: barber B, Beard Club)
python3 book.py --barber 13002          # specific barber
python3 book.py --days 14              # search up to 14 days ahead
python3 book.py --dry-run
```

### `get_token.py`
Opens the barbershop website in a browser for manual login, then captures and saves the session token to `token.json` (valid for ~60 days).

```bash
python3 get_token.py
```

## Configuration

Create a `.env` file in the project root:

```env
BARBER_API=https://api.bestbarbers.app
BARBERSHOP_ID=12345
CLIENT_ID=99999

# Barbers: 13001=barber B | 13002=barber C | 13000=barber A | 13003=barber D
DEFAULT_BARBER_ID=13001

# Subscription services: 47000=Beard Club | 47001=Hair Club | 47002=Hair+Beard Club
DEFAULT_SERVICES=47000
```

All values fall back to the defaults above if the variable is not set. For multiple services, use a comma-separated list: `DEFAULT_SERVICES=47000,47001`.

## Authentication

Run `get_token.py` once to save the session token locally. The scripts will use `token.json` automatically on subsequent runs.

## Barbers

| ID    | Name      |
|-------|-----------|
| 13001 | barber B    |
| 13002 | barber C     |
| 13000 | barber A |
| 13003 | barber D    |

## Subscription services

| ID    | Service             |
|-------|---------------------|
| 47000 | Beard Club          |
| 47001 | Hair Club           |
| 47002 | Hair & Beard Club   |

## Dependencies

```bash
pip install requests python-dotenv playwright
playwright install chromium  # only needed for get_token.py
```
