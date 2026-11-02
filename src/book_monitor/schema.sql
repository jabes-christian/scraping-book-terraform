CREATE TABLE IF NOT EXISTS executions (
  id           BIGSERIAL PRIMARY KEY,
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ,
  status       TEXT NOT NULL CHECK (status IN ('RUNNING','SUCCESS','FAILED')),
  items_count  INTEGER,
  error        TEXT
);

CREATE TABLE IF NOT EXISTS books (
  id            BIGSERIAL PRIMARY KEY,
  url           TEXT NOT NULL UNIQUE,
  title         TEXT NOT NULL,
  category      TEXT NOT NULL,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS price_history (
  id           BIGSERIAL PRIMARY KEY,
  execution_id BIGINT NOT NULL REFERENCES executions(id),
  book_id      BIGINT NOT NULL REFERENCES books(id),
  price        NUMERIC(10,2) NOT NULL,
  currency     CHAR(3) NOT NULL DEFAULT 'GBP',
  availability TEXT NOT NULL,
  scraped_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (execution_id, book_id)
);

CREATE INDEX IF NOT EXISTS ix_price_history_book ON price_history (book_id, scraped_at DESC);
