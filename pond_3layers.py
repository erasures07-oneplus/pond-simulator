#!/usr/bin/env python3
"""
Первый Пруд 5.0 — ТРИ СРЕДЫ
Поверхность (быстрый рост), Открытая вода (норма), Дно (убежище)
Жуки НЕ могут заходить на дно
"""

import curses
import random
import time
import csv

WIDTH = 78
HEIGHT = 22

# ГРАНИЦЫ СРЕД
SURFACE_MAX = 3      # 0-3: поверхность
DEEP_MIN = 16        # 16-21: глубоководье/дно

MAX_ALGAE = 250
MAX_DAPHNIA = 120
MAX_BEETLE = 12

class Genome:
    def __init__(self, speed=1.0, efficiency=1.0, neuroticism=0.0, stealth=0.5, bottom_feeding=0.3):
        self.speed = speed
        self.efficiency = efficiency
        self.neuroticism = neuroticism
        self.stealth = stealth
        self.bottom_feeding = bottom_feeding  # 0-1: желание спускаться на дно
    
    def mutate(self):
        if random.random() < 0.2:
            gene = random.choice(['speed', 'efficiency', 'neuroticism', 'stealth', 'bottom_feeding'])
            delta = random.uniform(-0.1, 0.1)
            new = getattr(self, gene) + delta
            new = max(0.2, min(2.0, new))
            setattr(self, gene, new)
        return self
    
    def copy(self):
        return Genome(self.speed, self.efficiency, self.neuroticism, self.stealth, self.bottom_feeding)

class Algae:
    def __init__(self, x, y, energy=10):
        self.x = x
        self.y = y
        self.energy = energy
    
    def get_growth_rate(self):
        """Рост зависит от среды"""
        if self.y <= SURFACE_MAX:
            return 1.5      # Поверхность: много света
        elif self.y >= DEEP_MIN:
            return 0.3      # Дно: мало света (но безопасно)
        else:
            return 0.8      # Открытая вода: норма
    
    def update(self, world):
        growth = self.get_growth_rate()
        self.energy += growth
        
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
    
    def is_in_refuge(self):
        """На дне дафнии в безопасности от жуков"""
        return self.y >= DEEP_MIN
    
    def update(self, world):
        self.energy -= 0.2 / self.genome.efficiency
        
        if self.energy <= 0:
            return False
        
        # Поиск еды
        target = None
        if random.random() > self.genome.neuroticism:
            min_dist = float('inf')
            for a in world.algae:
                # Предпочитаем водоросли в той же среде
                dist = abs(a.x - self.x) + abs(a.y - self.y)
                if dist < min_dist:
                    min_dist = dist
                    target = a
        
        # Движение к еде или случайное
        if target:
            dx = 1 if target.x > self.x else -1 if target.x < self.x else 0
            dy = 1 if target.y > self.y else -1 if target.y < self.y else 0
            if random.random() < self.genome.speed * 0.5:
                self.x = max(0, min(WIDTH-1, self.x + dx))
                self.y = max(0, min(HEIGHT-1, self.y + dy))
            
            if abs(self.x - target.x) <= 1 and abs(self.y - target.y) <= 1:
                if target in world.algae:
                    world.algae.remove(target)
                    self.energy += 4
        else:
            # Блуждание (с учётом bottom_feeding)
            if random.random() < 0.3:
                self.x += random.randint(-1, 1)
                # Склонность к спуску на дно
                if random.random() < self.genome.bottom_feeding and self.y < HEIGHT-1:
                    self.y += 1
                elif self.y > 0:
                    self.y += random.randint(-1, 0)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
        
        # Размножение
        if self.energy >= 35 and len(world.daphnia) < MAX_DAPHNIA:
            child_genome = self.genome.copy().mutate()
            world.daphnia.append(Daphnia(self.x, self.y, child_genome, energy=10))
            self.energy -= 15
        
        return True
    
    def energy_value(self):
        return 12 * self.genome.efficiency

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
        
        # Голоден?
        голоден = (self.energy < 35 or self.hunger > 25)
        
        if not голоден and random.random() > 0.3:
            # Сытый жук отдыхает
            if random.random() < 0.05:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
            return True
        
        # ОХОТА — но НЕ на дне!
        лучшая_дафния = None
        лучшее_расстояние = 1000
        
        for d in world.daphnia:
            # Жук НЕ может есть дафний на дне
            if d.is_in_refuge():
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
        
        # Размножение
        if self.energy >= 50 and len(world.beetles) < MAX_BEETLE and random.random() < 0.03:
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
        
        # Водоросли — больше на дне (убежище)
        for _ in range(40):
            self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(DEEP_MIN, HEIGHT-1)))
        for _ in range(30):
            self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        # Дафнии — начинаем в основном в открытой воде
        for _ in range(25):
            y = random.randint(SURFACE_MAX+1, DEEP_MIN-1)
            self.daphnia.append(Daphnia(random.randint(0, WIDTH-1), y))
        
        # Жуки
        for _ in range(3):
            y = random.randint(SURFACE_MAX+1, DEEP_MIN-1)
            self.beetles.append(Beetle(random.randint(0, WIDTH-1), y))
        
        self.stats_file = open('pond_3layers_stats.csv', 'w', newline='')
        self.csv_writer = csv.writer(self.stats_file)
        self.csv_writer.writerow(['time_sec', 'algae', 'daphnia', 'beetles', 
                                  'd_stealth', 'd_bottom_feeding', 'algae_bottom'])
        self.last_save_time = 0
        self.start_time = time.time()
    
    def get_stats(self):
        a = len(self.algae)
        d = len(self.daphnia)
        b = len(self.beetles)
        
        d_stealth = 0
        d_bottom = 0
        if d > 0:
            for дафния in self.daphnia:
                d_stealth += дафния.genome.stealth
                d_bottom += дафния.genome.bottom_feeding
            d_stealth = d_stealth / d
            d_bottom = d_bottom / d
        
        # Водоросли на дне
        algae_bottom = sum(1 for a in self.algae if a.y >= DEEP_MIN)
        
        return a, d, b, d_stealth, d_bottom, algae_bottom
    
    def update(self):
        # Защита от вымирания водорослей
        if len(self.algae) < 15:
            for _ in range(15):
                y = random.choice([random.randint(DEEP_MIN, HEIGHT-1), random.randint(0, HEIGHT-1)])
                self.algae.append(Algae(random.randint(0, WIDTH-1), y, energy=8))
        
        self.algae = [a for a in self.algae if a.update(self)]
        self.daphnia = [d for d in self.daphnia if d.update(self)]
        self.beetles = [b for b in self.beetles if b.update(self)]
        self.time += 1
    
    def maybe_save(self):
        current = time.time()
        if current - self.last_save_time >= 15:
            elapsed = int(current - self.start_time)
            a, d, b, stealth, bottom, algae_bottom = self.get_stats()
            self.csv_writer.writerow([elapsed, a, d, b, stealth, bottom, algae_bottom])
            self.stats_file.flush()
            self.last_save_time = current
            print(f"[{elapsed:4}c] A:{a:3} D:{d:3} B:{b:2} | Stl:{stealth:.3f} Bottom:{bottom:.2f} | Дно:{algae_bottom}/a")
    
    def close(self):
        self.stats_file.close()

def draw(stdscr, world):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    # Рисуем границы сред
    for x in range(min(w-1, WIDTH)):
        stdscr.addch(SURFACE_MAX, x, '☀')
        stdscr.addch(DEEP_MIN, x, '~')
    
    # Водоросли
    for a in world.algae:
        if a.y < h-1 and a.x < w-1:
            if a.y >= DEEP_MIN:
                char = 'W'  # Донные водоросли
            elif a.y <= SURFACE_MAX:
                char = 'G'  # Поверхностные
            else:
                char = 'g'
            stdscr.addch(a.y, a.x, char)
    
    # Жуки
    for b in world.beetles:
        if b.y < h-1 and b.x < w-1:
            stdscr.addch(b.y, b.x, 'B')
    
    # Дафнии
    for d in world.daphnia:
        if d.y < h-1 and d.x < w-1:
            if d.is_in_refuge():
                char = 'D'  # На дне — жирная D
            elif d.genome.stealth > 0.7:
                char = 's'
            elif d.genome.bottom_feeding > 0.6:
                char = '▼'  # Склонность ко дну
            else:
                char = 'd'
            stdscr.addch(d.y, d.x, char)
    
    # Статистика
    a, d, b, stealth, bottom, algae_bottom = world.get_stats()
    
    if b == 0:
        state = "🐞 ЖУКИ ВЫМЕРЛИ"
    elif algae_bottom < 10:
        state = "⚠️ ДНО ПУСТЕЕТ"
    elif bottom > 0.6:
        state = "▼ ДАФНИИ УХОДЯТ ВНИЗ"
    else:
        state = "⚖️ РАВНОВЕСИЕ"
    
    status = f"A:{a:3} D:{d:3} B:{b:2} | Stl:{stealth:.2f} Bottom:{bottom:.2f} | Дно:{algae_bottom} | {state}"
    stdscr.addstr(0, 0, status[:w-1])
    stdscr.addstr(h-1, 0, "ПРОБЕЛ=пауза Q=выход | G=поверхность g=вода W=дно B=жук D=на дне ▼=ныряльщик")
    
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    
    world = World()
    paused = False
    
    print("\n🌊 ПРУД С ТРЕМЯ СРЕДАМИ")
    print("☀️ Поверхность (быстрый рост)")
    print("💧 Открытая вода (охота жуков)")
    print("🌿 Дно (убежище для дафний, жуки не заходят)")
    print("📊 Данные: pond_3layers_stats.csv\n")
    
    while True:
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
        
        if not paused:
            world.update()
            world.maybe_save()
        
        draw(stdscr, world)
        time.sleep(0.05)
    
    world.close()
    print("\n🟢 СИМУЛЯЦИЯ ОСТАНОВЛЕНА")

if __name__ == "__main__":
    import shutil
    size = shutil.get_terminal_size()
    if size.columns < 80 or size.lines < 24:
        print(f"Терминал слишком мал ({size.columns}x{size.lines})")
    else:
        curses.wrapper(main)
