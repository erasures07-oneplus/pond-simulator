#!/usr/bin/env python3
"""
Первый Пруд 2.0 — ИСПРАВЛЕННАЯ ВЕРСИЯ
Жуки охотятся только когда голодны, дафнии эволюционируют в скрытность
"""

import curses
import random
import time

WIDTH = 78
HEIGHT = 22
SUN_TOP = HEIGHT // 2

MAX_ALGAE = 200
MAX_DAPHNIA = 100
MAX_BEETLE = 8

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
            self.energy += 0.7
        else:
            self.energy += 0.3
        
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
                    self.energy += 5
        
        if self.energy >= 30 and len(world.daphnia) < MAX_DAPHNIA:
            child_genome = self.genome.copy().mutate()
            world.daphnia.append(Daphnia(self.x, self.y, child_genome, energy=10))
            self.energy -= 15
        
        return True
    
    def energy_value(self):
        return 15 * self.genome.efficiency

class Beetle:
    def __init__(self, x, y, genome=None, energy=40):
        self.x = x
        self.y = y
        self.genome = genome if genome else Genome(speed=0.7, stealth=0.5)
        self.energy = energy
        self.hunger = 0
    
    def update(self, world):
        # Трата энергии
        self.energy -= 0.12 / self.genome.efficiency
        self.hunger += 1
        
        # Умираем от голода
        if self.energy <= 0:
            return False
        
        # === ГЛАВНОЕ: охотимся ТОЛЬКО если голодны ===
        голоден = (self.energy < 40 or self.hunger > 30)
        
        if not голоден:
            # Сытый жук — отдыхает, еле шевелится
            if random.random() < 0.05:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
            return True
        
        # === ОХОТА ===
        # Ищем ближайшую заметную дафнию
        лучшая_дафния = None
        лучшее_расстояние = 1000
        
        for d in world.daphnia:
            # Чем выше скрытность (stealth), тем меньше шанс что жук заметит
            заметность = 1.0 - d.genome.stealth
            расстояние = abs(d.x - self.x) + abs(d.y - self.y)
            
            # Если дафния близко и заметная
            if расстояние < лучшее_расстояние and random.random() < заметность:
                лучшее_расстояние = расстояние
                лучшая_дафния = d
        
        if лучшая_дафния:
            # Движемся к цели
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
            
            # Атака
            if abs(self.x - лучшая_дафния.x) <= 1 and abs(self.y - лучшая_дафния.y) <= 1:
                if лучшая_дафния in world.daphnia:
                    энергия_от_добычи = лучшая_дафния.energy_value() * 0.1
                    world.daphnia.remove(лучшая_дафния)
                    self.energy += энергия_от_добычи
                    self.hunger = 0
        else:
            # Нет цели — просто плаваем
            if random.random() < 0.2:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
        
        # Размножение жуков
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
        
        # Водоросли
        for _ in range(60):
            self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        # Дафнии
        for _ in range(25):
            self.daphnia.append(Daphnia(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        # Жуки (всего 3)
        for _ in range(3):
            self.beetles.append(Beetle(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
    
    def update(self):
        # Защита: если водорослей почти нет — добавляем
        if len(self.algae) < 5:
            for _ in range(15):
                self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1), energy=8))
        
        # Обновляем всех
        self.algae = [a for a in self.algae if a.update(self)]
        self.daphnia = [d for d in self.daphnia if d.update(self)]
        self.beetles = [b for b in self.beetles if b.update(self)]
        self.time += 1
    
    def stats(self):
        a = len(self.algae)
        d = len(self.daphnia)
        b = len(self.beetles)
        
        # Средняя скрытность дафний
        скрытность = 0
        if d > 0:
            for дафния in self.daphnia:
                скрытность += дафния.genome.stealth
            скрытность = скрытность / d
        
        return a, d, b, скрытность

def draw(stdscr, world):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    # Рисуем солнце
    for x in range(min(w-1, WIDTH)):
        stdscr.addch(SUN_TOP, x, '~')
    
    # Водоросли (зелёные)
    for a in world.algae:
        if a.y < h-1 and a.x < w-1:
            stdscr.addch(a.y, a.x, 'g')
    
    # Дафнии
    for d in world.daphnia:
        if d.y < h-1 and d.x < w-1:
            if d.genome.stealth > 0.7:
                char = 's'  # Скрытные (эволюционировали)
            elif d.genome.neuroticism > 0.6:
                char = '?'  # Нейротичные
            else:
                char = 'd'  # Обычные
            stdscr.addch(d.y, d.x, char)
    
    # Жуки (красные B)
    for b in world.beetles:
        if b.y < h-1 and b.x < w-1:
            stdscr.addch(b.y, b.x, 'B')
    
    # Статистика
    a, d, b, stealth = world.stats()
    
    # Определяем состояние
    if a == 0:
        state = "💀 ВСЁ УМЕРЛО"
    elif d == 0 and b > 0:
        state = "🍽️ ЖУКИ ГОЛОДАЮТ"
    elif b == 0 and d > 30:
        state = "🌊 ДАФНИИ БЕЗ КОНТРОЛЯ"
    elif stealth > 0.6 and d > 15:
        state = "🛡️ ЭВОЛЮЦИЯ! СКРЫТНЫЕ ДАФНИИ"
    else:
        state = "⚖️ ЦИКЛ"
    
    status = f"Водоросли:{a:3} Дафнии:{d:3} Жуки:{b:3} | Скрытность:{stealth:.2f} | {state}"
    stdscr.addstr(0, 0, status[:w-1])
    stdscr.addstr(h-1, 0, "ПРОБЕЛ=пауза Q=выход | s=скрытная дафния B=жук g=водоросль")
    
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    
    world = World()
    paused = False
    
    while True:
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
        
        if not paused:
            world.update()
        
        draw(stdscr, world)
        time.sleep(0.05)

if __name__ == "__main__":
    import shutil
    size = shutil.get_terminal_size()
    if size.columns < 80 or size.lines < 24:
        print(f"Терминал слишком мал ({size.columns}x{size.lines})")
        print("Растяните окно или уменьшите шрифт")
    else:
        curses.wrapper(main)
