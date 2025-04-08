CREATE TABLE IF NOT EXISTS Role (name TEXT PRIMARY KEY) STRICT;

CREATE TABLE IF NOT EXISTS TokenValidFromDate (
    user TEXT,
    -- NOTE: Parse as datetime.isoformat()
    unixtime INT NOT NULL,
    PRIMARY KEY (user),
    FOREIGN KEY (user) REFERENCES User (name) ON DELETE CASCADE
) STRICT;

CREATE TABLE IF NOT EXISTS UserRole (
    user TEXT,
    name TEXT,
    PRIMARY KEY (user, name),
    FOREIGN KEY (name) REFERENCES Role (name) ON DELETE CASCADE,
    FOREIGN KEY (user) REFERENCES User (name) ON DELETE CASCADE
) STRICT;

CREATE TABLE IF NOT EXISTS User (
    name TEXT PRIMARY KEY,
    pwd BLOB NOT NULL,
) STRICT;

CREATE TABLE IF NOT EXISTS UserData (
    user TEXT,
    display_name TEXT NOT NULL,
    mail TEXT UNIQUE,
    -- Isoformat
    created TEXT NOT NULL,
    -- history_json, old key -> this has been renamed registration_data
    -- {"name": name, "created_by": creator, "mail": mail}, created by mail: creator == name
    history_json BLOB NOT NULL,
    PRIMARY KEY (user),
    FOREIGN KEY (user) REFERENCES User (name) ON DELETE CASCADE
) STRICT;

-- CREATE TABLE IF NOT EXISTS RegistrationData (
--     name TEXT,
--     mail TEXT,
--     created_by TEXT NOT NULL,
--     PRIMARY KEY (name),
--     FOREIGN KEY (name) REFERENCES User (name) ON DELETE CASCADE
-- ) STRICT;

CREATE TABLE IF NOT EXISTS SensorSnapshot (
    -- NOTE: Parse as datetime.isoformat()
    timestamp TEXT PRIMARY KEY,
    -- NOTE: JSON
    data BLOB NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS ErrorMessage (
    -- NOTE: Parse as datetime.isoformat()
    timestamp TEXT PRIMARY KEY,
    -- NOTE: JSON
    data BLOB NOT NULL
) STRICT;