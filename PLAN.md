# Plan: Sistema de Alertas de Trading

### Objetivos

Señales de compra y venta de bitcoin

## Estado actual (v3 — funcional)

| Archivo | Rol |
|---------|-----|
| `config.py` | Umbrales y símbolos |
| `indicators.py` | RSI, MACD, BB, Golden/Death Cross, VI, Stoch RSI, ATR, Volume |
| `alerts.py` | Envío Telegram + historial en `alerts_history.json` |
| `monitor.py` | Loop principal + cooldowns + confluencia scoring |
| `scoring.py` | Sistema de puntuación alcista/bajista por confluencia |
| `web.py` | Flask — dashboard, API config, drawings, history |
| `drawings.json` | Líneas de dibujo persistidas |
| `templates/inde.html` | Dashboard completo (ver detalle abajo) |

**Símbolos monitoreados:** solo BTC-USD,
**Intervalo:** cada 1D 4h 1W | **Cooldown anti-spam:** 24h

**Correr monitor:** `python monitor.py`
**Correr dashboard:** `python web.py` → [localhost:5050](http://localhost:5050)

---

## Wireframe

- []  Barra de tabs inferior en móvil (Indicadores,  Dibujo,Señales, Umbrales)
- []  Tabs de Indicadores para desactivar/activar
- []  Tabs de Lapiz editar Lineas de soporte resistencia tendencia
- []  Tabs de info de indicadores en select (Info,Umbrales)

## Dashboard — funcionalidades implementadas

### Charts

- [] Selector de temporalidad: 1D, 4H, 1W (con fade al cambiar)
  Grafico Principal
- [] Velas 1D BTC desde 2020, vista filtrada a los últimos 3 meses al cargar/actualizar
 Indicadores
- []Presets MACD: Estándar (12,26,9), Crypto 1D (8,21,5), EMA 50/200 (50,200,9)
- [] Bollinger Bands + EMA rápida/lenta overlay (toggle on/off)
- [] Volumen como histograma (verde/rojo) en franja inferior (toggle)
- [] Charts separados: RSI + MA(14), MACD (12,26,9), Stochastic RSI
- [] Resize handle en cada chart (arrastrar borde inferior)
- [] Crosshair sincronizado entre todos los chart
- [] Umbrales Stochastic RSI (80/20) con mismo estilo que umbrales RSI

### Herramienta de dibujo (✏)

- [] Líneas horizontales, verticales y de tendencia
- [] Drag para mover líneas después de crearlas
- [] Tecla Supr para eliminar línea seleccionada
- [] Borrar línea individual o todas
- [] Color picker
- [] Persistencia en `drawings.json` (sobreviven al recargar)
- [] Círculos en endpoints de tendencia solo visibles al seleccionar/editar

### Semáforos y confluencia

- [] Semáforo verde/rojo por indicador (estado actual, no cruces puntuales)
- [] Panel de confluencia: barras alcista/bajista con scoring
- [] ATR amplifica la dirección dominante (+1 al score)
- [] Umbral configurable desde ⚙ Umbrales

### UI / U

- [] Responsive para móvil (< 768p)
- [] Eje  con fechas visible en móvil (por encima de la tabbar)
- [] Configuración de umbrales persistida en `web_config.json`
- [] Historial de alertas con tabla

---

## Mejoras planificadas

### Fase 5 — Mejoras técnicas

- [ ] Modo `--dry-run` para probar sin enviar Telegram
- [ ] Tests unitarios para cada función en `indicators.py`
- [ ] Soporte para intervalos intradiarios (1h, 4h) además del diario
- [ ] Migrar historial de JSON a SQLite

### Fase 6 — Alertas enriquecidas

- [ ] Adjuntar gráfico (matplotlib) en el mensaje de Telegram
- [ ] Incluir conteto: precio actual, % cambio 24h
- [ ] Botones inline en Telegram para silenciar/ver más detalles

---

## Próimo paso recomendado

**Fase 5** — Mejoras técnicas o **Fase 6** — Alertas enriquecidas.
