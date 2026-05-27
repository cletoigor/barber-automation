"""
Books a subscription beard appointment every Friday.
Tries 09:30 → 10:00 → 10:30 → 11:00. Only books if a slot is available.
If the booked time differs from 09:30, updates the Google Calendar event.

Usage:
    python3 schedule_recurring.py              # next available Friday
    python3 schedule_recurring.py --all        # attempt to book all upcoming Fridays
    python3 schedule_recurring.py --dry-run    # simulate without creating an appointment
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

API = os.getenv("BARBER_API", "https://api.bestbarbers.app")
BARBERSHOP_ID = int(os.getenv("BARBERSHOP_ID", 12345))
CLIENT_ID = int(os.getenv("CLIENT_ID", 99999))
BARBER_ID = int(os.getenv("DEFAULT_BARBER_ID", 13001))
SERVICES = [int(s) for s in os.getenv("DEFAULT_SERVICES", "47000").split(",")]
PREFERRED_HOURS = ["09:30", "10:00", "10:30", "11:00"]
CLAUDE_BIN = "/opt/homebrew/bin/claude"


def get_token():
    email = os.getenv("BARBER_EMAIL")
    password = os.getenv("BARBER_PASSWORD")
    if email and password:
        try:
            r = requests.post(f"{API}/v3/login", json={"email": email, "password": password})
            if r.ok:
                data = r.json()
                token = data.get("token") or data.get("access_token") or (data.get("data") or {}).get("token")
                if token:
                    return token
        except Exception:
            pass
    # Fallback: token salvo em token.json (válido ~60 dias)
    token_file = os.path.join(os.path.dirname(__file__), "token.json")
    if os.path.exists(token_file):
        saved = json.load(open(token_file))
        token = saved.get("@BestBarbers:token", "").strip('"')
        if token:
            print("Usando token salvo em token.json.")
            return token
    sys.exit("Erro: nenhuma credencial disponível. Rode get_token.py primeiro.")


def get_slots(token, date_str):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(
        f"{API}/v3/appointment/available-times",
        params={"type": "client"},
        json={
            "date": date_str,
            "currentHour": datetime.now().strftime("%H:%M"),
            "currentDate": datetime.now().strftime("%Y-%m-%d"),
            "barber_id": BARBER_ID,
            "barbershop_id": BARBERSHOP_ID,
            "time_required": "00:30",
            "services": SERVICES,
        },
        headers=headers,
    )
    if r.status_code != 200:
        return {}
    return r.json()


def pick_hour(slots):
    all_slots = slots.get("morning", []) + slots.get("evening", []) + slots.get("night", [])
    for h in PREFERRED_HOURS:
        if h in all_slots:
            return h
    return None


def already_booked_this_week(token, target_friday: date):
    """Retorna (True, data, hora) se já existe agendamento na semana da sexta-alvo."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API}/v3/client/appointments", headers=headers)
    if not r.ok:
        return False, None, None

    # Semana da sexta: segunda a domingo
    week_start = target_friday - timedelta(days=target_friday.weekday())  # segunda
    week_end = week_start + timedelta(days=6)                             # domingo

    for appt in r.json():
        appt_date = appt.get("simple_date") or (appt.get("date") or "")[:10]
        try:
            d = date.fromisoformat(appt_date)
        except ValueError:
            continue
        if week_start <= d <= week_end and appt.get("status") not in ("cancelled", "canceled"):
            return True, appt_date, appt.get("start_hour", "")[:5]

    return False, None, None


def update_appointment(token, appointment_id, date_str, start_hour):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.put(
        f"{API}/v3/appointments/update-appointment",
        json={
            "id": appointment_id,
            "date": date_str,
            "start_hour": start_hour,
            "barber_id": BARBER_ID,
            "barbershop_id": BARBERSHOP_ID,
            "servicesId": SERVICES,
            "time_required": "00:20",
            "client_id": CLIENT_ID,
            "type": "signature",
            "currentHour": datetime.now().strftime("%H:%M"),
            "currentDate": datetime.now().strftime("%Y-%m-%d"),
        },
        headers=headers,
    )
    r.raise_for_status()
    return r.json()


def book(token, date_str, start_hour, dry_run=False):
    body = {
        "date": date_str,
        "currentHour": datetime.now().strftime("%H:%M"),
        "currentDate": datetime.now().strftime("%Y-%m-%d"),
        "barber_id": BARBER_ID,
        "servicesId": SERVICES,
        "time_required": "00:30",
        "client_id": CLIENT_ID,
        "start_hour": start_hour,
        "type": "signature",
        "barbershop_id": BARBERSHOP_ID,
        "source": "client_mobile_app",
        "without_preference": False,
    }
    if dry_run:
        return {"dry_run": True, "date": date_str, "start_hour": start_hour}
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API}/v3/appointments/new-appointment", json=body, headers=headers)
    r.raise_for_status()
    return r.json()


def _run_claude(prompt, tools, dry_run_label=None, dry_run=False):
    """Executa claude -p com as ferramentas especificadas."""
    if dry_run:
        print(f"    [DRY RUN] {dry_run_label}")
        return True
    if not os.path.exists(CLAUDE_BIN):
        print(f"    ⚠ claude não encontrado em {CLAUDE_BIN}.")
        return False
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--allowedTools", tools],
            capture_output=True, text=True, timeout=90,
            env={**os.environ, "HOME": os.path.expanduser("~")},
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("    ⚠ Timeout ao chamar claude.")
        return False
    except Exception as e:
        print(f"    ⚠ Erro ao chamar claude: {e}")
        return False


def update_calendar(date_str, hour, dry_run=False):
    """Atualiza o evento do Google Calendar para o horário agendado."""
    h, m = map(int, hour.split(":"))
    end_total = h * 60 + m + 30
    end_hour = f"{end_total // 60:02d}:{end_total % 60:02d}"

    prompt = (
        f"Update the Google Calendar event titled 'Barba — the barbershop (barber B)' "
        f"on {date_str} to start at {hour} and end at {end_hour} "
        f"(timezone America/Sao_Paulo). "
        f"Use list_events to find it first, then update_event with the event ID."
    )
    ok = _run_claude(
        prompt,
        "mcp__claude_ai_Google_Calendar__list_events,mcp__claude_ai_Google_Calendar__update_event",
        dry_run_label=f"Atualizaria Calendar: {date_str} → {hour}–{end_hour}",
        dry_run=dry_run,
    )
    if ok:
        print(f"    ✓ Google Calendar atualizado: {date_str} → {hour}")
    else:
        print(f"    ⚠ Falha ao atualizar Calendar.")


def notify_no_slot(date_str, dry_run=False):
    """Cria evento de alerta no Google Calendar quando nenhum horário está disponível."""
    prompt = (
        f"Create a Google Calendar event on {date_str} at 09:00 (America/Sao_Paulo) "
        f"with summary '⚠️ Barba NÃO agendada — agendar manualmente' "
        f"and description 'Nenhum horário disponível entre 09:30 e 11:00 com barber B na the barbershop. Agendar pelo app.' "
        f"Set color to Tomato (colorId 11) and add a popup reminder 30 minutes before. "
        f"End time: 09:15."
    )
    ok = _run_claude(
        prompt,
        "mcp__claude_ai_Google_Calendar__create_event",
        dry_run_label=f"Criaria alerta no Calendar: {date_str} sem horário disponível",
        dry_run=dry_run,
    )
    if ok:
        print(f"    ✓ Alerta criado no Google Calendar para {date_str}.")
    else:
        print(f"    ⚠ Falha ao criar alerta no Calendar.")


def next_fridays(n=24):
    today = date.today()
    days_ahead = (4 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # já é sexta, pular para próxima
    first = today + timedelta(days=days_ahead)
    return [first + timedelta(days=7 * i) for i in range(n)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Tentar agendar todas as datas futuras")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token = get_token()
    dates = next_fridays(24)

    booked = []
    for d in dates:
        date_str = d.strftime("%Y-%m-%d")
        slots = get_slots(token, date_str)
        hour = pick_hour(slots)
        if not hour:
            print(f"  {date_str} (sexta): sem horário disponível (09:30–11:00)")
            notify_no_slot(date_str, dry_run=args.dry_run)
            if not args.all:
                break
            continue

        booked_already, existing_date, existing_hour = already_booked_this_week(token, d)
        if booked_already:
            print(f"  {date_str} (sexta): já agendado nesta semana → {existing_date} às {existing_hour}, pulando.")
            if not args.all:
                break
            continue

        print(f"  {date_str} (sexta): slot disponível → {hour}")
        result = book(token, date_str, hour, dry_run=args.dry_run)
        booked.append({"date": date_str, "hour": hour, "result": result})
        print(f"    ✓ Agendado: {date_str} às {hour}")

        if hour != "09:30":
            update_calendar(date_str, hour, dry_run=args.dry_run)

        if not args.all:
            break  # por padrão, agenda só a próxima

    print(f"\nTotal agendado: {len(booked)}")
    return booked


if __name__ == "__main__":
    main()
