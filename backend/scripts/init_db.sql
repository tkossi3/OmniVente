-- ============================================================================
--  OmniVente — initialisation PostgreSQL
--  Exécution :  sudo -u postgres psql -f scripts/init_db.sql
-- ============================================================================

-- ---------- 1. Utilisateur et base ----------
DROP DATABASE IF EXISTS omnivente_db;
DROP ROLE IF EXISTS omnivente;

CREATE ROLE omnivente WITH LOGIN PASSWORD 'change_me_2026';
CREATE DATABASE omnivente_db OWNER omnivente ENCODING 'UTF8' TEMPLATE template0;

\connect omnivente_db

SET ROLE omnivente;

-- ---------- 2. Tables ----------
CREATE TABLE tenants (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(80)  NOT NULL UNIQUE,
    company         VARCHAR(160) NOT NULL,
    sector          VARCHAR(120),
    legal_form      VARCHAR(40),
    tax_id          VARCHAR(60),
    manager         VARCHAR(120),
    phone           VARCHAR(40),
    email           VARCHAR(160),
    website         VARCHAR(160),
    address         VARCHAR(240),
    city            VARCHAR(80)  DEFAULT 'Lomé',
    country         VARCHAR(80)  DEFAULT 'Togo',
    currency        VARCHAR(10)  DEFAULT 'FCFA',
    pickup_point    VARCHAR(240),
    delivery_zone   VARCHAR(240),
    opening_hours   VARCHAR(160),
    about           TEXT,
    integrations    JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ref         VARCHAR(20)  NOT NULL,
    position    INTEGER      NOT NULL,          -- numéro tapé par le client
    name        VARCHAR(160) NOT NULL,
    price       NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    quantity    INTEGER      NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    in_stock    BOOLEAN      NOT NULL DEFAULT TRUE,
    category    VARCHAR(80),
    CONSTRAINT uq_product_ref UNIQUE (tenant_id, ref)
);
CREATE INDEX idx_products_tenant ON products(tenant_id, position);

CREATE TABLE clients (
    id             SERIAL PRIMARY KEY,
    tenant_id      INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name           VARCHAR(160) NOT NULL DEFAULT 'Client',
    channel        VARCHAR(20)  NOT NULL CHECK (channel IN ('whatsapp','instagram','messenger','email')),
    external_id    VARCHAR(160) NOT NULL,       -- numéro WhatsApp, PSID Meta ou e-mail
    phone          VARCHAR(40),
    email          VARCHAR(160),
    location       VARCHAR(240),
    session_state  JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_client_channel UNIQUE (tenant_id, channel, external_id)
);
CREATE INDEX idx_clients_tenant ON clients(tenant_id, last_seen_at DESC);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id   INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    reference   VARCHAR(30) NOT NULL UNIQUE,
    quantity    INTEGER     NOT NULL DEFAULT 1 CHECK (quantity > 0),
    amount      NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    channel     VARCHAR(20) NOT NULL CHECK (channel IN ('whatsapp','instagram','messenger','email')),
    status      VARCHAR(20) NOT NULL DEFAULT 'preparer'
                CHECK (status IN ('preparer','livraison','retrait','termine','probleme')),
    fulfilment  VARCHAR(20) NOT NULL CHECK (fulfilment IN ('livraison','retrait')),
    slot        VARCHAR(120),                   -- jour et heure convenus
    place       VARCHAR(240),                   -- adresse, coordonnées GPS ou boutique
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_orders_board ON orders(tenant_id, status, created_at DESC);

CREATE TABLE messages (
    id          SERIAL PRIMARY KEY,
    tenant_id   INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id   INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    channel     VARCHAR(20) NOT NULL CHECK (channel IN ('whatsapp','instagram','messenger','email')),
    direction   VARCHAR(10) NOT NULL CHECK (direction IN ('in','out')),
    body        TEXT        NOT NULL,
    step        VARCHAR(30),                    -- étape de la machine d'état
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_thread ON messages(client_id, created_at);
CREATE INDEX idx_messages_stats  ON messages(tenant_id, direction, created_at);

-- ---------- 3. Commerçant témoin du Hackathon LSC 2026 ----------
INSERT INTO tenants (slug, company, sector, legal_form, tax_id, manager, phone, email, website,
                     address, city, country, currency, pickup_point, delivery_zone, opening_hours, about)
VALUES ('kino-steak', 'Tinos TechLogistics', 'Distribution & logistique', 'SARL', '1000487621',
        'Afi Kinvi', '+228 90 00 11 22', 'ventes@kinosteak.tg', 'kinosteak.tg',
        '142, rue des Hydrocarbures, Tokoin',
        'Lomé', 'Togo', 'FCFA', 'Boutique Tokoin, en face de la station CAP',
        'Lomé et périphérie · livraison sous 24 h', 'Lun–Sam · 08h00 – 19h00',
        'Tinos TechLogistics distribue des packs de produits et services logistiques aux commerçants et PME du Grand Lomé.');

-- ---------- 4. Catalogue officiel ----------
INSERT INTO products (tenant_id, ref, position, name, price, quantity, in_stock, category)
SELECT t.id, v.ref, v.position, v.name, v.price, v.quantity, v.quantity > 0, v.category
FROM tenants t,
     (VALUES ('P01', 1, 'Pack Basic',         10000, 42,  'Packs'),
             ('P02', 2, 'Pack Pro',           25000, 18,  'Packs'),
             ('P03', 3, 'Pack Entreprise',    50000, 0,   'Packs'),
             ('P04', 4, 'Produit A',          15000, 64,  'Produits'),
             ('P05', 5, 'Produit B',          30000, 27,  'Produits'),
             ('P06', 6, 'Service Livraison',   5000, 999, 'Services'),
             ('P07', 7, 'Abonnement Mensuel', 20000, 120, 'Services'),
             ('P08', 8, 'Formation',          75000, 12,  'Formation')
     ) AS v(ref, position, name, price, quantity, category)
WHERE t.slug = 'kino-steak';

-- ---------- 5. Droits ----------
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO omnivente;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO omnivente;

\echo '✅ Base omnivente_db prête : 5 tables, 1 commerçant, 8 références.'
