#!/usr/bin/env python3
# scan.py
# Главный скрипт для 3D сканирования с поддержкой параметров

import os
import time
import datetime
import argparse
import RPi.GPIO as GPIO
from pyrplidar import PyRPlidar

# Настройки двигателя
PUL = 29
DIR = 31
ENA = 33
STEPS_PER_REV = 200
MICROSTEP = 8
STEPS_PER_FULL_REV = STEPS_PER_REV * MICROSTEP
DEGREES_PER_STEP = 360.0 / STEPS_PER_FULL_REV
ENA_ENABLE = GPIO.HIGH
ENA_DISABLE = GPIO.LOW

# Параметры сканирования по умолчанию
DEFAULT_SCAN_RANGE = 240
DEFAULT_SCAN_STEP = 5
DEFAULT_LIDAR_DURATION = 10
DEFAULT_PULSE_DELAY = 0.006

def setup_gpio():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PUL, GPIO.OUT)
    GPIO.setup(DIR, GPIO.OUT)
    GPIO.setup(ENA, GPIO.OUT)
    GPIO.output(ENA, ENA_DISABLE)
    GPIO.output(DIR, GPIO.LOW)
    GPIO.output(PUL, GPIO.LOW)

def steps_for_angle(angle_deg):
    return max(1, int(round(angle_deg / DEGREES_PER_STEP)))

def move_angle(angle_deg, direction=True, pulse_delay=0.001):
    steps = steps_for_angle(angle_deg)
    GPIO.output(DIR, GPIO.HIGH if direction else GPIO.LOW)
    time.sleep(0.01)
    
    for i in range(steps):
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(pulse_delay)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(pulse_delay)

def main_scan(scan_range=DEFAULT_SCAN_RANGE, 
              scan_step=DEFAULT_SCAN_STEP, 
              lidar_duration=DEFAULT_LIDAR_DURATION, 
              pulse_delay=DEFAULT_PULSE_DELAY,
              filename=None):
    
    # Если имя файла не указано, генерируем автоматически
    if filename is None:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"scans/scan_{timestamp}.txt"
    
    # Создаем папку scans если её нет
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    print(f"[+] Начало 3D сканирования")
    print(f"[+] Диапазон: {scan_range}°, шаг: {scan_step}°")
    print(f"[+] Длительность сканирования: {lidar_duration}с")
    print(f"[+] Задержка импульса: {pulse_delay}с")
    print(f"[+] Файл: {filename}")
    
    total_points = 0
    start_total_time = time.time()
    current_motor_angle = 0
    
    GPIO.setwarnings(False)
    setup_gpio()
    GPIO.output(ENA, ENA_ENABLE)
    
    lidar = None
    try:
        lidar = PyRPlidar()
        lidar.connect(port='/dev/ttyUSB0', baudrate=115200, timeout=3)
        
        try:
            lidar.stop()
        except:
            pass
        
        lidar.set_motor_pwm(600)
        time.sleep(3)
        
        health = lidar.get_health()
        print(f"[+] Состояние лидара: {health}")
        
        scan_generator_func = lidar.start_scan()
        scan_generator = scan_generator_func()
        
        with open(filename, 'w') as f:
            for motor_angle in range(0, scan_range + 1, scan_step):
                current_motor_angle = motor_angle
                
                if motor_angle > 0:
                    move_angle(scan_step, True, pulse_delay)
                
                start_scan_time = time.time()
                point_count = 0
                
                for scan in scan_generator:
                    if time.time() - start_scan_time > lidar_duration:
                        break
                        
                    if scan.distance > 0 and scan.quality > 10:
                        angle = scan.angle % 360
                        f.write(f"{angle:.4f};{scan.distance:.4f};{motor_angle}\n")
                        point_count += 1
                
                total_points += point_count
                elapsed = time.time() - start_total_time
                print(f"[+] Угол {motor_angle}°, точек {point_count}, время {elapsed:.1f}с")
        
    except KeyboardInterrupt:
        print("\n[!] Сканирование прервано пользователем")
        if current_motor_angle > 0:
            print(f"[+] Возврат на {current_motor_angle}° в исходное положение")
            move_angle(current_motor_angle, False, pulse_delay)
        
    except Exception as e:
        print(f"[-] Ошибка сканирования: {e}")
        if current_motor_angle > 0:
            print(f"[+] Возврат на {current_motor_angle}° в исходное положение")
            move_angle(current_motor_angle, False, pulse_delay)
            
    finally:
        try:
            if lidar:
                lidar.stop()
                lidar.set_motor_pwm(0)
                lidar.disconnect()
        except:
            pass
        
        if current_motor_angle == scan_range:
            print("[+] Возврат в исходное положение")
            move_angle(scan_range, False, pulse_delay)
        
        GPIO.output(ENA, ENA_DISABLE)
        GPIO.cleanup()
    
    total_time = time.time() - start_total_time
    print("[+] Сканирование завершено")
    print(f"[+] Всего точек: {total_points}")
    print(f"[+] Время сканирования: {total_time:.1f}с")
    print(f"[+] Файл: {filename}")
    
    return filename
    
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='3D сканирование лидаром')
	parser.add_argument('--scan_range', type=int, default=DEFAULT_SCAN_RANGE, 
					   help=f'Диапазон сканирования в градусах (по умолчанию: {DEFAULT_SCAN_RANGE})')
	parser.add_argument('--scan_step', type=int, default=DEFAULT_SCAN_STEP,
					   help=f'Шаг сканирования в градусах (по умолчанию: {DEFAULT_SCAN_STEP})')
	parser.add_argument('--lidar_duration', type=int, default=DEFAULT_LIDAR_DURATION,
					   help=f'Длительность сканирования на каждом шаге в секундах (по умолчанию: {DEFAULT_LIDAR_DURATION})')
	parser.add_argument('--pulse_delay', type=float, default=DEFAULT_PULSE_DELAY,
					   help=f'Задержка между импульсами двигателя (по умолчанию: {DEFAULT_PULSE_DELAY})')
	parser.add_argument('--filename', type=str, default=None,
					   help='Имя файла для сохранения (по умолчанию: scans/scan_YYYYMMDD_HHMMSS.txt)')

	args = parser.parse_args()

	main_scan(
		scan_range=args.scan_range,
		scan_step=args.scan_step,
		lidar_duration=args.lidar_duration,
		pulse_delay=args.pulse_delay,
		filename=args.filename
	)
