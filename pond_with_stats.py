#!/usr/bin/env python3
"""
Первый Пруд 3.2 — С ЗАПИСЬЮ СТАТИСТИКИ
Каждые 10 секунд данные пишутся в файл pond_stats.csv
"""

import curses
import random
import time
import csv
from datetime import datetime

WIDTH = 78
HEIGHT = 22
SUN_TOP = HEIGHT // 2

MAX_ALGAE = 200
MAX_DAPHNIA = 100
MAX_BEETLE = 8

# НАСТРОЙКИ ЗАПИСИ
SAVE_INTERVAL = 10  # Секунд между сохранениями
last_save_time = 0

class Genome:
    def __init__(self, speed=1.0, efficiency=1.0, neuroticism=0.0, stealth=0.5):
        self.speed = speed
        self.efficiency = efficiency
        self.neuroticism = neuroticism
        self.stealth = stealth
    
    def mutate(self):
        if random.random() < 0.25:
            gene = random.choice(['speed', 'efficiency', 'neuroticism', 'stealth'])
            delta = random.uniform(-0.2, 0.2)
            new = getattr(self, gene) + delta
            new = max(0.3, min(2.5, new))
            setattr(self, gene, new)
        return self
    
    def copy(self):
        return Genome(self.speed, self.efficiency, self.neuroticism, self.stealth)

class Algae:
    def __init__(self, x, y, energy=10):
        self.x = x
        self.y = y
        self.energy = energy
    
    def update(self, world):
        if self.y < SUN_TOP:
            self.energy += 1.2
        else:
            self.energy += 0.6
        
        if self.energy >= 15 and len(world.algae) < MAX_ALGAE:
            dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                world.algae.append(Algae(nx, ny, energy=5))
                self.energy -= 5
        
        if self.energy <= 0:
            return False
        return True

class Daphnia:
    def __init__(self, x, y, genome=None, energy=20):
        self.x = x
        self.y = y
        self.genome = genome if genome else Genome()
        self.energy = energy
    
    def update(self, world):
        self.energy -= 0.2 / self.genome.efficiency
        
        if self.energy <= 0:
            return False
        
        target = None
        if random.random() > self.genome.neuroticism:
            min_dist = float('inf')
            for a in world.algae:
                dist = abs(a.x - self.x) + abs(a.y - self.y)
                if dist < min_dist:
                    min_dist = dist
                    target = a
        
        if target:
            dx = 1 if target.x > self.x else -1 if target.x < self.x else 0
            dy = 1 if target.y > self.y else -1 if target.y < self.y else 0
            if random.random() < self.genome.speed * 0.5:
                self.x = max(0, min(WIDTH-1, self.x + dx))
                self.y = max(0, min(HEIGHT-1, self.y + dy))
            
            if abs(self.x - target.x) <= 1 and abs(self.y - target.y) <= 1:
                if target in world.algae:
                    world.algae.remove(target)
                    self.energy += 3
        
        if self.energy >= 40 and len(world.daphnia) < MAX_DAPHNIA:
            child_genome = self.genome.copy().mutate()
            world.daphnia.append(Daphnia(self.x, self.y, child_genome, energy=10))
            self.energy -= 15
        
        return True
    
    def energy_value(self):
        return 15 * self.genome.efficiency
    
    def pod_zashitoy(self, world):
        for a in world.algae:
            if a.x == self.x and a.y == self.y:
                return True
        return False

class Beetle:
    def __init__(self, x, y, genome=None, energy=40):
        self.x = x
        self.y = y
        self.genome = genome if genome else Genome(speed=0.7, stealth=0.5)
        self.energy = energy
        self.hunger = 0
    
    def update(self, world):
        self.energy -= 0.12 / self.genome.efficiency
        self.hunger += 1
        
        if self.energy <= 0:
            return False
        
        голоден = (self.energy < 40 or self.hunger > 30)
        
        if not голоден:
            if random.random() < 0.05:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
            return True
        
        лучшая_дафния = None
        лучшее_расстояние = 1000
        
        for d in world.daphnia:
            if d.pod_zashitoy(world):
                continue
            
            заметность = 1.0 - d.genome.stealth
            расстояние = abs(d.x - self.x) + abs(d.y - self.y)
            
            if расстояние < лучшее_расстояние and random.random() < заметность:
                лучшее_расстояние = расстояние
                лучшая_дафния = d
        
        if лучшая_дафния:
            if лучшая_дафния.x > self.x:
                self.x += 1
            elif лучшая_дафния.x < self.x:
                self.x -= 1
            
            if лучшая_дафния.y > self.y:
                self.y += 1
            elif лучшая_дафния.y < self.y:
                self.y -= 1
            
            self.x = max(0, min(WIDTH-1, self.x))
            self.y = max(0, min(HEIGHT-1, self.y))
            
            if abs(self.x - лучшая_дафния.x) <= 1 and abs(self.y - лучшая_дафния.y) <= 1:
                if лучшая_дафния in world.daphnia:
                    энергия_от_добычи = лучшая_дафния.energy_value() * 0.1
                    world.daphnia.remove(лучшая_дафния)
                    self.energy += энергия_от_добычи
                    self.hunger = 0
        else:
            if random.random() < 0.2:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
        
        if self.energy >= 50 and len(world.beetles) < MAX_BEETLE and random.random() < 0.02:
            детёныш = Beetle(self.x, self.y, self.genome.copy().mutate(), energy=25)
            world.beetles.append(детёныш)
            self.energy -= 30
        
        return True

class World:
    def __init__(self):
        self.algae = []
        self.daphnia = []
        self.beetles = []
        self.time = 0
        self.seconds = 0
        
        for _ in range(60):
            self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        for _ in range(25):
            self.daphnia.append(Daphnia(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        for _ in range(3):
            self.beetles.append(Beetle(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        # Открываем файл для записи статистики
        self.stats_file = open('pond_stats.csv', 'w', newline='')
        self.csv_writer = csv.writer(self.stats_file)
        # Заголовки
        self.csv_writer.writerow(['time_sec', 'algae', 'daphnia', 'beetles', 
                                  'avg_stealth', 'avg_neuroticism', 'protected'])
        self.last_save_step = 0
    
    def save_stats(self, current_seconds):
        a, d, b, stealth, neuro, protected = self.get_stats()
        self.csv_writer.writerow([current_seconds, a, d, b, stealth, neuro, protected])
        self.stats_file.flush()  # Сразу записываем на диск
        
        # Печатаем в консоль последние значения
        print(f"[{current_seconds}c] A:{a} D:{d} B:{b} | Stl:{stealth:.3f} Neuro:{neuro:.3f}")
    
    def get_stats(self):
        a = len(self.algae)
        d = len(self.daphnia)
        b = len(self.beetles)
        
        скрытность = 0
        нейротизм = 0
        под_защитой = 0
        
        if d > 0:
            for дафния in self.daphnia:
                скрытность += дафния.genome.stealth
                нейротизм += дафния.genome.neuroticism
                if дафния.pod_zashitoy(self):
                    под_защитой += 1
            скрытность = скрытность / d
            нейротизм = нейротизм / d
        
        return a, d, b, скрытность, нейротизм, под_защитой
    
    def update(self):
        if len(self.algae) < 10:
            for _ in range(20):
                self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1), energy=8))
        
        self.algae = [a for a in self.algae if a.update(self)]
        self.daphnia = [d for d in self.daphnia if d.update(self)]
        self.beetles = [b for b in self.beetles if b.update(self)]
        self.time += 1
    
    def close(self):
        self.stats_file.close()

def draw(stdscr, world, save_timer):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    for x in range(min(w-1, WIDTH)):
        stdscr.addch(SUN_TOP, x, '~')
    
    for a in world.algae:
        if a.y < h-1 and a.x < w-1:
            stdscr.addch(a.y, a.x, 'g')
    
    for b in world.beetles:
        if b.y < h-1 and b.x < w-1:
            stdscr.addch(b.y, b.x, 'B')
    
    for d in world.daphnia:
        if d.y < h-1 and d.x < w-1:
            if d.pod_zashitoy(world):
                char = '@'
            elif d.genome.stealth > 0.7:
                char = 's'
            elif d.genome.neuroticism > 0.6:
                char = '?'
            else:
                char = 'd'
            stdscr.addch(d.y, d.x, char)
    
    a, d, b, stealth, neuro, protected = world.get_stats()
    
    # Состояние системы
    if a == 0:
        state = "💀 ВЫМИРАНИЕ"
    elif d == 0:
        state = "🍽️ ДАФНИИ ИСЧЕЗЛИ"
    elif b == 0 and d > 20:
        state = "🌊 ЖУКИ ВЫМЕРЛИ"
    elif protected > d * 0.3 and d > 0:
        state = "🛡️ ПОД ЗАЩИТОЙ"
    elif neuro > 0.6:
        state = "🧠 НЕЙРОТИЧНЫЕ"
    else:
        state = "⚖️ ЦИКЛ"
    
    status = f"A:{a:3} D:{d:3} B:{b:3} | Stl:{stealth:.2f} Neuro:{neuro:.2f} | Защ:{protected} | {state}"
    status2 = f"Сохранение через: {save_timer:.0f}c | CSV: pond_stats.csv"
    stdscr.addstr(0, 0, status[:w-1])
    stdscr.addstr(1, 0, status2[:w-1])
    stdscr.addstr(h-1, 0, "ПРОБЕЛ=пауза Q=выход | @=в безопасности s=скрытная B=жук g=водоросль")
    
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    
    world = World()
    paused = False
    
    start_time = time.time()
    last_save_time = start_time
    
    print("\n🔵 ЗАПУСК СИМУЛЯЦИИ")
    print("📊 Статистика пишется в файл: pond_stats.csv")
    print("   (можно открыть в LibreOffice Calc или Excel)")
    print("🟢 Наблюдайте за эволюцией...\n")
    
    while True:
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
            if paused:
                stdscr.addstr(2, 0, "⏸ ПАУЗА")
            else:
                stdscr.addstr(2, 0, "▶ ЗАПУСК")
        
        if not paused:
            world.update()
            
            # Сохраняем статистику каждые SAVE_INTERVAL секунд
            current_time = time.time()
            if current_time - last_save_time >= SAVE_INTERVAL:
                elapsed = int(current_time - start_time)
                world.save_stats(elapsed)
                last_save_time = current_time
        
        save_timer = SAVE_INTERVAL - (time.time() - last_save_time)
        draw(stdscr, world, save_timer)
        time.sleep(0.05)
    
    world.close()
    print("\n🟢 СИМУЛЯЦИЯ ОСТАНОВЛЕНА")
    print(f"📊 Статистика сохранена в pond_stats.csv")
    print("   Чтобы построить график:")
    print("   1. Откройте файл в LibreOffice Calc")
    print("   2. Выделите столбцы")
    print("   3. Вставка → Диаграмма → Линии")

if __name__ == "__main__":
    import shutil
    size = shutil.get_terminal_size()
    if size.columns < 80 or size.lines < 24:
        print(f"Терминал слишком мал ({size.columns}x{size.lines})")
    else:
        curses.wrapper(main)
