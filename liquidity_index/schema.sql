-- Esquema PostgreSQL para el Liquidity Index.
-- Idempotente: seguro correrlo varias veces (CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS series_economicas (
    id                    SERIAL PRIMARY KEY,
    indicador             VARCHAR(50)  NOT NULL,   -- 'M2SL', 'WALCL', 'RRPONTSYD', 'WTREGEN', 'DGS10'
    fecha                 DATE         NOT NULL,
    valor                 NUMERIC      NOT NULL,
    unidad                VARCHAR(50),
    fuente                VARCHAR(50)  NOT NULL DEFAULT 'FRED',
    fecha_actualizacion   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (indicador, fecha)
);
CREATE INDEX IF NOT EXISTS idx_series_economicas_indicador_fecha
    ON series_economicas (indicador, fecha);

CREATE TABLE IF NOT EXISTS mercado (
    id                    SERIAL PRIMARY KEY,
    indicador             VARCHAR(50)  NOT NULL,   -- 'BTC-USD', 'DXY'
    fecha                 DATE         NOT NULL,
    valor                 NUMERIC      NOT NULL,
    unidad                VARCHAR(50)  DEFAULT 'USD',
    fuente                VARCHAR(50)  NOT NULL DEFAULT 'yfinance',
    fecha_actualizacion   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (indicador, fecha)
);
CREATE INDEX IF NOT EXISTS idx_mercado_indicador_fecha ON mercado (indicador, fecha);

CREATE TABLE IF NOT EXISTS stablecoins (
    id                    SERIAL PRIMARY KEY,
    indicador             VARCHAR(50)  NOT NULL DEFAULT 'stablecoin_total_mcap',
    fecha                 DATE         NOT NULL,
    valor                 NUMERIC      NOT NULL,
    unidad                VARCHAR(50)  DEFAULT 'USD',
    fuente                VARCHAR(50)  NOT NULL DEFAULT 'DefiLlama',
    fecha_actualizacion   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (indicador, fecha)
);

CREATE TABLE IF NOT EXISTS halvings (
    id                    SERIAL PRIMARY KEY,
    fecha                 DATE         NOT NULL UNIQUE,
    numero                INTEGER      NOT NULL,
    es_estimado           BOOLEAN      NOT NULL DEFAULT false,
    notas                 TEXT
);
