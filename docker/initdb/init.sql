-- 1. Создаём таблицу users
CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    user_name     VARCHAR(20) UNIQUE NOT NULL,
    user_password VARCHAR(60) NOT NULL,
    email         VARCHAR(50)
);
