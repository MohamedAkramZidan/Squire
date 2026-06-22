

CREATE EXTENSION IF NOT EXISTS vector;


DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE meeting_status AS ENUM ('scheduled', 'in_progress', 'completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE progress_status AS ENUM ('not_started', 'in_progress', 'completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;



CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    email       VARCHAR(50) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);




CREATE TABLE IF NOT EXISTS tasks (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(50) NOT NULL,
    task_date   DATE NOT NULL,
    task_time   TIME NOT NULL,
    status      task_status NOT NULL DEFAULT 'pending',
    embedding   VECTOR(384),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_tasks_id      ON tasks (id);
CREATE INDEX IF NOT EXISTS ix_tasks_user_id ON tasks (user_id);




CREATE TABLE IF NOT EXISTS meetings (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(50) NOT NULL,
    meeting_date    DATE NOT NULL,
    meeting_time    TIME NOT NULL,
    status          meeting_status NOT NULL DEFAULT 'scheduled',
    person          VARCHAR(50),
    location        VARCHAR(50),
    embedding       VECTOR(384),
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_meetings_id      ON meetings (id);
CREATE INDEX IF NOT EXISTS ix_meetings_user_id ON meetings (user_id);



CREATE TABLE IF NOT EXISTS notes (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_notes_id      ON notes (id);
CREATE INDEX IF NOT EXISTS ix_notes_user_id ON notes (user_id);


CREATE TABLE IF NOT EXISTS note_chunks (
    id          SERIAL PRIMARY KEY,
    chunk_index INTEGER NOT NULL,
    chunk_text  TEXT NOT NULL,
    embedding   VECTOR(384),
    note_id     INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_note_chunks_id      ON note_chunks (id);
CREATE INDEX IF NOT EXISTS ix_note_chunks_note_id ON note_chunks (note_id);


CREATE TABLE IF NOT EXISTS progress (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(50) NOT NULL,
    status      progress_status NOT NULL DEFAULT 'not_started',
    field       VARCHAR(30),
    value       INTEGER,
    embedding   VECTOR(384),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_progress_id      ON progress (id);
CREATE INDEX IF NOT EXISTS ix_progress_user_id ON progress (user_id);


CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_tasks_updated_at ON tasks;
CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_meetings_updated_at ON meetings;
CREATE TRIGGER trg_meetings_updated_at
    BEFORE UPDATE ON meetings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_notes_updated_at ON notes;
CREATE TRIGGER trg_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_progress_updated_at ON progress;
CREATE TRIGGER trg_progress_updated_at
    BEFORE UPDATE ON progress
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


INSERT INTO users (id, name, email)
VALUES (1, 'Test User', 'test.user@squire.local')
ON CONFLICT (id) DO NOTHING;


SELECT setval(
    pg_get_serial_sequence('users', 'id'),
    GREATEST((SELECT MAX(id) FROM users), 1)
);



SELECT id, name, email FROM users;

SELECT * FROM meetings;

select * from tasks;

select * from progress;

select * from notes;

SELECT id, title, status FROM progress WHERE user_id = 1;