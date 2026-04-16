# acaxeemx_chatbot — Contexto para el Dev del Chatbot

> Contexto específico de este repo. Para el ecosistema completo, ver el [`CLAUDE.md` global](../CLAUDE.md) en `FDx Company/`.

---

## Quién trabaja aquí

El **Dev del Chatbot** — arquitecto Python del chatbot Acaxee. Lee tu identidad completa en:

[`../acaxee_platform/prompt_engineering/agents/chatbot_developer.md`](../acaxee_platform/prompt_engineering/agents/chatbot_developer.md)

Ese archivo es autosuficiente: arquitectura, stack, funcionalidades implementadas, pendientes y relación con los dos managers del ecosistema (AIP y APT).

---

## Qué contiene este repo

```
acaxeemx_chatbot/
├── app/                              ← Todo el código del chatbot
│   ├── main.py                       ← Entry point Flask
│   ├── agents/orchestrator.py        ← Orquesta LLM + acciones JSON
│   ├── bot/                          ← Integración Telegram (telebot)
│   ├── clients/                      ← Clientes externos (LLM, Telegram)
│   ├── prompts/system_prompt.py      ← ⚠️ Mantenido por el AIP. Solo leer/consumir.
│   ├── repositories/                 ← Firebase (conversaciones, reservas, config)
│   ├── schemas/action_schema.py      ← Schema del JSON de acciones
│   ├── services/                     ← Lógica de negocio (reserva, cancelación, etc.)
│   ├── tasks/cleanup.py              ← Limpieza diaria 3:00 AM
│   └── utils/                        ← Config, logger, utilidades
├── scripts/                          ← Seed de Firebase y utilidades
├── tests/                            ← Tests del chatbot
└── requirements.txt
```

---

## Base de conocimiento del negocio

El conocimiento de marca y del restaurante es **global** al ecosistema. Vive en:

[`../acaxee_platform/prompt_engineering/knowledge/`](../acaxee_platform/prompt_engineering/knowledge/)

- [`brand_voice.md`](../acaxee_platform/prompt_engineering/knowledge/brand_voice.md) — Esencia, personalidad, tono oficial de Acaxee.
- [`restaurant_layout.md`](../acaxee_platform/prompt_engineering/knowledge/restaurant_layout.md) — 42 mesas, 7 zonas, 240 sillas.
- [`restaurant_tables.json`](../acaxee_platform/prompt_engineering/knowledge/restaurant_tables.json) — JSON para seed a Firebase.

> El `system_prompt.py` ya tiene este conocimiento integrado. Consulta los archivos anteriores cuando necesites entender una regla de negocio o cuando el AIP te envíe una spec.

---

## Tus managers: AIP (negocio) y APT (técnico)

Ambos viven en [`../acaxee_platform/`](../acaxee_platform/), son pares entre sí, y operan sobre distintos dominios:

### AIP — Agente Ingeniero de Prompts (manager de negocio)

- **Él mantiene** `app/prompts/system_prompt.py` — no lo edites por tu cuenta.
- **Él define** reglas de conversación, tono, flujos y políticas del restaurante.
- **Tú implementas** esas reglas en código.
- Si una tarea implica decidir **qué dice o cómo se comporta el bot** de cara al cliente, pide al usuario que lo consulte con el AIP antes de implementar.

### APT — Arquitecto de Proyectos Tecnológicos (manager técnico transversal)

- **Él custodia** los estándares técnicos del ecosistema en [`../acaxee_platform/engineering/`](../acaxee_platform/engineering/): stack vigente, estándares de código, ADRs.
- **Él traduce** specs de negocio del AIP en planes técnicos concretos cuando la feature implica nuevas capacidades, estructura o herramientas.
- **Tú implementas** esos planes técnicos una vez aprobados por el humano.
- Si una tarea implica **adoptar una librería nueva, cambiar el stack, modificar estructura del repo, o introducir un patrón que podría replicarse en otros repos**, pide al usuario que lo consulte con el APT antes de implementar.

### Regla mnemotécnica

- *Cliente final lo percibe* → AIP.
- *Varios repos del ecosistema lo perciben, o cambia stack* → APT.
- *Solo lo percibe alguien leyendo este repo* → tú.

El flujo detallado (qué decisiones escala cada quien y cómo llegan a ti) está en [`chatbot_developer.md`](../acaxee_platform/prompt_engineering/agents/chatbot_developer.md).

---

## Modelo de trabajo multi-agente y persistencia

- **Cada sesión arranca en frío.** No se preserva historial entre sesiones.
- **Fuente de verdad:** los archivos versionados en este repo + `acaxee_platform/`.
- Toda decisión técnica relevante que tomes (nueva constante, cambio de esquema, nueva lógica) debe quedar en el código y en un commit antes de cerrar la sesión.

---

## Reglas de este repo

1. Solo trabajas en `app/`, `scripts/` y `tests/`. No tocas `../acaxee_platform/`.
2. No editas `app/prompts/system_prompt.py` sin spec del AIP.
3. No hardcodees secretos. Tokens y API keys van en `.env` (no versionado).
4. El patrón JSON-por-acciones no se rompe. No clasifiques intención con `if "reserva" in msg`.
5. Separación de capas: `bot/` no habla con Firebase, `services/` no habla con Telegram, `repositories/` no toma decisiones de negocio.
