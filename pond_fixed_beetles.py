#!/usr/bin/env python3
"""
Первый Пруд 4.0 — ЖУКИ ЭВОЛЮЦИОНИРУЮТ
Добавлены гены vision и aggression для жуков
"""

import curses
import random
import time
import csv

WIDTH = 78
HEIGHT = 22
SUN_TOP = HEIGHT // 2

MAX_ALGAE = 200
MAX_DAPHNIA = 100
MAX_BEETLE = 15  # Увеличено

# ========== ГЕНОМ ДАФНИИ ==========
class DaphniaGenome:
    def __init__(self, speed=1.0, efficiency=1.0, neuroticism=0.0, stealth=0.5):
        self.speed = speed
        self.efficiency = efficiency
        self.neuroticism = neuroticism
        self.stealth = stealth
    
    def mutate(self):
        if random.random() < 0.25:
            gene = random.choice(['speed', 'efficiency', 'neuroticism', 'stealth'])
            delta = random.uniform(-0.15, 0.15)
            new = getattr(self, gene) + delta
            new = max(0.3, min(2.5, new))
            setattr(self, gene, new)
        return self
    
    def copy(self):
        return DaphniaGenome(self.speed, self.efficiency, self.neuroticism, self.stealth)

# ========== ГЕНОМ ЖУКА (НОВЫЙ!) ==========
class BeetleGenome:
    def __init__(self, speed=0.8, efficiency=1.0, vision=1.0, aggression=0.5):
        self.speed = speed          # Скорость движения
        self.efficiency = efficiency # Эффективность метаболизма
        self.vision = vision        # Зрение (против stealth дафний)
        self.aggression = aggression # Агрессивность (0-1, как часто охотится)
    
    def mutate(self):
        if random.random() < 0.25:
            gene = random.choice(['speed', 'efficiency', 'vision', 'aggression'])
            delta = random.uniform(-0.15, 0.15)
            new = getattr(self, gene) + delta
            new = max(0.3, min(2.5, new))
            setattr(self, gene, new)
        return self
    
    def copy(self):
        return BeetleGenome(self.speed, self.efficiency, self.vision, self.aggression)

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
        self.genome = genome if genome else DaphniaGenome()
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
        
        if self.energy >= 35 and len(world.daphnia) < MAX_DAPHNIA:
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
        return True if random.random() < 0.3 else False

class Beetle:
    def __init__(self, x, y, genome=None, energy=35):
        self.x = x
        self.y = y
        self.genome = genome if genome else BeetleGenome()
        self.energy = energy
        self.hunger = 0
    
    def update(self, world):
        self.energy -= 0.12 / self.genome.efficiency
        self.hunger += 1
        
        if self.energy <= 0:
            return False
        
        # Агрессивность определяет, будет ли жук охотиться
        будет_охотиться = random.random() < self.genome.aggression
        голоден = (self.energy < 35 or self.hunger > 25)
        
        if not (будет_охотиться or голоден):
            # Отдых
            if random.random() < 0.05:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
            return True
        
        # Охота — с учётом зрения жука и скрытности дафнии
        лучшая_дафния = None
        лучшее_расстояние = 1000
        
        for d in world.daphnia:
            if d.pod_zashitoy(world):
                continue
            
            # КЛЮЧЕВАЯ ФОРМУЛА: заметность = скрытность_дафнии против зрение_жука
            заметность = max(0, 1.0 - d.genome.stealth + (0.5 / self.genome.vision))
            # Чем выше vision у жука, тем больше шанс заметить стелс-дафнию
            
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
                    энергия_от_добычи = лучшая_дафния.energy_value() * 0.12
                    world.daphnia.remove(лучшая_дафния)
                    self.energy += энергия_от_добычи
                    self.hunger = 0
        else:
            if random.random() < 0.2:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))
        
        # Размножение — УПРОЩЕНО
        if self.energy >= 45 and len(world.beetles) < MAX_BEETLE and random.random() < 0.05:
            детёныш = Beetle(self.x, self.y, self.genome.copy().mutate(), energy=25)
            world.beetles.append(детёныш)
            self.energy -= 25
        
        return True

class World:
    def __init__(self):
        self.algae = []
        self.daphnia = []
        self.beetles = []
        self.time = 0
        
        for _ in range(80):
            self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        for _ in range(30):
            self.daphnia.append(Daphnia(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        
        # Стартуем с 5 жуками, разными
        for _ in range(5):
            genome = BeetleGenome(
                speed=random.uniform(0.6, 1.0),
                vision=random.uniform(0.7, 1.3),
                aggression=random.uniform(0.4, 0.8)
            )
            self.beetles.append(Beetle(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1), genome))
        
        self.stats_file = open('pond_fixed_stats.csv', 'w', newline='')
        self.csv_writer = csv.writer(self.stats_file)
        self.csv_writer.writerow(['time_sec', 'algae', 'daphnia', 'beetles', 
                                  'd_stealth', 'b_vision', 'b_aggression'])
        self.last_save_time = 0
        self.start_time = time.time()
    
    def get_stats(self):
        a = len(self.algae)
        d = len(self.daphnia)
        b = len(self.beetles)
        
        d_stealth = 0
        if d > 0:
            for дафния in self.daphnia:
                d_stealth += дафния.genome.stealth
            d_stealth = d_stealth / d
        
        b_vision = 0
        b_aggression = 0
        if b > 0:
            for жук in self.beetles:
                b_vision += жук.genome.vision
                b_aggression += жук.genome.aggression
            b_vision = b_vision / b
            b_aggression = b_aggression / b
        
        return a, d, b, d_stealth, b_vision, b_aggression
    
    def update(self):
        if len(self.algae) < 10:
            for _ in range(20):
                self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1), energy=8))
        
        self.algae = [a for a in self.algae if a.update(self)]
        self.daphnia = [d for d in self.daphnia if d.update(self)]
        self.beetles = [b for b in self.beetles if b.update(self)]
        self.time += 1
    
    def maybe_save(self):
        current = time.time()
        if current - self.last_save_time >= 10:
            elapsed = int(current - self.start_time)
            a, d, b, d_stealth, b_vision, b_agg = self.get_stats()
            self.csv_writer.writerow([elapsed, a, d, b, d_stealth, b_vision, b_agg])
            self.stats_file.flush()
            self.last_save_time = current
            print(f"[{elapsed}c] A:{a} D:{d} B:{b} | Stl:{d_stealth:.3f} Vis:{b_vision:.3f} Agg:{b_agg:.3f}")
    
    def close(self):
        self.stats_file.close()

def draw(stdscr, world):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    for x in range(min(w-1, WIDTH)):
        stdscr.addch(SUN_TOP, x, '~')
    
    for a in world.algae:
        if a.y < h-1 and a.x < w-1:
            stdscr.addch(a.y, a.x, 'g')
    
    for b in world.beetles:
        if b.y < h-1 and b.x < w-1:
            # Разные символы для жуков
            if b.genome.vision > 1.2:
                char = '👁'
            elif b.genome.aggression > 0.7:
                char = '⚔'
            else:
                char = 'B'
            try:
                stdscr.addch(b.y, b.x, char)
            except:
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
    
    a, d, b, stealth, vision, agg = world.get_stats()
    
    if b == 0:
        state = "🐞 ЖУКИ ВЫМЕРЛИ"
    elif stealth > 0.8 and vision < 1.0:
        state = "🛡️ СТЕЛСЫ ПРОТИВ СЛЕПЫХ ЖУКОВ"
    elif vision > 1.2:
        state = "👁 ЖУКИ УЧАТСЯ ВИДЕТЬ"
    elif d == 0:
        state = "💀 ДАФНИИ ИСЧЕЗЛИ"
    else:
        state = "⚖️ ГОНКА ВООРУЖЕНИЙ"
    
    status = f"A:{a:3} D:{d:3} B:{b:3} | Stl:{stealth:.2f} Vis:{vision:.2f} Agg:{agg:.2f} | {state}"
    stdscr.addstr(0, 0, status[:w-1])
    stdscr.addstr(h-1, 0, "ПРОБЕЛ=пауза Q=выход | @=защита s=стелс B=жук g=водоросль 👁=зрячий жук")
    
    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)
    
    world = World()
    paused = False
    
    print("\n🔬 НОВАЯ ЭВОЛЮЦИОННАЯ ГОНКА")
    print("📊 Жуки теперь эволюционируют: vision (зрение) и aggression (агрессия)")
    print("🟢 Наблюдайте, кто победит — стелс-дафнии или зрячие жуки\n")
    
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
    print("📊 Данные сохранены в pond_fixed_stats.csv")

if __name__ == "__main__":
    import shutil
    size = shutil.get_terminal_size()
    if size.columns < 80 or size.lines < 24:
        print(f"Терминал слишком мал ({size.columns}x{size.lines})")
    else:
        curses.wrapper(main)