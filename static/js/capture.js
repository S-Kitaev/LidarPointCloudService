// static/js/capture.js
document.addEventListener("DOMContentLoaded", () => {
  const logOutput = document.getElementById("log-output");

  function log(message) {
    const line = document.createElement("div");
    line.textContent = message;
    logOutput.appendChild(line);
    logOutput.scrollTop = logOutput.scrollHeight;
  }

  const toggles = document.querySelectorAll(".capture-accordion-toggle");
  toggles.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetSelector = btn.getAttribute("data-target");
      if (!targetSelector) return;
      const panel = document.querySelector(targetSelector);
      if (!panel) return;
      const isOpen = panel.classList.contains("open");
      if (isOpen) {
        panel.classList.remove("open");
        btn.classList.remove("active");
      } else {
        panel.classList.add("open");
        btn.classList.add("active");
      }
    });
  });

  const connectionPanel = document.getElementById("connection-panel");
  const scanPanel = document.getElementById("scan-panel");

  const btnCheck = document.getElementById("btn-check-connection");
  const btnConnect = document.getElementById("btn-connect-ssh");

  const btnLidarTest = document.getElementById("btn-lidar-test");
  const btnEngineTest = document.getElementById("btn-engine-test");
  const btnStartScan = document.getElementById("btn-start-scan");
  const btnStopScan = document.getElementById("btn-stop-scan");
  const btnDownload = document.getElementById("btn-download");

  const inputRange = document.getElementById("scan_range");
  const inputStep = document.getElementById("scan_step");
  const inputDuration = document.getElementById("lidar_duration");
  const inputPulseDelay = document.getElementById("pulse_delay");

  let isConnected = false;
  let currentTaskId = null;
  let currentFilename = null;
  let ws = null;

  async function postJson(path, body) {
    const resp = await fetch(path, {
      method: "POST",
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body || {})
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(txt || resp.status);
    }
    return resp.json();
  }

  btnCheck?.addEventListener("click", async () => {
    log("[+] Проверка соединения с лидаром...");
    try {
      const resp = await postJson("/api/lidar/ping", {});
      if (resp.ok) log("[+] Лидар доступен");
      else log("[-] Лидар недоступен");
    } catch (e) {
      log("[-] Ошибка при проверке соединения: " + e.message);
    }
  });

  btnConnect?.addEventListener("click", async () => {
    log("[+] Подключение к Raspberry Pi...");
    try {
      const resp = await postJson("/api/lidar/connect", {});
      if (resp.ok) {
        isConnected = true;
        log("[+] Подключение установлено");
        if (btnLidarTest) btnLidarTest.disabled = false;
        if (btnEngineTest) btnEngineTest.disabled = false;
        if (btnStartScan) btnStartScan.disabled = false;
        // открыть панель параметров
        if (scanPanel && !scanPanel.classList.contains("open")) scanPanel.classList.add("open");
      } else {
        log("[-] Ошибка подключения");
      }
    } catch (e) {
      log("[-] Ошибка подключения: " + e.message);
    }
  });

    async function openLogWs(taskId) {
      if (ws) {
        try { ws.close(); } catch (e) { }
        ws = null;
      }
      const protocol = (location.protocol === "https:") ? "wss:" : "ws:";
      const url = `${protocol}//${location.host}/api/lidar/ws/${taskId}`;
      ws = new WebSocket(url);

      ws.onopen = () => log(`[+] Подключен к логам (task ${taskId})`);

      ws.onmessage = ev => {
        try {
          const obj = JSON.parse(ev.data);
          if (obj.type === "out") {
            log(obj.text);
          } else if (obj.type === "err") {
            log("ERR: " + obj.text);
          } else if (obj.type === "info") {
            log(obj.text);

            // Если команда завершена (нормально или с ошибкой) —
            // стоп выключаем, старт включаем
            if (obj.text.includes("Команда завершена") ||
                obj.text.includes("Прервано пользователем")) {

              if (btnStopScan) btnStopScan.disabled = true;
              if (btnStartScan) btnStartScan.disabled = false;

              // и если есть файл — даём возможность скачать
              if (obj.text.includes("Команда завершена") &&
                  currentFilename && btnDownload) {
                btnDownload.disabled = false;
              }
            }
          }
        } catch (e) {
          log(ev.data);
        }
      };

      ws.onclose = () => log("[*] WebSocket логов закрыт");
      ws.onerror = e => log("[!] WebSocket ошибка");
    }

  btnLidarTest?.addEventListener("click", async () => {
    if (!isConnected) { log("[-] Нет подключения"); return; }
    try {
      const resp = await postJson("/api/lidar/test", {});
      if (resp.task_id) {
        currentTaskId = resp.task_id;
        await openLogWs(currentTaskId);
      }
    } catch (e) {
      log("[-] Ошибка: " + e.message);
    }
  });

  btnEngineTest?.addEventListener("click", async () => {
    if (!isConnected) { log("[-] Нет подключения"); return; }
    try {
      const resp = await postJson("/api/lidar/engine_test", {});
      if (resp.task_id) {
        currentTaskId = resp.task_id;
        await openLogWs(currentTaskId);
      }
    } catch (e) {
      log("[-] Ошибка: " + e.message);
    }
  });

  btnStartScan?.addEventListener("click", async () => {
    if (!isConnected) { log("[-] Нет подключения"); return; }
    const payload = {
      scan_range: inputRange?.value,
      scan_step: inputStep?.value,
      lidar_duration: inputDuration?.value,
      pulse_delay: inputPulseDelay?.value
    };
    btnStartScan.disabled = true;
    btnStopScan.disabled = false;
    if (btnDownload) btnDownload.disabled = true;

    try {
      const resp = await postJson("/api/lidar/start", payload);
      if (resp.task_id) {
        currentTaskId = resp.task_id;
        currentFilename = resp.filename;
        await openLogWs(currentTaskId);
      }
    } catch (e) {
      log("[-] Ошибка старта: " + e.message);
      btnStartScan.disabled = false;
      btnStopScan.disabled = true;
    }
  });

  btnStopScan?.addEventListener("click", async () => {
    if (!currentTaskId) return log("[-] Нет активной задачи");
    btnStopScan.disabled = true;
    try {
      await postJson("/api/lidar/stop", { task_id: currentTaskId });
      log("[+] Запрос на остановку отправлен");
    } catch (e) {
      log("[-] Ошибка остановки: " + e.message);
    } finally {
      if (btnStartScan) btnStartScan.disabled = false;
    }
  });

    btnDownload?.addEventListener("click", () => {
      if (!currentFilename) return log("[-] Нет файла для скачивания");
      window.location = `/api/lidar/download?filename=${encodeURIComponent(currentFilename)}`;
      if (btnStartScan) btnStartScan.disabled = false;   // ← включаем повторные съёмки
    });

});