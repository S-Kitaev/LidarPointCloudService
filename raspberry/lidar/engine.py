#!/usr/bin/env python3
# engine.py

import RPi.GPIO as GPIO
import time
import sys

PUL = 29    # Физический пин 29 - импульсы
DIR = 31    # Физический пин 31 - направление  
ENA = 33    # Физический пин 33 - включение драйвера

# Параметры двигателя
STEPS_PER_REV = 200      # Полных шагов на оборот для NEMA 23 (1.8°)
MICROSTEP = 8            # Микрошаг (должен соответствовать настройкам TB6600)
STEPS_PER_FULL_REV = STEPS_PER_REV * MICROSTEP  # Всего шагов на полный оборот
DEGREES_PER_STEP = 360.0 / STEPS_PER_FULL_REV   # Градусов на один шаг

# Логика управления (инвертированная для ENA)
ENA_ENABLE = GPIO.HIGH   # Включить драйвер
ENA_DISABLE = GPIO.LOW   # Выключить драйвер

def setup_gpio():
    """Настройка GPIO пинов"""
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PUL, GPIO.OUT)
    GPIO.setup(DIR, GPIO.OUT)
    GPIO.setup(ENA, GPIO.OUT)
    
    # Инициализация состояний
    GPIO.output(ENA, ENA_DISABLE)  # Сначала выключаем драйвер
    GPIO.output(DIR, GPIO.LOW)     # Направление по умолчанию
    GPIO.output(PUL, GPIO.LOW)     # Низкий уровень на импульсе

def steps_for_angle(angle_deg):
    """Рассчитывает количество шагов для заданного угла"""
    steps = int(round(angle_deg / DEGREES_PER_STEP))
    return max(1, steps)

def move_angle(angle_deg, direction=True, pulse_delay=0.001):
    """
    Поворачивает двигатель на указанный угол
    
    Args:
        angle_deg: угол в градусах
        direction: True - вперед, False - назад
        pulse_delay: задержка между импульсами в секундах
    """
    steps = steps_for_angle(angle_deg)
    
    # Устанавливаем направление
    GPIO.output(DIR, GPIO.HIGH if direction else GPIO.LOW)
    time.sleep(0.01)  # Небольшая задержка после смены направления
    
    # Генерируем импульсы
    for i in range(steps):
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(pulse_delay)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(pulse_delay)

def main():
    """Основная функция тестирования"""    
    # Параметры теста
    test_angle = 240     # Угол поворота в градусах
    pulse_delay = 0.006   # Задержка между импульсами

    try:
        # Настройка GPIO
        setup_gpio()
        
        # Включаем драйвер
        print("[+] Запуск двигателя")
        GPIO.output(ENA, ENA_ENABLE)
        time.sleep(0.5)
        
        print(f"[+] Поворот на +{test_angle}°")
        move_angle(test_angle, direction=True, pulse_delay=pulse_delay)
        
        time.sleep(2)
        
        print(f"[+] Поворот на -{test_angle}°")
        move_angle(test_angle, direction=False, pulse_delay=pulse_delay)
        
        print("[+] Тест успешно завершен")
        
    except KeyboardInterrupt:
        print("[!] Тест прерван пользователем")
    except Exception as e:
        print(f"[!] Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Гарантированно выключаем драйвер
        GPIO.output(ENA, ENA_DISABLE)
        GPIO.cleanup()
        print("[+] Ресурсы освобождены")

if __name__ == "__main__":
    main()
