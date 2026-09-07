"""
Automação de agendamento de assinatura — the barbershop (BestBarbers)

Uso:
    python3 book.py                  # próximo horário disponível com preferências padrão
    python3 book.py --barber 13001   # barbeiro específico (barber B=13001, barber C=13002, etc.)
    python3 book.py --days 5         # buscar horários nos próximos N dias
    python3 book.py --dry-run        # simular sem criar agendamento
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.bestbarbers.app"
BARBERSHOP_ID = 10000
CLIENT_ID = 300000  # the client

# Barbers disponíveis:
# 13001 = barber B | 13002 = barber C | 13000 = barber A | 13003 = barber D
DEFAULT_BARBER_ID = 13000

# Serviços de assinatura disponíveis:
# 47000 = Barba Club | 47001 = Cabelo Club | 47002 = Cabelo e Barba Club
DEFAULT_SERVICES = [47000]  # Barba Club

# Horários preferidos: tenta 09:30 e avança de 30 em 30 min até 11:00
PREFERRED_HOURS = ["09:30", "10:00", "10:30", "11:00"]


def get_token(email: str, password: str) -> str:
    r = requests.post(f"{API}/v3/login", json={"email": email, "password": password})
    r.raise_for_status()
    data = r.json()
    token = data.get("token") or data.get("access_token") or data.get("data", {}).get("token")
    if not token:
        raise ValueError(f"Token não encontrado na resposta: {list(data.keys())}")
    return token


def get_available_slots(token: str, barber_id: int, date: str, services: list) -> dict:
    """Retorna dict com keys 'morning', 'evening', 'night' — cada um é lista de strings 'HH:MM'."""
    headers = {"Authorization": f"Bearer {token}"}
    # Calcular time_required baseado nos serviços (estimativa: 20min por serviço)
    time_required = f"00:{20 * len(services):02d}"
    body = {
        "date": date,
        "currentHour": datetime.now().strftime("%H:%M"),
        "currentDate": datetime.now().strftime("%Y-%m-%d"),
        "barber_id": barber_id,
        "barbershop_id": BARBERSHOP_ID,
        "time_required": time_required,
        "services": services,
    }
    r = requests.post(
        f"{API}/v3/appointment/available-times",
        params={"type": "client"},
        json=body,
        headers=headers,
    )
    r.raise_for_status()
    return r.json()


def pick_slot(slots, preferred=None):
    """Escolhe o melhor horário disponível com base nas preferências."""
    all_slots = slots.get("morning", []) + slots.get("evening", []) + slots.get("night", [])
    if not all_slots:
        return None
    if preferred:
        for h in preferred:
            if h in all_slots:
                return h
    return all_slots[0]


def create_appointment(token: str, barber_id: int, date: str, start_hour: str, services: list, dry_run: bool = False) -> dict:
    """Cria o agendamento de assinatura."""
    time_required = f"00:{20 * len(services):02d}"
    body = {
        "date": date,
        "currentHour": datetime.now().strftime("%H:%M"),
        "currentDate": datetime.now().strftime("%Y-%m-%d"),
        "barber_id": barber_id,
        "servicesId": services,
        "time_required": time_required,
        "client_id": CLIENT_ID,
        "start_hour": start_hour,
        "type": "signature",
        "barbershop_id": BARBERSHOP_ID,
        "source": "client_mobile_app",
        "without_preference": False,
    }

    if dry_run:
        print(f"[DRY RUN] POST {API}/v3/appointments/new-appointment")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return {"dry_run": True, "body": body}

    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API}/v3/appointments/new-appointment", json=body, headers=headers)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Agendar horário de assinatura na the barbershop")
    parser.add_argument("--barber", type=int, default=DEFAULT_BARBER_ID, help="ID do barbeiro")
    parser.add_argument("--days", type=int, default=7, help="Buscar nos próximos N dias")
    parser.add_argument("--services", nargs="+", type=int, default=DEFAULT_SERVICES, help="IDs dos serviços")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem criar agendamento")
    args = parser.parse_args()

    email = os.getenv("BARBER_EMAIL")
    password = os.getenv("BARBER_PASSWORD")

    if email and password:
        print(f"Fazendo login como {email}...")
        token = get_token(email, password)
        print("Login OK.")
    else:
        # Fallback: usar token salvo em token.json (válido por ~60 dias)
        token_file = os.path.join(os.path.dirname(__file__), "token.json")
        if not os.path.exists(token_file):
            sys.exit("Erro: defina BARBER_EMAIL e BARBER_PASSWORD no .env ou rode get_token.py primeiro.")
        saved = json.load(open(token_file))
        token = saved.get("@BestBarbers:token", "").strip('"')
        print("Usando token salvo em token.json.")

    print(f"\nBuscando horários — barbeiro {args.barber}, próximos {args.days} dias...")
    for i in range(1, args.days + 1):
        date = (datetime.today() + timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            slots = get_available_slots(token, args.barber, date, args.services)
        except requests.HTTPError as e:
            print(f"  {date}: erro {e.response.status_code}")
            continue

        all_available = slots.get("morning", []) + slots.get("evening", []) + slots.get("night", [])
        if not all_available:
            print(f"  {date}: sem horários disponíveis")
            continue

        chosen = pick_slot(slots, PREFERRED_HOURS)
        print(f"  {date}: disponíveis = {all_available}")
        print(f"  → Escolhido: {chosen}")

        if not chosen:
            print(f"  {date}: nenhum slot escolhido")
            continue
        result = create_appointment(token, args.barber, date, chosen, args.services, dry_run=args.dry_run)
        print("\nAgendamento criado com sucesso!")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("\nNenhum horário encontrado nos próximos dias.")


if __name__ == "__main__":
    main()
