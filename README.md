# Lidar
HES LiDAR project 

## Запуск проекта

1. Веб-приложение на **FastAPI** с **JWT-авторизацией** и базой данных **PostgreSQL** обернутое в Docker, далее это будет полноценный проект интернета вещей.

2. Чтобы запустить его:

   - Склонируйте репозиторий.
   - Перейдите в папку проекта.
   - Убедитесь, что у вас установлены **Docker** и **Docker Compose**.

3. Выполните команду:
   ```bash
   docker compose up --build
   ```
   
4. Сам API-сервер на порту 8000 внутри контейнера, проброшенном на порт 8001 хоста. Перейдите в браузере по ссылке:
   ```bash
   http://localhost:8001/
   ```
   
## Документация к проекту

### Руководства пользователей
- Технические требования - [docs/тт v1(07_12_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D1%82%D1%82%20v1(07_12_25).md)
- Руководство пользователя - [docs/руководство v1(07_12_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D1%80%D1%83%D0%BA%D0%BE%D0%B2%D0%BE%D0%B4%D1%81%D1%82%D0%B2%D0%BE%20v1(07_12_25).md)
- Руководство по запуску ПО - [docs/запуск по v1(07_12_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D0%B7%D0%B0%D0%BF%D1%83%D1%81%D0%BA%20%D0%BF%D0%BE%20v1(07_12_25).md)
- Руководство по сборке установки - [raspberry/build.md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/raspberry/build.md)
- Руководство загрузки ПО установки - [raspberry/installation.md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/raspberry/installation.md)
- API - [docs/api v1(07_12_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/api%20v1(07_12_25).md)

### Отчетные документы

- Техническое задание - [docs/тз v1(22_03_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D1%82%D0%B7%20v1(22_03_25).md)
- Функциональные и нефункциональные требования - [docs/фтт нфтт v1(22_03_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D1%84%D1%82%D1%82%20%D0%BD%D1%84%D1%82%D1%82%20v1(22_03_25).md)
- Концептуальный проект - [docs/концептуальный проект v1(01_01_2024).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D0%BA%D0%BE%D0%BD%D1%86%D0%B5%D0%BF%D1%82%D1%83%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9%20%D0%BF%D1%80%D0%BE%D0%B5%D0%BA%D1%82%20v1(01_01_2024).md)
- Обоснование выбора технологий - [docs/обоснования проекта v1(07_12_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D0%BE%D0%B1%D0%BE%D1%81%D0%BD%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F%20%D0%BF%D1%80%D0%BE%D0%B5%D0%BA%D1%82%D0%B0%20v1(07_12_25).md)
- Ролевая модель первой фазы проекта - [docs/ролевая модель v1(10_05_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D1%80%D0%BE%D0%BB%D0%B5%D0%B2%D0%B0%D1%8F%20%D0%BC%D0%BE%D0%B4%D0%B5%D0%BB%D1%8C%20v1(10_05_25).md)
- Ролевая модель второй фазы проекта - [docs/ролевая модель v2(12_12_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D1%80%D0%BE%D0%BB%D0%B5%D0%B2%D0%B0%D1%8F%20%D0%BC%D0%BE%D0%B4%D0%B5%D0%BB%D1%8C%20v2(12_12_25).md)
- План-график работ первой фазы проекта - [docs/план график v1(10_05_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D0%BF%D0%BB%D0%B0%D0%BD%20%D0%B3%D1%80%D0%B0%D1%84%D0%B8%D0%BA%20v1(10_05_25).md)
- План-график работ второй фазы проекта - ```---```
- Программа методики испытаний - [docs/программа испытаний v1(07_12_25).md](https://github.com/S-Kitaev/LidarPointCloudService/blob/main/docs/%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B0%20%D0%B8%D1%81%D0%BF%D1%8B%D1%82%D0%B0%D0%BD%D0%B8%D0%B9%20v1(07_12_25).md)
- Приложения к ПМИ - [docs/Приложения к ПМИ (для печати)](https://github.com/S-Kitaev/LidarPointCloudService/tree/main/docs/%D0%9F%D1%80%D0%B8%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D1%8F%20%D0%BA%20%D0%9F%D0%9C%D0%98%20(%D0%B4%D0%BB%D1%8F%20%D0%BF%D0%B5%D1%87%D0%B0%D1%82%D0%B8))

