"""Renova o token do BestBarbers via login manual no browser.

Grava em token.json o localStorage completo (a chave usada pelos scripts é
`@BestBarbers:token`). Só sobrescreve o arquivo quando um token válido é
capturado — um login que falha ou expira nunca destrói a credencial atual.
"""

import asyncio
import base64
import json
import os
import shutil
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE_DIR, "token.json")
BACKUP = os.path.join(BASE_DIR, "token.json.bak")
PROFILE_DIR = os.path.join(BASE_DIR, "chrome-profile")
TOKEN_KEY = "@BestBarbers:token"
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
_SHOP = os.getenv("BARBERSHOP_ID", "10000")
LOGIN_URL = os.getenv(
    "BARBER_BOOKING_URL", f"https://agendamentos.bestbarbers.app/barbershop/id/{_SHOP}")
TIMEOUT_SECONDS = 300


def decode_expiry(token):
    """Retorna o datetime de expiração do JWT, ou None se não der para ler."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp")
        return datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
    except Exception:
        return None


def extract_token(storage):
    """Pega o token do localStorage, sem aspas. String vazia se não houver."""
    return (storage.get(TOKEN_KEY) or "").strip('"').strip()


async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(LOGIN_URL)

        print("\n" + "=" * 60)
        print("  Faça LOGIN no site que abriu no browser.")
        print("  O script detecta o token sozinho e fecha o browser.")
        print("=" * 60 + "\n")
        print("Aguardando login...")

        storage, token = {}, ""
        for _ in range(TIMEOUT_SECONDS // 2):
            if page.is_closed():
                print("\n✗ Browser fechado antes de capturar o token.")
                break
            try:
                storage = await page.evaluate("() => ({ ...localStorage })")
                token = extract_token(storage)
                if token:
                    print("✓ Token detectado!")
                    break
            except Exception:
                pass  # navegação em curso — tenta de novo
            await asyncio.sleep(2)

        await context.close()

        if not token:
            print(
                f"\n✗ Nenhum token capturado (chave {TOKEN_KEY} ausente no "
                f"localStorage).\n  {OUTPUT} foi mantido intacto.",
                file=sys.stderr,
            )
            return 1

        if os.path.exists(OUTPUT):
            shutil.copy2(OUTPUT, BACKUP)

        with open(OUTPUT, "w") as f:
            json.dump(storage, f, indent=2)

        print(f"✓ Token salvo em {OUTPUT}")
        expiry = decode_expiry(token)
        if expiry:
            dias = (expiry - datetime.now(tz=timezone.utc)).days
            print(f"  Expira em {expiry.astimezone():%d/%m/%Y %H:%M} ({dias} dias)")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
