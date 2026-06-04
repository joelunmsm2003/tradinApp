SYMBOLS = {
    "crypto": ["BTC-USD", "ETH-USD"],
    "indices": ["^GSPC", "^NDX", "^VIX"],
}

# Umbrales RSI
RSI_OVERSOLD   = 30   # señal alcista cuando cruza hacia arriba
RSI_OVERBOUGHT = 70   # señal bajista cuando cruza hacia abajo

# Multiplicador de volumen para considerar spike (veces el promedio 20d)
VOLUME_SPIKE_MULT = 2.0

# Subida mínima del VIX en una sesión para considerarlo spike (%)
VIX_SPIKE_PCT = 20

# Cuántos minutos entre cada chequeo de mercado
CHECK_INTERVAL_MINUTES = 15

# Horas mínimas entre alertas del mismo símbolo+indicador (anti-spam)
COOLDOWN_HOURS = 24

# Score mínimo de confluencia para disparar alerta combinada
CONFLUENCE_THRESHOLD = 4

# Período de datos históricos para calcular indicadores (monitor)
DATA_PERIOD = "120d"
DATA_INTERVAL = "1d"

# Fecha de inicio para el dashboard web
CHART_START = "2020-01-01"
