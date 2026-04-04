# ACAXEE — Roadmap de Producto y Escalabilidad
### Documento para Equipo de Negocios

---

## Resumen Ejecutivo

ACAXEE cuenta hoy con un asistente virtual funcional capaz de gestionar reservaciones en tiempo real a través de Telegram. Este documento describe cómo ese núcleo tecnológico puede crecer de forma ordenada hacia una plataforma completa de atención al cliente, gestión de la marca y relación con el comensal — sin necesidad de reconstruir lo que ya existe.

El principio de diseño es simple: **cada nueva funcionalidad se construye encima de lo que ya está operando**, no en paralelo ni desde cero.

---

## Estado Actual — Lo que ya existe

> Ver: [Mapa de Infraestructura Actual](mapa_actual.svg)

### Capacidades operativas hoy

| Funcionalidad | Estado |
|---|---|
| Reservar mesa | ✅ Operativo |
| Cancelar reserva | ✅ Operativo |
| Modificar reserva | ✅ Operativo |
| Consultar disponibilidad con alternativas | ✅ Operativo |
| Validación de horario (2PM–9PM) | ✅ Operativo |
| Aviso de seguridad alimentaria | ✅ Operativo |
| Historial conversacional del día | ✅ Operativo |
| Alta disponibilidad (instancia única garantizada) | ✅ Operativo |
| Limpieza automática diaria 3AM | ✅ Operativo |
| Despliegue continuo desde GitHub | ✅ Render |

---

## Arquitectura de Escalabilidad

> Ver: [Mapa de Visión de Plataforma](mapa_futuro.svg)

El proyecto está diseñado en capas independientes. Cada capa puede crecer sin afectar a las demás.

- Agregar **WhatsApp** es conectar un nuevo canal al orquestador que ya existe.
- Agregar el **módulo de menú** es añadir un servicio nuevo sin tocar los de reservaciones.
- Cada nueva capacidad del LLM es un **bloque independiente** en el esquema de acciones JSON.

---

## Roadmap de Producto

### Fase 1 — Fundamentos Inteligentes

Lo que ya se tiene más las mejoras inmediatas de mayor impacto.

- **Asistente de reservaciones completo** — operativo hoy
- **Memoria de cliente recurrente** — el bot reconoce a clientes que han reservado antes y los saluda por nombre
- **Notificaciones de confirmación** — mensaje automático al cliente antes de su reserva
- **Respuestas sobre el menú** — el bot informa sobre platillos, ingredientes del mar y restricciones alimentarias en base a una carta cargada en Firebase
- **Panel de administración básico** — vista web para que el equipo del restaurante vea las reservas del día

**Valor para el negocio:** El restaurante tiene una herramienta de atención 24/7 que reduce la carga operativa en llamadas y mensajes manuales.

---

### Fase 2 — Expansión de Canales

- **WhatsApp Business (Meta)** — el canal de mayor penetración en México; misma lógica del bot, nuevo canal de entrada
- **Instagram Direct** — captura de clientes que descubren el restaurante por redes sociales
- **Widget web** — chat embebido en el sitio `acaxeemazatlan.com` para visitantes que llegan al sitio
- **Identificación unificada del cliente** — un cliente que escribe por WhatsApp o Instagram es reconocido como el mismo en el sistema

**Valor para el negocio:** El restaurante aparece donde están los clientes. Se elimina la fragmentación entre canales.

---

### Fase 3 — CRM y Dashboard de Marca

Una aplicación propia para el equipo del restaurante.

#### Módulo de Operaciones
- Vista en tiempo real de reservas del día, semana y mes
- Capacidad de confirmar, cancelar o mover reservas manualmente
- Indicador de ocupación por hora y fecha
- Tomar control del chat (intervención humana cuando se necesite)

#### Módulo de Clientes (CRM)
- Perfil de cada cliente: historial de visitas, preferencias, alergias registradas
- Segmentación: clientes frecuentes, clientes nuevos, clientes que no han regresado
- Notas internas del equipo sobre clientes VIP

#### Módulo de Marketing
- Envío de mensajes segmentados (promociones, eventos especiales, temporada)
- Campañas para recuperar clientes inactivos
- Métricas de respuesta y conversión

#### Módulo de Análisis
- Horas de mayor demanda
- Platillos más consultados
- Tasa de conversión del bot (consultas → reservas confirmadas)
- Origen del cliente (Telegram, WhatsApp, Instagram, web)

**Valor para el negocio:** El restaurante deja de operar reactivamente y empieza a tomar decisiones basadas en datos reales de sus propios comensales.

---

### Fase 4 — Experiencia Avanzada

- **Agente proactivo** — el sistema detecta que un cliente habitual no ha reservado en el mes y le envía un mensaje personalizado
- **Lista de espera inteligente** — si no hay disponibilidad, el cliente entra a una lista y el bot le avisa automáticamente si se libera un lugar
- **Solicitudes especiales** — decoraciones, cumpleaños, menús personalizados coordinados desde el chat
- **Integración con pagos** — reserva con anticipo o pago de consumo mínimo desde el chat
- **Reseñas post-visita** — el bot envía automáticamente una solicitud de reseña (Google, TripAdvisor) después de la visita

---

## Infraestructura Técnica

### Hoy

| Componente | Tecnología | Rol |
|---|---|---|
| Código fuente | GitHub | Control de versiones y CI/CD |
| Despliegue | Render | Hosting del bot, despliegue automático |
| Base de datos | Firebase RTDB | Conversaciones y reservaciones |
| IA / LLM | GitHub Models (gpt-4o-mini) | Interpretación de lenguaje natural |
| Canal | Telegram | Interfaz con el cliente |

### Crecimiento planificado

| Componente | Propósito |
|---|---|
| Canales adicionales | WhatsApp Cloud API, Instagram Graph API |
| Base de datos de clientes | Firebase Firestore para perfiles CRM |
| Almacenamiento de medios | Firebase Storage para carta y multimedia |
| Autenticación del equipo | Firebase Auth con roles (admin, staff) |
| App CRM / Dashboard | Por definir |
| Pagos | Por definir |
| Analytics avanzado | Firebase Analytics + BigQuery |

### Por qué esta infraestructura escala bien

- **Firebase** crece con el negocio: de cientos a millones de registros sin cambiar de plataforma
- **Render** permite pasar de un proceso a múltiples servicios independientes con un clic
- **GitHub** como fuente de verdad garantiza trazabilidad de cada cambio en producción
- **La arquitectura de acciones JSON** del bot permite agregar nuevas funcionalidades sin modificar las existentes — cada nueva capacidad es un bloque independiente

---

## Propuesta de App CRM / Dashboard

Una aplicación privada para el equipo de ACAXEE que centraliza la operación del restaurante y la relación con el cliente.

| Módulo | Funciones principales |
|---|---|
| **Operaciones** | Reservas del día · Control del bot · Chat en vivo |
| **CRM Clientes** | Perfiles · Historial de visitas · Alergias · Notas VIP |
| **Marketing** | Campañas · Segmentación · Reseñas automatizadas |
| **Análisis** | Métricas de conversión · Demanda por hora · Origen del cliente |

> El stack tecnológico de esta aplicación está por definir.

---

## Valor para el Negocio — Resumen

| Hoy | Próxima fase | Visión de plataforma |
|---|---|---|
| Reservas por Telegram 24/7 | +WhatsApp e Instagram | CRM propio con datos de clientes |
| Respuesta automática | Memoria de clientes frecuentes | Campañas de marketing propias |
| Sin intervención manual | Dashboard de operaciones | Decisiones basadas en datos |
| 1 canal | 3+ canales unificados | Plataforma completa de marca |

---

## Conclusión

El proyecto ACAXEE no es un chatbot de reservas. Es la base de una plataforma de relación con el cliente construida sobre tecnología moderna, escalable y mantenible. Cada fase entrega valor inmediato al negocio mientras prepara el terreno para la siguiente.

Lo que se construye hoy no se descarta mañana — se extiende.

---

*Documento preparado por el equipo de desarrollo **BucksandBrainsAI***
*Versión 1.1*
