#!/usr/bin/env python3
# scan.py
# Главный скрипт для 3D сканирования

import os
import time
import datetime
import RPi.GPIO as GPIO
from pyrplidar import PyRPlidar

timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
FILENAME = f"scans/scan_{timestamp}.txt"

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

# Параметры сканирования
SCAN_RANGE = 240
SCAN_STEP = 5
LIDAR_SCAN_DURATION = 10
PULSE_DELAY = 0.006

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

def move_angle(angle_deg, direction=True):
    steps = steps_for_angle(angle_deg)
    GPIO.output(DIR, GPIO.HIGH if direction else GPIO.LOW)
    time.sleep(0.01)
    
    for i in range(steps):
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(PULSE_DELAY)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(PULSE_DELAY)

def scan_lidar(scan_generator, duration, motor_angle, file):
    start_time = time.time()
    point_count = 0
    
    for scan in scan_generator:
        if time.time() - start_time > duration:
            break
            
        if scan.distance > 0 and scan.quality > 10:
            angle = scan.angle % 360
            file.write(f"{angle:.4f};{scan.distance:.4f};{motor_angle}\n")
            point_count += 1
    
    return point_count

def main_scan(scan_range=SCAN_RANGE, 
			  scan_step=SCAN_STEP, 
              lidar_duration=LIDAR_SCAN_DURATION, 
              pulse_delay=PULSE_DELAY,
              filename=FILENAME):
    
    global PULSE_DELAY
    PULSE_DELAY = pulse_delay
    
    print("[+] Начало 3D сканирования")
    print(f"[+] Диапазон: {scan_range}°, шаг: {scan_step}°")
    print(f"[+] Файл: {filename}")
    
    total_points = 0
    start_total_time = time.time()
    current_motor_angle = 0  # Отслеживаем текущий угол
    
    # Отключаем предупреждения GPIO
    GPIO.setwarnings(False)
    setup_gpio()
    GPIO.output(ENA, ENA_ENABLE)
    
    try:
        lidar = PyRPlidar()
        lidar.connect(port='/dev/ttyUSB0', baudrate=115200, timeout=3)
        
        # Сбрасываем лидар перед началом работы
        try:
            lidar.stop()
        except:
            pass
        
        lidar.set_motor_pwm(600)
        time.sleep(3)  # Увеличиваем время для раскрутки мотора
        
        # Проверяем состояние лидара
        health = lidar.get_health()
        print(f"[+] Состояние лидара: {health}")
        
        # Запускаем сканирование
        scan_generator_func = lidar.start_scan()
        scan_generator = scan_generator_func()
        
        with open(filename, 'w') as f:
            for motor_angle in range(0, scan_range + 1, scan_step):
                current_motor_angle = motor_angle  # Обновляем текущий угол
                
                if motor_angle > 0:
                    move_angle(scan_step, True)
                
                start_scan_time = time.time()
                point_count = 0
                
                # Сканируем в течение заданного времени
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
        # Возвращаем на текущий угол, а не на полный диапазон
        if current_motor_angle > 0:
            print(f"[+] Возврат на {current_motor_angle}° в исходное положение")
            move_angle(current_motor_angle, False)
        
    except Exception as e:
        print(f"[-] Ошибка сканирования: {e}")
        # При ошибке тоже возвращаем на пройденное расстояние
        if current_motor_angle > 0:
            print(f"[+] Возврат на {current_motor_angle}° в исходное положение")
            move_angle(current_motor_angle, False)
            
    finally:
        # Гарантированно останавливаем лидар и двигатель
        try:
            lidar.stop()
        except:
            pass
        try:
            lidar.set_motor_pwm(0)
        except:
            pass
        try:
            lidar.disconnect()
        except:
            pass
        
        # Возврат в исходное положение только если сканирование завершилось нормально
        # и мы не были прерваны (т.е. current_motor_angle == scan_range)
        if current_motor_angle == scan_range:
            print("[+] Возврат в исходное положение")
            move_angle(scan_range, False)
        
        GPIO.output(ENA, ENA_DISABLE)
        GPIO.cleanup()
    
    total_time = time.time() - start_total_time
    print("[+] Сканирование завершено")
    print(f"[+] Всего точек: {total_points}")
    print(f"[+] Время сканирования: {total_time:.1f}с")
    print(f"[+] Файл: {filename}")
    
    return filename

if __name__ == "__main__":
    main_scan()
