-- SolTerra Drawing Manager - Database Schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS drawings (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    drawing_number     TEXT NOT NULL UNIQUE,
    title              TEXT NOT NULL,
    description        TEXT DEFAULT '',
    project_id         INTEGER REFERENCES projects(id)   ON DELETE SET NULL,
    category_id        INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    part_number        TEXT DEFAULT '',
    status             TEXT DEFAULT 'Draft' CHECK(status IN ('Draft','Released','Obsolete')),
    current_revision   TEXT DEFAULT 'A',
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_type          TEXT DEFAULT '',
    current_version_id INTEGER
);

CREATE TABLE IF NOT EXISTS drawing_versions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    drawing_id        INTEGER NOT NULL REFERENCES drawings(id) ON DELETE CASCADE,
    revision          TEXT    NOT NULL DEFAULT 'A',
    file_path         TEXT    NOT NULL,
    original_filename TEXT    NOT NULL,
    file_size         INTEGER DEFAULT 0,
    change_note       TEXT    DEFAULT '',
    uploaded_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    version_number    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS drawing_tags (
    drawing_id INTEGER NOT NULL REFERENCES drawings(id) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
    PRIMARY KEY (drawing_id, tag_id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    drawing_id  INTEGER NOT NULL REFERENCES drawings(id) ON DELETE CASCADE,
    filename    TEXT    NOT NULL,
    file_path   TEXT    NOT NULL,
    file_size   INTEGER DEFAULT 0,
    description TEXT    DEFAULT '',
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recent_views (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    drawing_id INTEGER NOT NULL REFERENCES drawings(id) ON DELETE CASCADE,
    viewed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_drawings_project    ON drawings(project_id);
CREATE INDEX IF NOT EXISTS idx_drawings_category   ON drawings(category_id);
CREATE INDEX IF NOT EXISTS idx_drawings_status     ON drawings(status);
CREATE INDEX IF NOT EXISTS idx_drawings_number     ON drawings(drawing_number);
CREATE INDEX IF NOT EXISTS idx_versions_drawing    ON drawing_versions(drawing_id);
CREATE INDEX IF NOT EXISTS idx_recent_drawing      ON recent_views(drawing_id);
CREATE INDEX IF NOT EXISTS idx_recent_time         ON recent_views(viewed_at DESC);
