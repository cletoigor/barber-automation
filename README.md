# barber-automation

Automates weekly beard appointment booking at a BestBarbers-hosted barbershop via the BestBarbers API. Finds the next available Friday slot within preferred hours (09:30–11:00), books it, and optionally updates a Google Calendar event when the time differs from the default.

## Architecture

![Architecture](docs/architecture.svg)

Read left to right. The two authentication paths — an email/password login and the
cached-token fallback — converge into a single resolved token before the booking loop
begins. Three gates stand between the script and anything that touches the outside
world: `--dry-run`, the `already_booked_this_week()` idempotency check, and the
fail-closed token refresh, which backs up the existing token and only overwrites it on
success. Google Calendar writes go through a Claude subprocess rather than a direct API
client.

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
python3 book.py                         # next available slot (default barber, default service)
python3 book.py --barber 13001          # specific barber
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

# Barbers: see the table below for the IDs in your shop
DEFAULT_BARBER_ID=13000

# Subscription services: see the table below
DEFAULT_SERVICES=47000
```

All values fall back to the defaults above if the variable is not set. For multiple services, use a comma-separated list: `DEFAULT_SERVICES=47000,47001`.

## Authentication

Run `get_token.py` once to save the session token locally. The scripts will use `token.json` automatically on subsequent runs.

## Barbers

| ID    | Name      |
|-------|-----------|
| 13000 | Barber A  |
| 13001 | Barber B  |
| 13002 | Barber C  |
| 13003 | Barber D  |

IDs above are placeholders. Read the real ones for your shop from the booking
site's network traffic (`capture.py` helps) and set them in `.env`.

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
