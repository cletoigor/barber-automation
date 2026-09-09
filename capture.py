import asyncio
import json
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
_SHOP = os.getenv("BARBERSHOP_ID", "10000")
BOOKING_URL = os.getenv(
    "BARBER_BOOKING_URL", f"https://agendamentos.bestbarbers.app/barbershop/id/{_SHOP}")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "captured_calls.json")
API_CALLS = []


async def handle_request(request):
    if "api.bestbarbers.app" not in request.url:
        return
    body = request.post_data
    entry = {
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "body": body,
    }
    API_CALLS.append(entry)
    print(f"\n>>> {request.method} {request.url}")
    if body:
        print(f"    Body: {body[:300]}")


async def handle_response(response):
    if "api.bestbarbers.app" not in response.url:
        return
    try:
        body = await response.json()
        text = json.dumps(body, ensure_ascii=False)[:600]
    except Exception:
        text = "(não-JSON)"
    print(f"<<< {response.status} {response.url}")
    print(f"    Response: {text}")

    # Atualiza a última entrada com a resposta
    for entry in reversed(API_CALLS):
        if entry["url"] == response.url and "response" not in entry:
            entry["response_status"] = response.status
            try:
                entry["response_body"] = await response.json()
            except Exception:
                pass
            break


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("request", handle_request)
        page.on("response", handle_response)

        print("Abrindo o site da barbearia...")
        await page.goto(BOOKING_URL)

        print("\n" + "=" * 60)
        print("  Faça o fluxo completo de agendamento (Assinatura) no browser.")
        print("  Feche o browser quando terminar (após a confirmação).")
        print("=" * 60 + "\n")

        # Aguarda o browser ser fechado pelo usuário
        await page.wait_for_event("close", timeout=0)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(API_CALLS, f, indent=2, ensure_ascii=False)

        print(f"\n✓ {len(API_CALLS)} chamadas salvas em {OUTPUT_FILE}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
