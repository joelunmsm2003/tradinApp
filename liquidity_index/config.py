"""Configuración del Liquidity Index: series, pesos, inversión de signo, TTLs."""

# Series FRED (id -> unidad)
FRED_SERIES = {
    "M2SL":       "USD Bn",
    "WALCL":      "USD Mn",
    "RRPONTSYD":  "USD Bn",
    "WTREGEN":    "USD Bn",
    "DGS10":      "%",
}

# Tickers de mercado vía yfinance
MARKET_TICKERS = {
    "BTC-USD": "BTC-USD",
    "DXY":     "DX-Y.NYB",
}

# Fuente pública de stablecoins (sin API key)
DEFILLAMA_STABLECOINS_URL = "https://stablecoins.llama.fi/stablecoincharts/all"
STABLECOIN_INDICATOR = "stablecoin_total_mcap"

# Variables donde un aumento representa MENOS liquidez (se invierte el signo al normalizar)
INVERT_SIGN = {
    "DXY":        True,
    "DGS10":      True,
    "WTREGEN":    True,
    "RRPONTSYD":  True,
    "M2SL":       False,
    "WALCL":      False,
    STABLECOIN_INDICATOR: False,
}

# Pesos del Liquidity Index v1 — transparentes pero PROVISIONALES.
# No se asumen óptimos; se validan estadísticamente en la Fase 7 (backtest.py).
#
# IMPORTANTE: todos los pesos son POSITIVOS a propósito. La dirección
# (favorable/desfavorable) ya se resuelve en normalization.py vía INVERT_SIGN
# antes de ponderar — un peso negativo aquí volvería a invertir el signo de
# las series que INVERT_SIGN ya invirtió, cancelando la inversión (bug real
# detectado: hacía que DXY alto contara como favorable para la liquidez).
WEIGHTS = {
    "M2SL":       0.20,
    "WALCL":      0.20,
    "RRPONTSYD":  0.15,
    "WTREGEN":    0.15,
    STABLECOIN_INDICATOR: 0.15,
    "DXY":        0.10,
    "DGS10":      0.05,
}

# Halvings históricos + estimación del próximo
HALVINGS = [
    {"fecha": "2012-11-28", "numero": 1, "es_estimado": False, "notas": "Primer halving"},
    {"fecha": "2016-07-09", "numero": 2, "es_estimado": False, "notas": None},
    {"fecha": "2020-05-11", "numero": 3, "es_estimado": False, "notas": None},
    {"fecha": "2024-04-20", "numero": 4, "es_estimado": False, "notas": None},
    {"fecha": "2028-04-20", "numero": 5, "es_estimado": True,  "notas": "Estimado, ajustar por tiempo de bloque real"},
]

# Ventana asimétrica para el análisis de ciclo alrededor de cada halving en backtest.py.
# No es simétrica porque los techos de ciclo históricos llegan 12-18 meses DESPUÉS
# del halving, no en la fecha misma — una ventana corta simétrica se queda corta.
CYCLE_WINDOW_DAYS_BEFORE = 180
CYCLE_WINDOW_DAYS_AFTER = 540
