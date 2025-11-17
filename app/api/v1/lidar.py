# app/api/v1/lidar.py
import asyncio
import threading
import uuid
import os
import time
from typing import Dict, Any

import paramiko
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Body
from starlette.responses import FileResponse, JSONResponse

from app.core.config import settings

router = APIRouter()

# tasks: task_id -> dict { queue: asyncio.Queue, stop: dict, thread: Thread, channel, ssh, filename, done }
tasks: Dict[str, Dict[str, Any]] = {}
tasks_lock = threading.Lock()


def _ssh_connect():
    """Соединение paramiko (использует настройки из settings)."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(settings.LIDAR_HOST, username=settings.LIDAR_USER, password=settings.LIDAR_PASS, timeout=10)
    return ssh


def _start_ssh_command_in_thread(task_id: str, cmd: str, loop: asyncio.AbstractEventLoop):
    """
    Запускается в отдельном thread: выполняет команду через ssh, пушит строки в queue.
    """
    q: asyncio.Queue = tasks[task_id]["queue"]
    stop_holder = tasks[task_id]["stop"]
    try:
        ssh = _ssh_connect()
        transport = ssh.get_transport()
        chan = transport.open_session()
        full_cmd = f"cd {settings.LIDAR_REMOTE_PATH} && source .venv/bin/activate && {cmd}"
        chan.exec_command(full_cmd)

        with tasks_lock:
            tasks[task_id]["channel"] = chan
            tasks[task_id]["ssh"] = ssh

        while True:
            if chan.recv_ready():
                out = chan.recv(4096).decode("utf-8", errors="replace")
                loop.call_soon_threadsafe(q.put_nowait, {"type": "out", "text": out})
            if chan.recv_stderr_ready():
                err = chan.recv_stderr(4096).decode("utf-8", errors="replace")
                loop.call_soon_threadsafe(q.put_nowait, {"type": "err", "text": err})
            if chan.exit_status_ready():
                break
            if stop_holder.get("stop"):
                try:
                    chan.close()
                except Exception:
                    pass
                loop.call_soon_threadsafe(q.put_nowait, {"type": "info", "text": "[!] Прервано пользователем"})
                break
            time.sleep(0.05)

        code = None
        try:
            code = chan.recv_exit_status()
        except Exception:
            pass
        loop.call_soon_threadsafe(q.put_nowait, {"type": "info", "text": f"[+] Команда завершена (exit={code})"})
    except Exception as e:
        loop.call_soon_threadsafe(q.put_nowait, {"type": "err", "text": f"[!] Ошибка: {e}"})
    finally:
        with tasks_lock:
            tasks[task_id]["done"] = True
        # не закрываем ssh тут — сохранён если нужен для SFTP


@router.post("/ping")
async def ping():
    try:
        ssh = _ssh_connect()
        # просто проверить доступность каталога
        stdin, stdout, stderr = ssh.exec_command(f"cd {settings.LIDAR_REMOTE_PATH} && echo ok")
        if stdout.channel.recv_exit_status() == 0:
            ssh.close()
            return {"ok": True}
        ssh.close()
        raise HTTPException(status_code=500, detail="Remote path check failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def connect():
    # Мы не храним соединение "навсегда" на сервере — просто проверяем, что можно подключиться.
    try:
        ssh = _ssh_connect()
        stdin, stdout, stderr = ssh.exec_command(f"cd {settings.LIDAR_REMOTE_PATH} && pwd")
        rc = stdout.channel.recv_exit_status()
        ssh.close()
        if rc == 0:
            return {"ok": True}
        raise HTTPException(status_code=500, detail="Remote path not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_lidar():
    # Запускаем короткую команду и возвращаем task_id для websocket логов
    loop = asyncio.get_event_loop()
    task_id = uuid.uuid4().hex
    q: asyncio.Queue = asyncio.Queue()
    tasks[task_id] = {"queue": q, "stop": {"stop": False}, "done": False}

    cmd = "python lidar.py"
    t = threading.Thread(target=_start_ssh_command_in_thread, args=(task_id, cmd, loop), daemon=True)
    tasks[task_id]["thread"] = t
    t.start()
    return {"task_id": task_id}


@router.post("/engine_test")
async def test_engine():
    loop = asyncio.get_event_loop()
    task_id = uuid.uuid4().hex
    q: asyncio.Queue = asyncio.Queue()
    tasks[task_id] = {"queue": q, "stop": {"stop": False}, "done": False}

    cmd = "python engine.py"
    t = threading.Thread(target=_start_ssh_command_in_thread, args=(task_id, cmd, loop), daemon=True)
    tasks[task_id]["thread"] = t
    t.start()
    return {"task_id": task_id}


@router.post("/start")
async def start_scan(payload: dict = Body(...)):
    """
    payload ожидает: scan_range, scan_step, lidar_duration, pulse_delay
    возвращает task_id
    """
    scan_range = payload.get("scan_range")
    scan_step = payload.get("scan_step")
    lidar_duration = payload.get("lidar_duration")
    pulse_delay = payload.get("pulse_delay")

    if not all([scan_range, scan_step, lidar_duration, pulse_delay]):
        raise HTTPException(status_code=400, detail="Missing parameters")

    loop = asyncio.get_event_loop()
    task_id = uuid.uuid4().hex
    q: asyncio.Queue = asyncio.Queue()
    tasks[task_id] = {"queue": q, "stop": {"stop": False}, "done": False, "filename": None}

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"scan_{timestamp}.txt"
    tasks[task_id]["filename"] = filename

    cmd = (
        f"python scan.py --scan_range {scan_range} --scan_step {scan_step} "
        f"--lidar_duration {lidar_duration} --pulse_delay {pulse_delay} "
        f"--filename scans/{filename}"
    )

    t = threading.Thread(target=_start_ssh_command_in_thread, args=(task_id, cmd, loop), daemon=True)
    tasks[task_id]["thread"] = t
    t.start()
    return {"task_id": task_id, "filename": filename}


@router.post("/stop")
async def stop_scan(payload: dict = Body(...)):
    task_id = payload.get("task_id")
    if not task_id or task_id not in tasks:
        raise HTTPException(status_code=404, detail="task not found")
    with tasks_lock:
        tasks[task_id]["stop"]["stop"] = True
        # если есть открытый канал — попробуем закрыть
        ch = tasks[task_id].get("channel")
        try:
            if ch:
                ch.close()
        except Exception:
            pass
    return {"ok": True}


@router.get("/download")
async def download(filename: str):
    # скачиваем посредством SFTP на сервер и отдаем клиенту
    tmp_dir = "/tmp" if os.name != "nt" else os.getenv("TEMP", ".")
    remote_path = f"{settings.LIDAR_REMOTE_PATH}/scans/{filename}"
    local_path = os.path.join(tmp_dir, filename)
    try:
        ssh = _ssh_connect()
        sftp = ssh.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        ssh.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SFTP failed: {e}")
    # вернём файл
    return FileResponse(local_path, filename=filename)


@router.websocket("/ws/{task_id}")
async def websocket_logs(websocket: WebSocket, task_id: str):
    await websocket.accept()
    if task_id not in tasks:
        await websocket.send_json({"type": "err", "text": "task not found"})
        await websocket.close()
        return

    q: asyncio.Queue = tasks[task_id]["queue"]
    try:
        while True:
            msg = await q.get()
            await websocket.send_json(msg)
            # если задача помечена done и очередь пуста — закрываем
            if tasks[task_id].get("done") and q.empty():
                break
    except WebSocketDisconnect:
        # клиент отключился — просто выходим
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass