# Plan: Sistema de Alertas de Trading

## Estado actual (v3 — funcional)

| Archivo | Rol |
|---------|-----|
| `config.py` | Umbrales y símbolos |
| `indicators.py` | RSI, MACD, BB, Golden/Death Cross, VIX, Stoch RSI, ATR, Volume |
| `alerts.py` | Envío Telegram + historial en `alerts_history.json` |
| `monitor.py` | Loop principal + cooldowns + confluencia scoring |
| `scoring.py` | Sistema de puntuación alcista/bajista por confluencia |
| `web.py` | Flask — dashboard, API config, drawings, history |
| `drawings.json` | Líneas de dibujo persistidas |
| `templates/index.html` | Dashboard completo (ver detalle abajo) |

**Símbolos monitoreados:** BTC-USD, ETH-USD, ^GSPC, ^NDX, ^VIX
**Intervalo:** cada 1D | **Cooldown anti-spam:** 24h

**Correr monitor:** `python monitor.py`
**Correr dashboard:** `python web.py` → [localhost:5050](http://localhost:5050)

---

## Dashboard — funcionalidades implementadas

### Charts

- [x] Velas 1D BTC desde 2020, vista filtrada al último año al cargar
- [x] Bollinger Bands + EMA rápida/lenta overlay (toggle on/off)
- [x] Volumen como histograma (verde/rojo) en franja inferior (toggle)
- [x] Sub-paneles overlay en el chart de precio: RSI, MACD, Stoch (toggle independiente)
- [x] Charts separados: RSI + MA(14), MACD (12,26,9), Stochastic RSI
- [x] Resize handle en cada chart (arrastrar borde inferior)
- [x] Botón maximizar en cada chart (Escape para cerrar)
- [x] Crosshair sincronizado entre todos los charts

### Herramienta de dibujo (✏)

- [x] Líneas horizontales, verticales y de tendencia
- [x] Drag para mover líneas después de crearlas
- [x] Tecla Supr para eliminar línea seleccionada
- [x] Borrar línea individual o todas
- [x] Color picker
- [x] Persistencia en `drawings.json` (sobreviven al recargar)

### Semáforos y confluencia

- [x] Semáforo verde/rojo por indicador (estado actual, no cruces puntuales)
- [x] Panel de confluencia: barras alcista/bajista con scoring
- [x] ATR amplifica la dirección dominante (+1 al score)
- [x] Umbral configurable desde ⚙ Umbrales

### UI / UX

- [x] Sidebar de señales colapsable (botón lateral fijo)
- [x] Responsive para móvil (< 768px)
- [x] Presets MACD: Estándar (12,26,9), Crypto 1D (8,21,5), EMA 50/200 (50,200,9)
- [x] Configuración de umbrales persistida en `web_config.json`
- [x] Historial de alertas con tabla

---

## Mejoras planificadas

### ✅ Fase 2 — Dashboard web (completado)

### ✅ Fase 3 — Indicadores adicionales (completado)

### ✅ Fase 4 — Señales combinadas / confluencia (completado)

### Fase 5 — Mejoras técnicas

- [ ] Modo `--dry-run` para probar sin enviar Telegram
- [ ] Tests unitarios para cada función en `indicators.py`
- [ ] Soporte para intervalos intradiarios (1h, 4h) además del diario
- [ ] Migrar historial de JSON a SQLite

### Fase 6 — Alertas enriquecidas

- [ ] Adjuntar gráfico (matplotlib) en el mensaje de Telegram
- [ ] Incluir contexto: precio actual, % cambio 24h
- [ ] Botones inline en Telegram para silenciar/ver más detalles

---

## Próximo paso recomendado

**Fase 5** — Mejoras técnicas o **Fase 6** — Alertas enriquecidas.
