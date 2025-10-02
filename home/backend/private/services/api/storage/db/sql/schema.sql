-- ====================
-- User & Credentials
-- ====================
CREATE TABLE user (
    user_id            TEXT PRIMARY KEY NOT NULL, -- UUID, see trigger below
    login_name         TEXT UNIQUE NOT NULL COLLATE NOCASE,
    login_mail         TEXT UNIQUE COLLATE NOCASE,
    password           TEXT NOT NULL, -- hashed and salted
    enabled            BOOLEAN NOT NULL,
    last_login_date    DATETIME NOT NULL,
    last_updated_date  DATETIME NOT NULL
);

CREATE TABLE registration ( -- Historical, when created (READ ONLY)
    user_id         TEXT PRIMARY KEY NOT NULL,
    name            TEXT NOT NULL COLLATE NOCASE, -- Login name
    mail            TEXT COLLATE NOCASE,
    created_by      TEXT,
    created_date    DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY(created_by) REFERENCES user(user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);
CREATE INDEX idx_registration_created_by ON registration(created_by);
CREATE INDEX idx_registration_created_date ON registration(created_date);

CREATE TABLE user_profile (
    user_id           TEXT PRIMARY KEY NOT NULL,
    display_name      TEXT NOT NULL COLLATE NOCASE,
    last_updated_date DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id)
        ON DELETE CASCADE
);
CREATE INDEX idx_user_data_api_name ON user_profile(display_name COLLATE NOCASE);

-- ====================
-- Roles & Access
-- ====================
CREATE TABLE role (
    name            TEXT PRIMARY KEY
);

CREATE TABLE has_role (
    user_id         TEXT NOT NULL,
    role_name       TEXT NOT NULL,
    valid_from      DATETIME NOT NULL,
    valid_to        DATETIME NOT NULL,
    given_by        TEXT,
    created_date    DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY(role_name) REFERENCES role(name)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY(given_by) REFERENCES user(user_id)
        ON DELETE SET NULL,
    PRIMARY KEY(user_id, role_name)
);
CREATE INDEX idx_has_role_role_name ON has_role(role_name);
CREATE INDEX idx_has_role_given_by ON has_role(given_by);
CREATE INDEX idx_has_role_validity ON has_role(user_id, valid_from, valid_to);
CREATE INDEX idx_has_role_created_date ON has_role(created_date);
-- ====================
-- Services & Access
-- ====================
CREATE TABLE service (
    name            TEXT NOT NULL COLLATE NOCASE PRIMARY KEY,
    url             TEXT,
    description     TEXT NOT NULL,
    created_date    DATETIME NOT NULL
);

CREATE TABLE has_service (
    user_id         TEXT NOT NULL,
    service_name    TEXT NOT NULL,
    rwx             INTEGER CHECK (rwx >= 0 AND rwx <= 7),
    valid_from      DATETIME NOT NULL,
    valid_to        DATETIME NOT NULL,
    given_by        TEXT,
    created_date    DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY(service_name) REFERENCES service(name)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY(given_by) REFERENCES user(user_id)
        ON DELETE SET NULL,
    PRIMARY KEY(user_id, service_name)
);
CREATE INDEX idx_has_service_service ON has_service(service_name);
CREATE INDEX idx_has_service_given_by ON has_service(given_by);
CREATE INDEX idx_has_service_validity ON has_service(user_id, valid_from, valid_to);
CREATE INDEX idx_has_service_created_date ON has_service(created_date);

-- =========================
-- Misc
-- =========================
CREATE TABLE user_token_policy (
    user_id            TEXT PRIMARY KEY NOT NULL REFERENCES user(user_id)
        ON DELETE CASCADE,
    tokens_valid_after UNIXTIME NOT NULL
);

CREATE TABLE mail_confirmation (
    user_id         TEXT PRIMARY KEY NOT NULL,
    token           TEXT NOT NULL,
    created_date    DATETIME NOT NULL,
    expiry_date     DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id)
        ON DELETE CASCADE
);
CREATE INDEX idx_mail_confirmation_token ON mail_confirmation(token);
CREATE INDEX idx_mail_confirmation_expiry ON mail_confirmation(expiry_date);

CREATE TABLE user_bans (
    _id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    is_active   BOOLEAN NOT NULL,
    banned_by   TEXT,
    unbanned_by TEXT,
    reason      TEXT NOT NULL,
    start_time  DATETIME NOT NULL,
    end_time    DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY(banned_by) REFERENCES user(user_id)
        ON DELETE SET NULL,
    FOREIGN KEY(unbanned_by) REFERENCES user(user_id)
        ON DELETE SET NULL
);
CREATE INDEX idx_user_bans_user_id ON user_bans(user_id);
CREATE INDEX idx_user_bans_user_end ON user_bans(user_id, end_time);
CREATE INDEX idx_user_bans_active_user_end ON user_bans(user_id, is_active, end_time);

-- -- =========================
-- -- Views
-- -- =========================
-- CREATE VIEW uuid7 AS
-- WITH unixtime AS (SELECT CAST((UNIXEPOCH('subsec') * 1000) AS INTEGER) AS time)
-- SELECT PRINTF(
--     '%08x-%04x-%04x-%04x-%012x',
--     time >> 16,
--     time & 0xffff,
--     ABS(RANDOM()) % 0x0fff + 0x7000,
--     ABS(RANDOM()) % 0x3fff + 0x8000,
--     ABS(RANDOM()) >> 16
-- ) AS next
-- FROM unixtime;

-- -- SELECT PRINTF('%08x-%04x-%04x-%04x-%012x',
-- --       (SELECT time FROM unixtime) >> 16,
-- --       (SELECT time FROM unixtime) & 0xffff,
-- --       ABS(RANDOM()) % 0x0fff + 0x7000,   -- version 7
-- --       ABS(RANDOM()) % 0x3fff + 0x8000,   -- variant
-- --       ABS(RANDOM()) >> 16) AS next;

-- -- =========================
-- -- Triggers
-- -- =========================
-- CREATE TRIGGER trigger_after_insert_on_user
-- AFTER INSERT ON user
-- FOR EACH ROW
-- WHEN NEW.user_id IS NULL
-- BEGIN
--     UPDATE user
--     SET user_id = (SELECT next FROM uuid7)
--     WHERE ROWID = NEW.ROWID;
-- END;
