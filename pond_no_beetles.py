#!/usr/bin/env python3
"""
Первый Пруд — ВЕРСИЯ БЕЗ ХИЩНИКОВ
Только водоросли и дафнии. Проверяем, эволюционируют ли дафнии сами.
"""

import curses
import random
import time

WIDTH = 78
HEIGHT = 22
SUN_TOP = HEIGHT // 2

MAX_ALGAE = 200
MAX_DAPHNIA = 150

class Genome:
    def __init__(self, speed=1.0, efficiency=1.0, neuroticism=0.0):
        self.speed = speed
        self.efficiency = efficiency
        self.neuroticism = neuroticism
    
    def mutate(self):
        if random.random() < 0.25:
            gene = random.choice(['speed', 'efficiency', 'neuroticism'])
            delta = random.uniform(-0.2, 0.2)
            new = getattr(self, gene) + delta
            new = max(0.3, min(2.5, new))
            setattr(self, gene, new)
        return self
    
    def copy(self):
        return Genome(self.speed, self.efficiency, self.neuroticism)

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
        
        # Поиск еды
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
        
        # Размножение
        if self.energy >= 30 and len(world.daphnia) < MAX_DAPHNIA:
            child_genome = self.genome.copy().mutate()
            world.daphnia.append(Daphnia(self.x, self.y, child_genome, energy=10))
            self.energy -= 15
        
        return True

class World:
    def __init__(self):
        self.algae = []
        self.daphnia = []
        self.time = 0
        
        for _ in range(60):
            self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        for _ in range(30):
            self.daphnia.append(Daphnia(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
    
    def update(self):
        if len(self.algae) < 10:
            for _ in range(20):
                self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1), energy=8))
        
        self.algae = [a for a in self.algae if a.update(self)]
        self.daphnia = [d for d in self.daphnia if d.update(self)]
        self.time += 1
    
    def stats(self):
        a = len(self.algae)
        d = len(self.daphnia)
        
        нейротизм = 0
        скорость = 0
        if d > 0:
            for дафния in self.daphnia:
                нейротизм += дафния.genome.neuroticism
                скорость += дафния.genome.speed
            нейротизм = нейротизм / d
            скорость = скорость / d
        
        return a, d, нейротизм, скорость

def draw(stdscr, world):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    for x in range(min(w-1, WIDTH)):
        stdscr.addch(SUN_TOP, x, '~')
    
    for a in world.algae:
        if a.y < h-1 and a.x < w-1:
            stdscr.addch(a.y, a.x, 'g')
    
    for d in world.daphnia:
        if d.y < h-1 and d.x < w-1:
            if d.genome.neuroticism > 0.7:
                char = '?'
            elif d.genome.speed > 1.3:
                char = '>'
            else:
                char = 'd'
            stdscr.addch(d.y, d.x, char)
    
    a, d, neuro, speed = world.stats()
    
    if a == 0:
        state = "💀 ВЫМИРАНИЕ"
    elif d == 0:
        state = "🌱 ВОДОРОСЛИ ЦАРСТВУЮТ"
    elif neuro > 0.6:
        state = "🧠 НЕЙРОТИЧНЫЕ ДАФНИИ!"
    else:
        state = "⚖️ ЦИКЛ"
    
    status = f"Водоросли:{a:3} Дафнии:{d:3} | Нейротизм:{neuro:.2f} Скорость:{speed:.2f} | {state}"
    stdscr.addstr(0, 0, status[:w-1])
    stdscr.addstr(h-1, 0, "ПРОБЕЛ=пауза Q=выход | ?=нейротичная дафния")
    
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
    else:
        curses.wrapper(main)
