document.addEventListener('DOMContentLoaded', function() {
    // Элементы формы
    const dateInput = document.getElementById('date');
    const saveBtn = document.getElementById('saveBtn');
    const successMessage = document.getElementById('successMessage');

    // Элементы загрузки файла
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const browseButton = document.querySelector('.browse-button');
    const dataTableBody = document.getElementById('dataTableBody');
    const fileStatus = document.getElementById('fileStatus');
    const fileRows = document.getElementById('fileRows');
    const minR = document.getElementById('minR');
    const maxR = document.getElementById('maxR');
    const avgR = document.getElementById('avgR');

    // Данные для сохранения
    let experimentData = {
        date: '',
        room: '',
        address: '',
        object: '',
        measurements: []
    };

    // Установка текущей даты по умолчанию
    function setCurrentDateTime() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');

        dateInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
    }

    // Обработка загрузки файла
    browseButton.addEventListener('click', () => {
        fileInput.click();
    });

    // Обработка выбора файла
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Обработка перетаскивания файлов
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-over');
        });
    });

    // Обработка сброса файла
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files.length > 0) {
            handleFile(dt.files[0]);
        }
    });

    // Обработка выбранного файла
    function handleFile(file) {
        if (!file || !file.name.endsWith('.txt')) {
            alert('Пожалуйста, выберите файл в формате TXT');
            return;
        }

            // Скрываем информационную надпись
        dataPreviewInfo.style.display = 'none';

        // Показываем анимацию загрузки
        dropZone.innerHTML = `
            <div class="upload-icon">⏳</div>
            <div class="upload-text">Обработка файла...</div>
            <div class="upload-hint">${file.name}</div>
        `;

        const reader = new FileReader();
        reader.onload = function(e) {
            // Парсим содержимое файла
            parseFileContent(e.target.result);
        };
        reader.readAsText(file);
    }

    // Парсинг содержимого файла
function parseFileContent(content) {
    try {
        const lines = content.split('\n');
        const measurements = [];
        let validLines = 0;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            // Разделяем строку по точкам с запятой
            const parts = line.split(';').map(part => part.trim());

            // Проверяем, что в строке минимум 3 значения
            if (parts.length < 3) {
                throw new Error(`Неверный формат в строке ${i+1}: требуется 3 значения`);
            }

            const phi = parseFloat(parts[0]);
            const r = parseFloat(parts[1]);
            const theta = parseFloat(parts[2]);

            // Проверяем, что значения являются числами
            if (isNaN(phi) || isNaN(r) || isNaN(theta)) {
                throw new Error(`Неверный формат чисел в строке ${i+1}`);
            }

            measurements.push({ phi, r, theta });
            validLines++;
        }

        // Проверяем, что найдены действительные данные
        if (validLines === 0) {
            throw new Error("Файл не содержит действительных данных");
        }

        // Сохраняем данные
        experimentData.measurements = measurements;

        // Обновляем интерфейс
        updateUI(measurements);

    } catch (error) {
        // Обработка ошибки
        handleParseError(error.message);
    }
}

// Обработка ошибок парсинга
function handleParseError(errorMessage) {
    // Восстанавливаем исходное состояние области загрузки
    dropZone.innerHTML = `
        <div class="upload-icon">❌</div>
        <div class="upload-text">Ошибка обработки файла</div>
        <div class="upload-hint">${errorMessage}</div>
        <button class="browse-button">Попробовать снова</button>
        <input type="file" class="file-input" id="fileInput" accept=".txt">
    `;

    // Обновляем обработчики
    document.querySelector('.browse-button').addEventListener('click', () => {
        fileInput.click();
    });

    document.getElementById('fileInput').addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Сбрасываем данные
    experimentData.measurements = [];

    // Обновляем таблицу
    dataTableBody.innerHTML = `
        <tr>
            <td colspan="3" style="text-align: center; padding: 30px; color: #999;">
                Данные не загружены
            </td>
        </tr>
    `;

    // Скрываем информационную надпись
    dataPreviewInfo.style.display = 'none';

    // Деактивируем кнопку сохранения
    saveBtn.disabled = true;
}

    // Обновление интерфейса после загрузки данных
    function updateUI(measurements) {
        // Показываем успешное сообщение
        dropZone.innerHTML = `
            <div class="upload-icon">✅</div>
            <div class="upload-text">Файл успешно обработан</div>
            <div class="upload-hint">Загружено ${measurements.length} строк данных</div>
        `;

          // Показываем информационную надпись
        dataPreviewInfo.style.display = 'block';

        // Отображаем первые 10 строк в таблице
        renderDataTable(measurements);

        // Активируем кнопку сохранения
        saveBtn.disabled = false;
    }

    // Отображение данных в таблице
    function renderDataTable(measurements) {
        dataTableBody.innerHTML = '';

        // Берем первые 10 строк или все, если меньше
        const displayData = measurements.slice(0, 10);

        if (displayData.length === 0) {
            dataTableBody.innerHTML = `
                <tr>
                    <td colspan="3" style="text-align: center; padding: 30px; color: #999;">
                        Нет данных для отображения
                    </td>
                </tr>
            `;
            return;
        }

        displayData.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.phi.toFixed(4)}</td>
                <td>${item.r.toFixed(4)}</td>
                <td>${item.theta.toFixed(4)}</td>
            `;
            dataTableBody.appendChild(row);
        });
    }

    // Обработка сохранения данных эксперимента
    saveBtn.addEventListener('click', async () => {
    // 1) Собираем данные
    experimentData.date = dateInput.value;
    experimentData.room = document.getElementById('room').value.trim();
    experimentData.address = document.getElementById('address').value.trim();
    experimentData.object = document.getElementById('object').value.trim();

    if (
        !experimentData.date ||
        !experimentData.room ||
        !experimentData.address ||
        !experimentData.object ||
        experimentData.measurements.length === 0
    ) {
        alert('Пожалуйста, заполните все поля и загрузите файл с данными');
        return;
    }

    // 3) Формируем FormData
    const formData = new FormData();
    formData.append('date', experimentData.date);
    formData.append('room_description', experimentData.room);
    formData.append('address', experimentData.address);
    formData.append('object_description', experimentData.object);
    const jsonBlob = new Blob(
        [ JSON.stringify({ measurements: experimentData.measurements }) ],
        { type: 'application/json' }
        );
    formData.append('measurements_file', jsonBlob, 'measurements.json');

    const userId = getUserIdFromUrl();
    const endpoint = `/${userId}/create/save`;

    saveBtn.textContent = 'Сохранение...';
    saveBtn.disabled = true;

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
          const raw = await response.text();
          let errMsg = raw;
          try { errMsg = JSON.parse(raw).detail || raw; } catch {}
          throw new Error(errMsg);
        }

        // здесь статус 2xx
        const data = await response.json();

        successMessage.style.display = 'block';
        successMessage.textContent = 'Эксперимент успешно сохранён!';
        saveBtn.textContent = 'Сохранено';

        setTimeout(() => {
            successMessage.style.display = 'none';
            saveBtn.textContent = 'Сохранить эксперимент';
            saveBtn.disabled = false;
        }, 3000);

    } catch (error) {
        console.error('Ошибка при сохранении (fetch):', error);
        successMessage.style.display = 'block';
        successMessage.style.background = '#fff1f0';
        successMessage.style.borderColor = '#ffa39e';
        successMessage.style.color = '#cf1322';
        successMessage.textContent = `Ошибка: ${error.message}`;

        saveBtn.textContent = 'Ошибка сохранения';
        setTimeout(() => {
            successMessage.style.display = 'none';
            // сбрасываем стили
            successMessage.style = '';
            saveBtn.textContent = 'Сохранить эксперимент';
            saveBtn.disabled = false;
            }, 5000);
        }
    });


    // Функция для извлечения user_id из URL
    function getUserIdFromUrl() {
        const pathSegments = window.location.pathname.split('/').filter(segment => segment);
        return pathSegments.length > 0 ? pathSegments[0] : 'unknown';
    }

    // Инициализация страницы
    setCurrentDateTime();
});
