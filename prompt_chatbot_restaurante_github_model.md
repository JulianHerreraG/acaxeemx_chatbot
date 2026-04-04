# Implementación de chatbot para restaurante con GitHub Models, Python, Firebase y JSON estructurado por acciones

Quiero que actúes como un **arquitecto de software senior** y **desarrollador Python experto en sistemas conversacionales con LLMs**.

Necesito que me diseñes e implementes un proyecto de **chatbot para restaurante**, totalmente automatizado, usando **Python**, **GitHub Models** con la librería `openai`, **Firebase** para persistencia, y una arquitectura basada en **JSON estructurado por acciones**.

---

## Objetivo del sistema

Quiero construir un chatbot que permita a los usuarios conversar naturalmente para realizar acciones relacionadas con un restaurante, por ejemplo:

- hacer una reserva
- cancelar una reserva
- consultar disponibilidad
- hacer preguntas generales
- continuar una conversación natural

Pero hay una condición muy importante:

**NO quiero clasificación manual con palabras clave** como:

```python
if "reserva" in mensaje.lower():
    ...
```

Quiero que el LLM interprete la intención del usuario y siempre devuelva un JSON fijo con varias acciones posibles, donde cada bloque representa una acción.


Luego, mi código Python leerá ese JSON con if, y según qué acción tenga "estado": true, ejecutará la lógica correspondiente.

Lógica general que quiero implementar

La arquitectura debe seguir este flujo:

El usuario envía un mensaje.
El sistema manda el mensaje al LLM.
El LLM devuelve siempre un JSON con una estructura fija.
El código Python analiza el JSON.
Si una acción operativa está en true, se ejecuta el proceso correspondiente.
Después de ejecutar la acción, el resultado se vuelve a mandar al modelo junto con el contexto de la conversación.
El modelo responde nuevamente en JSON, pero esta vez generando el contenido final en mensaje_respuesta_directo.
Ese mensaje final es el que se envía al usuario.
Regla crítica del JSON

El modelo debe devolver siempre un JSON con exactamente esta estructura base:

```
{
  "fecha_hora_actual": {
    "Hora": "12:00",
    "fecha": "2024-06-01"
  },
  "reserva": {
    "estado": false,
    "nombre": null,
    "numero_personas": null,
    "telefono": null,
    "fecha": null,
    "hora": null
  },
  "cancelar_reserva": {
    "estado": false,
    "nombre": null,
    "telefono": null,
    "fecha": null,
    "hora": null
  },
  "consultar_disponibilidad": {
    "estado": false,
    "fecha": null,
    "hora": null
  },
  "mensaje_respuesta_directo": {
    "estado": true,
    "mensaje": "Buenos días, ¿en qué puedo ayudarte con tu reserva?"
  }
}
```

Regla muy importante sobre fecha_hora_actual

El campo:

"fecha_hora_actual": {
  "Hora": "12:00",
  "fecha": "2024-06-01"
}

NO debe ser generado por el modelo.

Ese bloque será agregado por mi código antes o después del procesamiento para darle al sistema la fecha y hora actual como contexto.

Por lo tanto:

- el modelo debe respetar ese campo

- el modelo no debe inventar ni modificar la fecha u hora actual

- el código es quien controla ese valor

Regla de activación de acciones

Cada bloque del JSON representa una acción posible.

Reglas:
Solo debe ponerse "estado": true en una acción operativa cuando ya estén todos los datos necesarios completos.

Si faltan datos, esa acción debe quedarse en "estado": false.
Si faltan datos o el usuario solo está conversando, el modelo debe activar mensaje_respuesta_directo.

mensaje_respuesta_directo sirve para responder directamente al usuario cuando todavía no se debe ejecutar una acción
Ejemplo:

Si el usuario dice:

"Quiero reservar para mañana"

Entonces NO debe marcar reserva.estado = true, porque faltan datos como:

nombre
teléfono
número de personas
hora

En ese caso debería responder algo así:
```
{
  "fecha_hora_actual": {
    "Hora": "12:00",
    "fecha": "2024-06-01"
  },
  "reserva": {
    "estado": false,
    "nombre": null,
    "numero_personas": null,
    "telefono": null,
    "fecha": "2024-06-02",
    "hora": null
  },
  "cancelar_reserva": {
    "estado": false,
    "nombre": null,
    "telefono": null,
    "fecha": null,
    "hora": null
  },
  "consultar_disponibilidad": {
    "estado": false,
    "fecha": null,
    "hora": null
  },
  "mensaje_respuesta_directo": {
    "estado": true,
    "mensaje": "Claro, te ayudo con tu reserva. ¿Para qué hora, a nombre de quién, para cuántas personas y con qué teléfono?"
  }
}
```

Regla de exclusividad con mensaje_respuesta_directo

Quiero esta lógica estricta:

1. Si mensaje_respuesta_directo.estado = true y contiene un mensaje, el sistema puede responder directamente al usuario.
Pero si una acción operativa está en true y lista para ejecutarse, entonces no debe usarse mensaje_respuesta_directo como respuesta final inmediata.

2. Primero se ejecuta la acción en Python
Luego el resultado de esa acción se manda nuevamente al modelo, Y solo entonces el modelo genera el mensaje final en mensaje_respuesta_directo

En resumen:
Caso 1: faltan datos o solo conversación

- mensaje_respuesta_directo.estado = true
- se responde directo al usuario

Caso 2: acción completa y lista
por ejemplo reserva.estado = true

- Python ejecuta la reserva
- después manda el resultado al modelo, 
- el modelo devuelve el mensaje final dentro de mensaje_respuesta_directo.

Flujo exacto que quiero:

Flujo 1: conversación normal o datos incompletos
Usuario: "Hola"

Modelo devuelve:

1. todas las acciones en false

2. mensaje_respuesta_directo.estado = true

3. El sistema responde directo al usuario

Flujo 2: reserva completa
Usuario: "Quiero reservar mañana a las 8 pm para 4 personas, a nombre de Juan, mi teléfono es 3001234567"

El modelo detecta que ya están todos los datos necesarios

Devuelve:

1. reserva.estado = true

2. todos los campos de reserva completos
3. mensaje_respuesta_directo.estado = false o vacío

4. Python ejecuta la reserva

5. Python obtiene un resultado, por ejemplo:

reserva creada correctamente
o horario no disponible

6. Ese resultado se manda nuevamente al modelo junto con el contexto conversacional
7. El modelo genera el mensaje final en mensaje_respuesta_directo

8. Ese mensaje final se envía al usuario

Flujo 3: consultar disponibilidad

Usuario: "¿Hay mesa mañana a las 7?"

Si la fecha y hora están claras:

1. consultar_disponibilidad.estado = true

2. Python consulta disponibilidad

3. El resultado vuelve al modelo

4. El modelo genera la respuesta final natural en mensaje_respuesta_directo

Flujo 4: cancelar reserva

Usuario: "Cancela mi reserva de mañana a las 8, soy Juan y mi teléfono es 3001234567"

Si están todos los datos requeridos:

1. cancelar_reserva.estado = true

2. Python ejecuta cancelación
3. El resultado vuelve al modelo
4. El modelo responde finalmente en mensaje_respuesta_directo


Acciones que quiero manejar inicialmente:
1. reserva

Debe activarse solo si están completos:

- nombre
- numero_personas
- telefono
- fecha
- hora

2. cancelar_reserva

Debe activarse solo si están completos:

- nombre
- telefono
- fecha
- hora

3. consultar_disponibilidad

Debe activarse solo si están completos:

- fecha
- hora

4. mensaje_respuesta_directo

Debe activarse cuando:

- faltan datos
- el usuario está saludando
- el usuario hace una pregunta general
- el sistema necesita pedir información faltante
todavía no corresponde ejecutar una acción

Requisitos de implementación

OBJETIVO DE DESARROLLO: Quiero que me implementes un proyecto real en Python con esta lógica. Creando un repositorio adecuado para la reproduccibilidad y productizacion de la solucion

Quiero que me entregues:
1. Arquitectura completa

Una arquitectura modular con:

- orquestador principal
- cliente LLM para GitHub Models
- parser/validador del JSON
- servicio de reservas
- servicio de cancelación
- servicio de disponibilidad
- servicio de contexto conversacional
- capa de Firebase
- generador de respuesta final mediante el modelo

2. Estructura de carpetas

Una estructura profesional y simple, por ejemplo:

- app/
- agents/
- services/
- schemas/
- prompts/
- repositories/
- utils/

3. Código base funcional

Quiero código real, no pseudocódigo, usando:

- Python
- integración con GitHub Models usando openai

4. Prompt del modelo

Quiero que redactes el prompt de sistema ideal para que el modelo:

- siempre devuelva JSON válido
- siempre use exactamente la estructura definida
- no agregue texto fuera del JSON
- no invente datos faltantes
- marque acciones en true solo cuando ya tengan todos los datos requeridos
- use mensaje_respuesta_directo cuando falten datos o cuando sea una respuesta conversacional
- respete que fecha_hora_actual la controla el sistema, no el modelo

5. Validación del JSON

Quiero que el código:

- valide el JSON que devuelve el modelo
- maneje errores si viene mal formado
- reintente si el modelo devuelve algo inválido
- normalice valores si hace falta

6. Lógica de ejecución

Quiero que el código haga esto:

- llama al modelo
- recibe JSON
- revisa con if qué acción tiene estado = true
- ejecuta esa acción
- toma el resultado de la acción
- vuelve a llamar al modelo con el contexto y el resultado
- obtiene el mensaje_respuesta_directo
- responde al usuario

7. Firebase

Quiero que el proyecto use Firebase para:

- guardar contexto conversacional temporal
- que borre los chats diariamente a las 3am hora mexico sinaloa
- guardar reservaciones persistentes
- eventualmente guardar datos del restaurante
- guardar datos de clientes recurrentes

Asume esta política:

- el historial del chat se guarda solo por el día
luego puede eliminarse
- las reservas sí se guardan de forma persistente

IMPORTANTE: Debes generar un script aparte para generar la estructura de datos en Realtime Database Firebase. Las credenciales para conectar a la base de datos se encuentran en el archivo "firebase_conection.json", define en que parte de la arquitectura del repositorio debe ir este archivo y ubicalo correctamente. No lo modifiques internamente

- Cada chat debe ser almacenado temporalmente con un identificador llave unico para conservar el contexto temporal del día

8. Estados conversacionales

Quiero que el sistema pueda continuar conversaciones como:

Usuario: "Quiero reservar mañana"

Bot: "Claro, ¿para qué hora, a nombre de quién, para cuántas personas y con qué teléfono?"

Usuario: "A las 8, para 4 personas, a nombre de Juan, mi número es 3001234567"

- El sistema entiende el contexto anterior

- Completa la reserva
- Ejecuta el proceso
- Devuelve la respuesta final

9. Ejemplos completos

Quiero ejemplos reales de:

- saludo
- reserva incompleta
- reserva completa
- cancelación
- consulta de disponibilidad
- respuesta final después de ejecutar una acción
- Formato técnico que debes usar

Usa esta base de integración:

```
from openai import OpenAI

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key="GITHUB_TOKEN"
)
```

Pero adaptado a variables de entorno.

Restricciones importantes:

- No uses clasificación manual por keywords como lógica principal
- No uses reglas rígidas para interpretar intención
- El LLM debe ser quien interprete la intención
- El código Python solo debe:

1. validar JSON
2. decidir qué proceso ejecutar según estado
3. ejecutar la lógica
4. reenviar el resultado al modelo

Todo debe quedar modularizado y preparado para crecer.

Lo que espero como salida:

- No quiero solo ideas.

- Quiero que me entregues:

1. explicación breve de la arquitectura
2. estructura de carpetas
3. archivos principales
4. código funcional base
5. prompt de sistema
6. esquemas JSON
7. flujo de ejecución completo
8. ejemplos de entrada/salida
9. manejo de Firebase
10. validación del JSON
11. lógica de reintento
12. Script que genera la base de datos

Si necesitas asumir algo, asúmelo razonablemente, crea una alerta identificable facilmente por el usuario desarrollador y continúa.

Aquí te dejo además una **versión más corta**, por si quieres algo más directo:

TOKEN = "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"
MODEL = "cambia por la version mini de gtp-4o"  

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=TOKEN,
)

prompt = "hello world"

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "Reemplaza con el contexto diseñado bajo el prompt""
            ),
        },
        {"role": "user", "content": prompt},
    ],
)

print("\nRespuesta:")
print(response.choices[0].message.content)


API_KEY_TELEGRAM: "8621430314:AAH7U3mhruU2LjCpzcTp74CyjWnkIeCF81c"

LIBRERIA PARA EL BOT DE TELEGRAM: telebot

