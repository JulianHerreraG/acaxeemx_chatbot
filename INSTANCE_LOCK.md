# Sistema de Lock de Instancia

## Problema Resuelto

Cuando múltiples instancias del bot se ejecutan simultáneamente, todas reciben mensajes de Telegram. Esto causa:
- Respuestas duplicadas
- Conflictos en la base de datos
- Consumo innecesario de recursos

## Solución Implementada

Un **sistema de locking distribuido** basado en Firebase Realtime Database que asegura:

1. **Solo una instancia activa**: El bot solo procesa mensajes si tiene el "lock"
2. **Failover automático**: Si la instancia activa falla, la siguiente toma el control
3. **Timeout inteligente**: Si una instancia no refresca el lock en 30 segundos, se considera muerta
4. **Sin punto único de fallo**: El lock está en Firebase, no en un servidor adicional

## Cómo Funciona

```
┌─ Instancia 1                ┌─ Instancia 2                ┌─ Instancia 3
│                             │                             │
├─ Intenta adquirir lock      ├─ Intenta adquirir lock      ├─ Intenta adquirir lock
│  ✅ ÉXITO → ACTIVA          │  ⏳ ESPERANDO                │  ⏳ ESPERANDO
│                             │                             │
├─ Procesa mensajes           ├─ Monitorea /bot_lock        ├─ Monitorea /bot_lock
├─ Refresca lock c/5 msg      │                             │
│  └─ timestamp actualizado   │                             │
│                             │                             │
│ [ERROR: proceso muere]      │  ❌ Lock expiró             │
│ ✅ Lock liberado            │  ✅ Toma lock               │
│                             │  Procesa mensajes...       │
```

## Componentes

### `app/utils/instance_lock.py`

Clase `InstanceLock` que:
- **Adquirir**: `acquire()` - espera/fuerza el lock
- **Refrescar**: `refresh()` - actualiza timestamp cada mensaje
- **Liberar**: `release()` - suelta el lock al cerrar
- **Expiración**: 30 segundos sin refresh = lock muerto

### `app/bot/telegram_bot.py`

Integración con el flujo del bot:
1. Antes de `infinity_polling()`, adquiere el lock
2. `LockRefresher` middleware refresca el lock en cada mensaje
3. Al salir, libera el lock automáticamente

## Estructura en Firebase

```json
{
  "bot_lock": {
    "instance_id": "a1b2c3d4",           // ID único de la instancia
    "acquired_at": 1712178319233         // Timestamp de último refresh
  }
}
```

## Comportamiento en Diferentes Escenarios

### Instancia activa detecta que perdió el lock
- Durante `refresh()`, detecta que otra instancia lo tiene
- Llama `shutdown_handler.shutdown("Otra instancia detectada")`
- Detiene el bot y Flask
- **Sale del proceso completamente**
- La nueva instancia ahora tiene el lock y está activa
- Si se está ejecutando en un orquestador (Docker, supervisord), este reinicia la instancia

### Instancia activa se desconecta de Telegram (pero sigue corriendo)
- El refresh() detecta que otra instancia tomó el lock
- Automáticamente detiene el bot y Flask
- El proceso termina (sale del main())
- Un orquestador externo puede reiniciar si está configurado

### Instancia se bloquea (crash sin cleanup)
- No hay refresh de lock
- Después de ~30 segundos, el lock expira
- Otra instancia en `acquire()` lo detecta y toma control

### Instancia se cierra normalmente
- El finally() en `start_bot()` llama `release()`
- El lock se borra inmediatamente
- Otra instancia lo detecta y toma control al instante

### Dos instancias intentan tomar lock simultáneamente
- Firebase es una base de datos transaccional
- Solo una write llega primero
- La otra espera 5 segundos y reinenta

## Monitoreo

En los logs verás:

```log
# Instancia 1 adquiere el lock
[INFO] Bot de Telegram intentando adquirir lock...
[INFO] Lock adquirido por instancia: a1b2c3d4
[INFO] Bot activo (instancia: a1b2c3d4)
[INFO] Flask corriendo en puerto 5000

# Instancia 2 inicia e intenta adquirir lock
[INFO] Bot de Telegram intentando adquirir lock...
[INFO] Lock en uso por a1b2c3d4. Esperando... (instancia: x9y8z7w6)

# (Esperando...)
[INFO] Lock en uso por a1b2c3d4. Esperando... (instancia: x9y8z7w6)

# Instancia 1 detecta que perdió el lock (Instancia 2 está tomándolo)
[ERROR] ALERTA: Lock fue tomado por otra instancia: x9y8z7w6
[WARNING] === INICIANDO SHUTDOWN: Otra instancia detectada - Lock perdido ===
[INFO] Deteniendo bot de Telegram...
[INFO] Bot detenido
[INFO] Bot detenido. Lock liberado.

# Instancia 2 ahora adquiere el lock exitosamente
[INFO] Lock adquirido por instancia: x9y8z7w6
[INFO] Bot activo (instancia: x9y8z7w6)
[INFO] Flask corriendo en puerto 5000
```

## Timeout Personalizado

Ajusta el timeout de adquisición (default 60 segundos):

```python
instance_lock.acquire(timeout=120)  # Esperar hasta 2 minutos
```

Ajusta el timeout de expiración (default 30 segundos):

En `instance_lock._is_expired()`, cambia `expiry_seconds`:

```python
return (current_time - acquired_at) > (45 * 1000)  # 45 segundos
```

## Testing

Para simular múltiples instancias localmente:

```bash
# Terminal 1
python -m app.main
# [Bot 1 adquiere lock y está activo]

# Terminal 2 (mientras Terminal 1 corre)
python -m app.main
# [Bot 2 intenta lock pero espera...]
# [Mientras espera, Bot 1 detectará que Bot 2 está esperando]
# [Bot 1 se detendrá automáticamente]
# [Bot 2 adquirirá el lock y estará activo]

# Ctrl+C en Terminal 2 → Terminal 1 se reinicia y puede volver a tomar el lock
```

### Comportamiento esperado con Docker/Supervisord

```bash
# Inicia 3 instancias del bot
docker-compose up --scale bot=3

# Resultado:
# - Bot 1 adquiere lock (activo)
# - Bot 2 espera (parado)
# - Bot 3 espera (parado)

# Si Bot 1 falla:
# - Detecta pérdida de lock
# - Se detiene y sale
# - Docker/supervisord reinicia Bot 1
# - Bot 2 puede adquirir lock si está listo
# - O Bot 1 reiniciado adquiere el lock nuevamente
```

## Limitaciones y Consideraciones

- **Latencia**: Hay un delay de ~5 segundos entre que una instancia detecta que el lock expiró y lo toma
- **Firebase**: Requiere conectividad a Firebase Realtime Database (ya es un requisito del bot)
- **Escalabilidad**: Perfecto para 2-3 instancias. Para 100+ considerar un sistema de queue diferente
