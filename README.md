# barber-automation

Automação de agendamento de assinatura na [the barbershop](https://agendamentos.bestbarbers.app/barbershop/id/12345) via API do BestBarbers.

## Configuração

Rode `get_token.py` para abrir o site no browser, fazer login e salvar o token localmente em `token.json` (válido ~60 dias):

```bash
python3 get_token.py
```

## Scripts

### `book.py`
Busca o próximo horário disponível e cria o agendamento.

```bash
python3 book.py                      # próximo horário (padrão: barber B, Barba Club)
python3 book.py --barber 13002       # barbeiro específico
python3 book.py --days 14            # buscar nos próximos 14 dias
python3 book.py --dry-run            # simular sem criar agendamento
```

### `schedule_recurring.py`
Agenda a barba toda sexta-feira (tenta 09:30 → 10:00 → 10:30 → 11:00). Se o horário agendado for diferente de 09:30, atualiza automaticamente o Google Calendar.

```bash
python3 schedule_recurring.py        # agenda a próxima sexta disponível
python3 schedule_recurring.py --all  # tenta agendar todas as sextas futuras
python3 schedule_recurring.py --dry-run
```

## Barbeiros

| ID    | Nome      |
|-------|-----------|
| 13001 | barber B    |
| 13002 | barber C     |
| 13000 | barber A |
| 13003 | barber D    |

## Serviços de assinatura

| ID    | Serviço             |
|-------|---------------------|
| 47000 | Barba Club          |
| 47001 | Cabelo Club         |
| 47002 | Cabelo e Barba Club |

## Dependências

```bash
pip install requests python-dotenv playwright
playwright install chromium  # apenas para get_token.py
```
