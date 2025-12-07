#!/usr/bin/env python3
# lidar.py

import os
import time
import datetime
import sys
from pyrplidar import PyRPlidar

PORT = '/dev/ttyUSB0'
SCAN_DURATION = 10  # секунд сканирования
OUT_DIR = 'tests'

def collect_layer(port=PORT, scan_duration=SCAN_DURATION, out_dir=OUT_DIR):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(out_dir, f"lidar_{timestamp}.txt")
    
    # Создаем файл лога
    log_file = open(log_filename, 'w')
    
    def log_message(message, prefix="", to_file=True):
        """Функция для логирования в консоль и файл"""
        console_message = f"{prefix}{message}"
        print(console_message)
        
        if to_file:
            # Для файла убираем префиксы и форматируем в стиле ключ-значение
            if ":" in message and ";" not in message:
                # Преобразуем сообщения вида "Текст: значение" в "Текст; значение"
                file_message = message.replace(":", ";")
            else:
                file_message = message
            log_file.write(file_message + "\n")
    
    lidar = None
    
    try:
        log_message("[+] Подключение к LIDAR на " + port)
        lidar = PyRPlidar()
        lidar.connect(port=port, baudrate=115200, timeout=3)
        
        info = lidar.get_info()
        log_message(f"[+] Модель лидара; {info.model}")
        
        health = lidar.get_health()
        log_message(f"[+] Состояние лидара; {health}")
        
        # Убрали сообщение о запуске мотора
        lidar.set_motor_pwm(600)
        time.sleep(2)  # Ждем раскрутки мотора
        
        log_message(f"[+] Тестовое сканирование; {scan_duration} секунд")
        scan_generator_func = lidar.start_scan()
        scan_generator = scan_generator_func()
        
        collected = []
        start_time = time.time()
        point_count = 0
        low_quality_points = []  # Точки с качеством < 15
        
        # Собираем данные в течение заданного времени
        for scan in scan_generator:
            if time.time() - start_time > scan_duration:
                break
                
            # Фильтруем точки с нулевым расстоянием и низким качеством
            if scan.distance > 0 and scan.quality > 10:
                collected.append((scan.quality, scan.angle, scan.distance))
                point_count += 1
                
                # Сохраняем точки с качеством < 15 для статистики
                if scan.quality < 15:
                    low_quality_points.append((scan.angle, scan.distance, scan.quality))
        
        if not collected:
            log_message("[-] Не собрано ни одной точки данных")
            return None
            
        # Сортируем по углу и преобразуем данные
        data = []
        for quality, angle, distance in collected:
            # Нормализуем угол к диапазону 0-360
            normalized_angle = angle % 360
            data.append((normalized_angle, distance, quality))
        
        # Сортируем по углу
        data.sort(key=lambda x: x[0])
        
        log_message(f"[+] Собрано точек облака; {len(data)}")
        
        # Анализ покрытия
        coverage_stats = analyze_coverage(data, log_message)
        
        # Анализ качества точек
        log_message("[+] Итоговая статистика сканирования:")
        log_message(f"    Общее количество точек; {len(data)}")
        log_message(f"    Точки с качеством < 15; {len(low_quality_points)}")
        log_message(f"    Диапазон углов; {coverage_stats['min_angle']:.1f}° - {coverage_stats['max_angle']:.1f}°")
        log_message(f"    Большие пропуски; {coverage_stats['large_gaps_count']}")
        
        return log_filename

    except Exception as e:
        log_message(f"[-] Ошибка; {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        try:
            if lidar:
                # Убрали сообщение об остановке лидара
                lidar.stop()
                lidar.set_motor_pwm(0)
                lidar.disconnect()
        except Exception as e:
            log_message(f"[-] Ошибка при завершении; {e}")
        finally:
            log_file.close()

def analyze_coverage(data, log_message):
    """Анализ покрытия углов"""
    if not data:
        return {"min_angle": 0, "max_angle": 0, "large_gaps_count": 0}
        
    angles = [point[0] for point in data]
    min_angle = min(angles)
    max_angle = max(angles)
    
    log_message(f"[+] Диапазон углов; {min_angle:.1f}° - {max_angle:.1f}°")
    
    # Проверяем покрытие по секторам
    sectors = 12  # 12 секторов по 30 градусов
    sector_size = 360 / sectors
    coverage = [0] * sectors
    
    for angle in angles:
        sector = int(angle // sector_size)
        if sector < sectors:
            coverage[sector] += 1
    
    log_message("[+] Покрытие по секторам (по 30°):")
    for i in range(sectors):
        start_angle = i * sector_size
        end_angle = (i + 1) * sector_size
        log_message(f"    {start_angle:3.0f}°-{end_angle:3.0f}°; {coverage[i]} точек")
    
    # Проверяем большие пропуски (> 45 градусов)
    angles_sorted = sorted(angles)
    large_gaps = []
    for i in range(1, len(angles_sorted)):
        gap = angles_sorted[i] - angles_sorted[i-1]
        if gap > 45:  # Пропуск больше 45 градусов
            large_gaps.append((angles_sorted[i-1], angles_sorted[i], gap))
    
    large_gaps_count = len(large_gaps)
    if large_gaps:
        log_message(f"[!] Обнаружены большие пропуски в данных; {large_gaps_count}")
        for gap_start, gap_end, gap_size in large_gaps[:5]:  # Показываем первые 5 пропусков
            log_message(f"    Пропуск; {gap_start:.1f}° - {gap_end:.1f}° ({gap_size:.1f}°)")
        if len(large_gaps) > 5:
            log_message(f"    ... и еще {len(large_gaps) - 5} пропусков")
    else:
        log_message("[+] Больших пропусков не обнаружено; 0")
    
    return {
        "min_angle": min_angle,
        "max_angle": max_angle,
        "large_gaps_count": large_gaps_count
    }

if __name__ == "__main__":  
    out = collect_layer()
    if not out:
        print("[-] Не удалось собрать данные")
        sys.exit(1)
        
    print("[+] Лог успешно сохранен:", out)
                
