import asyncio
import json
import os
from playwright.async_api import async_playwright

OUTPUT = os.path.join(os.path.dirname(__file__), "token.json")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://agendamentos.bestbarbers.app/barbershop/id/12345")

        print("\n" + "=" * 60)
        print("  Faça LOGIN no site que abriu no browser.")
        print("  Quando estiver logado (ver a tela da barbearia), feche o browser.")
        print("=" * 60 + "\n")

        # Aguarda até encontrar o token no localStorage (polling a cada 2s)
        print("Aguardando login...")
        storage = {}
        for _ in range(150):  # até 5 minutos
            try:
                storage = await page.evaluate("() => ({ ...localStorage })")
                if storage.get("@BestBarbers:token") or storage.get("USER"):
                    print("✓ Token detectado!")
                    break
            except Exception:
                pass
            await asyncio.sleep(2)

        data = {k: v for k, v in storage.items()}

        with open(OUTPUT, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✓ Token salvo em {OUTPUT}")
        print(f"  Chaves encontradas: {data['all_keys']}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
