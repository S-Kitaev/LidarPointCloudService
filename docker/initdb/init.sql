-- 1. Создаём таблицу users
CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    user_name     VARCHAR(20) UNIQUE NOT NULL,
    user_password VARCHAR(60) NOT NULL,
    email         VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS experiments(
    id                 SERIAL                      PRIMARY KEY,
    exp_dt             TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    room_description   VARCHAR(1000)               NULL,
    address            VARCHAR(200)                NULL,
    object_description VARCHAR(200)                NULL
);

CREATE TABLE IF NOT EXISTS measurements (
    id                 SERIAL                      PRIMARY KEY,
    experiment_id      integer                     REFERENCES experiments(id),
    phi                 FLOAT                       NOT NULL,
    theta               FLOAT                       NOT NULL,
    r                  FLOAT                       NOT NULL
);

---- 2. Сидаем тестовых пользователей (пароли — заранее захешируйте bcrypt)
--INSERT INTO users (user_name, user_password, email) VALUES
--('alice', '$2b$12$CZ1J4w3tp7rJTQWJ60Ja0.fgdqBwa5lCPqbKlscgWOAdyYv5E.kJq', 'alice@example.com'),
--('bob',   '$2b$12$cLwy1jqrjB5Mg2OKcnFjQeoVqRVRcdrcpz/q8glXUk6lLX9g/vnT.', 'bob@example.com')
--ON CONFLICT (user_name) DO NOTHING;