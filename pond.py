#!/usr/bin/env python3
"""
Первый Пруд 2.0 — с ХИЩНИКОМ (Жук-плавунец)
Три уровня: Водоросли → Дафнии → Жук
Правило 10% потери энергии на каждом уровне
"""

import curses
import random
import math
import time

# ========== ПАРАМЕТРЫ МИРА ==========
WIDTH = 78
HEIGHT = 22
SUN_TOP = HEIGHT // 2

MAX_ALGAE = 200
MAX_DAPHNIA = 120
MAX_BEETLE = 40

# ========== ГЕНОМЫ ==========
class Genome:
    def __init__(self, speed=1.0, efficiency=1.0, neuroticism=0.0, stealth=0.5):
        self.speed = speed           # Скорость движения
        self.efficiency = efficiency # Эффективность метаболизма
        self.neuroticism = neuroticism # 0=жадный поиск цели, 1=случайное блуждание
        self.stealth = stealth       # 0=заметный, 1=скрытный (для дафний — против хищника)

    def mutate(self):
        if random.random() < 0.2:  # 20% шанс мутации
            gene = random.choice(['speed', 'efficiency', 'neuroticism', 'stealth'])
            delta = random.uniform(-0.15, 0.15)
            new = getattr(self, gene) + delta
            new = max(0.3, min(2.5, new))
            setattr(self, gene, new)
        return self

    def copy(self):
        return Genome(self.speed, self.efficiency, self.neuroticism, self.stealth)

# ========== ВИД 1: ВОДОРОСЛИ ==========
class Algae:
    def __init__(self, x, y, energy=10):
        self.x = x
        self.y = y
        self.energy = energy

    def update(self, world):
        # Фотосинтез
        if self.y < SUN_TOP:
            self.energy += 0.6
        else:
            self.energy += 0.2

        if self.energy >= 15 and len(world.algae) < MAX_ALGAE:
            dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                world.algae.append(Algae(nx, ny, energy=5))
                self.energy -= 5

        if self.energy <= 0:
            return False
        return True

# ========== ВИД 2: ДАФНИЯ (ЖЕРТВА) ==========
class Daphnia:
    def __init__(self, x, y, genome=None, energy=20):
        self.x = x
        self.y = y
        self.genome = genome if genome else Genome()
        self.energy = energy

    def update(self, world):
        # Метаболизм
        self.energy -= 0.2 / self.genome.efficiency

        if self.energy <= 0:
            return False

        # Поиск еды (водорослей)
        target = None
        if random.random() > self.genome.neuroticism:
            min_dist = float('inf')
            for a in world.algae:
                dist = abs(a.x - self.x) + abs(a.y - self.y)
                if dist < min_dist:
                    min_dist = dist
                    target = a

        ate = False
        if target:
            dx = 1 if target.x > self.x else -1 if target.x < self.x else 0
            dy = 1 if target.y > self.y else -1 if target.y < self.y else 0
            if random.random() < self.genome.speed * 0.5:
                self.x = max(0, min(WIDTH-1, self.x + dx))
                self.y = max(0, min(HEIGHT-1, self.y + dy))

            if abs(self.x - target.x) <= 1 and abs(self.y - target.y) <= 1:
                world.algae.remove(target)
                self.energy += 5
                ate = True

        # Размножение
        if self.energy >= 30 and len(world.daphnia) < MAX_DAPHNIA:
            child_genome = self.genome.copy().mutate()
            world.daphnia.append(Daphnia(self.x, self.y, child_genome, energy=10))
            self.energy -= 15

        return True

    def energy_value(self):
        """Энергетическая ценность для хищника"""
        return 15 * self.genome.efficiency  # Эффективные дафнии вкуснее

# ========== ВИД 3: ЖУК-ПЛАВУНЕЦ (ХИЩНИК) ==========
class Beetle:
    def __init__(self, x, y, genome=None, energy=40):
        self.x = x
        self.y = y
        self.genome = genome if genome else Genome(speed=0.8, stealth=0.5)
        self.energy = energy
        self.hunger = 0

    def update(self, world):
        # Метаболизм хищника (медленнее, чем у жертвы)
        self.energy -= 0.15 / self.genome.efficiency
        self.hunger += 1

        if self.energy <= 0:
            return False

        # Поиск дафнии (с учётом скрытности жертвы)
        target = None
        best_score = -float('inf')

        for d in world.daphnia:
            # Дафнии с высоким stealth менее заметны
            visibility = 1.0 - d.genome.stealth
            distance = abs(d.x - self.x) + abs(d.y - self.y)
            # Хищник выбирает: близко + заметно + голод
            score = (1.0 / (distance + 1)) * visibility * (1.0 + self.hunger / 50)
            if score > best_score:
                best_score = score
                target = d

        if target:
            dx = 1 if target.x > self.x else -1 if target.x < self.x else 0
            dy = 1 if target.y > self.y else -1 if target.y < self.y else 0
            if random.random() < self.genome.speed * 0.4:
                self.x = max(0, min(WIDTH-1, self.x + dx))
                self.y = max(0, min(HEIGHT-1, self.y + dy))

            # Атака
            if abs(self.x - target.x) <= 1 and abs(self.y - target.y) <= 1:
                # Правило 10%: хищник получает ~10% энергии жертвы
                energy_gain = target.energy_value() * 0.1
                world.daphnia.remove(target)
                self.energy += energy_gain
                self.hunger = 0
        else:
            # Случайное движение
            if random.random() < 0.3:
                self.x += random.randint(-1, 1)
                self.y += random.randint(-1, 1)
                self.x = max(0, min(WIDTH-1, self.x))
                self.y = max(0, min(HEIGHT-1, self.y))

        # Размножение хищников (редко)
        if self.energy >= 60 and len(world.beetles) < MAX_BEETLE and random.random() < 0.05:
            child_genome = self.genome.copy().mutate()
            world.beetles.append(Beetle(self.x, self.y, child_genome, energy=25))
            self.energy -= 30

        return True

# ========== МИР ==========
class World:
    def __init__(self):
        self.algae = []
        self.daphnia = []
        self.beetles = []
        self.time = 0

        # Стартовая популяция
        for _ in range(60):
            self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        for _ in range(20):
            self.daphnia.append(Daphnia(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))
        for _ in range(3):  # Всего 3 хищника в начале
            self.beetles.append(Beetle(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)))

    def update(self):
        # Защита от вымирания водорослей (минимальная)
        if len(self.algae) < 5:
            for _ in range(10):
                self.algae.append(Algae(random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1), energy=8))

        # Обновление всех
        self.algae = [a for a in self.algae if a.update(self)]
        self.daphnia = [d for d in self.daphnia if d.update(self)]
        self.beetles = [b for b in self.beetles if b.update(self)]
        self.time += 1

    def stats(self):
        a = len(self.algae)
        d = len(self.daphnia)
        b = len(self.beetles)

        avg_d_speed = sum(dd.genome.speed for dd in self.daphnia) / d if d else 0
        avg_d_stealth = sum(dd.genome.stealth for dd in self.daphnia) / d if d else 0
        avg_b_speed = sum(bb.genome.speed for bb in self.beetles) / b if b else 0

        return a, d, b, avg_d_speed, avg_d_stealth, avg_b_speed

# ========== ОТРИСОВКА ==========
def draw(stdscr, world):
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    # Солнце
    for x in range(min(w-1, WIDTH)):
        stdscr.addch(SUN_TOP, x, '~')

    # Водоросли
    for a in world.algae:
        if a.y < h-1 and a.x < w-1:
            stdscr.addch(a.y, a.x, 'g')

    # Дафнии
    for d in world.daphnia:
        if d.y < h-1 and d.x < w-1:
            if d.genome.neuroticism > 0.6:
                char = '?'  # Нейротичные
            elif d.genome.stealth > 0.7:
                char = 's'  # Скрытные
            else:
                char = 'd'
            stdscr.addch(d.y, d.x, char)

    # Жуки-хищники
    for b in world.beetles:
        if b.y < h-1 and b.x < w-1:
            stdscr.addch(b.y, b.x, 'B')

    # Статистика
    a, d, b, dspeed, dstealth, bspeed = world.stats()

    # Диагностика состояния
    if a == 0:
        state = "💀 ВЫМИРАНИЕ"
    elif b == 0 and d > 50:
        state = "🌊 ДАФНИИ БЕЗ КОНТРОЛЯ"
    elif d == 0 and b > 0:
        state = "🍽️ ХИЩНИКИ ГОЛОДАЮТ"
    elif a > 50 and d < 10 and b < 3:
        state = "🌱 ТОЛЬКО ВОДОРОСЛИ"
    else:
        state = "⚖️ БАЛАНС"

    status = f"A:{a:3} D:{d:3} B:{b:3} | dSp:{dspeed:.2f} dSt:{dstealth:.2f} bSp:{bspeed:.2f} | {state}"
    stdscr.addstr(0, 0, status[:w-1])
    stdscr.addstr(h-1, 0, "SPACE=pause Q=quit | B=жук d=дафния g=водоросль s=скрытная ?=нейротичная")

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
        print(f"Terminal too small ({size.columns}x{size.lines}), need 80x24")
    else:
        curses.wrapper(main)
