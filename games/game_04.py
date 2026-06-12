import pygame
import math
import random
import json
import os
import sys
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# 初始化 Pygame
pygame.init()
pygame.mixer.init()

# ==================== 常量定义 ====================
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GRAY = (128, 128, 128)

# ==================== 音效管理器 (SoundManager) ====================
# 为了单文件运行，我们使用简单的频率生成声音，或者加载备用文件
class SoundManager:
    def __init__(self):
        self.sounds = {}
        # 这里我们尝试加载文件，如果不存在则生成简单的 beep 声
        # 在实际游戏中，你应该加载 .wav 或 .mp3 文件
        self.init_sounds()

    def init_sounds(self):
        # 生成简单的合成音效作为占位符
        # 注意：pygame.mixer 需要频率、位数、通道等
        # 为了简化，我们只定义结构，实际游戏中应加载文件
        
        # 示例：如果文件存在则加载，否则标记为 None
        file_paths = {
            'shoot': 'assets/sounds/shoot.wav',
            'explosion': 'assets/sounds/explosion.wav',
            'powerup': 'assets/sounds/powerup.wav',
            'hit': 'assets/sounds/hit.wav',
            'boss': 'assets/sounds/boss_theme.wav',
            'level_up': 'assets/sounds/level_up.wav'
        }
        
        for name, path in file_paths.items():
            try:
                if os.path.exists(path):
                    self.sounds[name] = pygame.mixer.Sound(path)
                else:
                    # 如果资源不存在，创建一个空的 Sound 对象或忽略
                    # 在实际部署中，请确保 assets/sounds 目录存在
                    self.sounds[name] = None 
            except Exception:
                self.sounds[name] = None

    def play(self, sound_name):
        if sound_name in self.sounds and self.sounds[sound_name]:
            try:
                self.sounds[sound_name].play()
            except:
                pass

    def stop_all(self):
        pygame.mixer.stop()

# ==================== 粒子系统 (ParticleSystem) ====================
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size *= 0.95  # 逐渐缩小

    def draw(self, screen):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            # 简单绘制圆形粒子
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), max(1, int(self.size)))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, count, color, speed_range=(1, 3), size_range=(2, 5), life_range=(20, 40)):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.uniform(*size_range)
            life = random.randint(*life_range)
            self.particles.append(Particle(x, y, vx, vy, color, life, size))

    def update(self):
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# ==================== 成就系统 (Achievement System) ====================
@dataclass
class Achievement:
    id: str
    name: str
    description: str
    unlocked: bool = False
    unlocked_count: int = 0

class AchievementManager:
    def __init__(self):
        self.achievements = {
            "first_blood": Achievement("first_blood", "First Blood", "Kill your first enemy", False),
            "sharpshooter": Achievement("sharpshooter", "Sharpshooter", "Kill 100 enemies", False, 0),
            "boss_slayer": Achievement("boss_slayer", "Boss Slayer", "Defeat a Boss", False),
            "survivor": Achievement("survivor", "Survivor", "Reach Wave 5", False),
            "collector": Achievement("collector", "Collector", "Collect 50 power-ups", False, 0),
            "speed_demon": Achievement("speed_demon", "Speed Demon", "Kill 10 enemies within 5 seconds", False),
            "tank": Achievement("tank", "Tank", "Survive a boss hit with < 10% HP", False),
            "explorer": Achievement("explorer", "Explorer", "Visit all 3 levels", False, 0),
            "max_level": Achievement("max_level", "Max Level", "Reach Level 10", False),
            "clean_sweep": Achievement("clean_sweep", "Clean Sweep", "Clear a wave without taking damage", False)
        }
        self.stats = {
            "enemies_killed": 0,
            "powerups_collected": 0,
            "waves_survived": 0,
            "bosses_defeated": 0,
            "levels_visited": set(),
            "high_dmg_time": 0,
            "last_kill_time": 0
        }

    def check_kill(self, is_boss=False):
        self.stats["enemies_killed"] += 1
        if self.stats["enemies_killed"] >= 1:
            self.unlock("first_blood")
        if self.stats["enemies_killed"] >= 100:
            self.unlock("sharpshooter")
        
        if is_boss:
            self.stats["bosses_defeated"] += 1
            self.unlock("boss_slayer")

        # Speed demon check (simplified)
        current_time = pygame.time.get_ticks()
        if current_time - self.stats["last_kill_time"] < 5000:
            self.stats["high_dmg_time"] += 1
            if self.stats["high_dmg_time"] >= 10:
                self.unlock("speed_demon")
                self.stats["high_dmg_time"] = 0
        else:
            self.stats["high_dmg_time"] = 0
        self.stats["last_kill_time"] = current_time

    def check_powerup(self):
        self.stats["powerups_collected"] += 1
        if self.stats["powerups_collected"] >= 50:
            self.unlock("collector")

    def check_wave(self, wave):
        self.stats["waves_survived"] = wave
        if wave >= 5:
            self.unlock("survivor")

    def check_level(self, level):
        if level >= 10:
            self.unlock("max_level")

    def check_level_visit(self, level_id):
        self.stats["levels_visited"].add(level_id)
        if len(self.stats["levels_visited"]) >= 3:
            self.unlock("explorer")

    def unlock(self, id):
        if id in self.achievements and not self.achievements[id].unlocked:
            self.achievements[id].unlocked = True
            self.achievements[id].unlocked_count += 1
            # In a real game, show a popup here

    def get_all(self):
        return self.achievements

# ==================== 存档系统 (Save System) ====================
class SaveSystem:
    SAVE_FILE = "save_data.json"

    def __init__(self):
        self.data = {
            "high_score": 0,
            "unlocked_achievements": [],
            "player_level": 1,
            "player_xp": 0,
            "current_wave": 1,
            "current_level": 1
        }
        self.load()

    def save(self, high_score, achievements, level, xp, wave, level_id):
        unlocked_ids = [k for k, v in achievements.items() if v.unlocked]
        self.data = {
            "high_score": high_score,
            "unlocked_achievements": unlocked_ids,
            "player_level": level,
            "player_xp": xp,
            "current_wave": wave,
            "current_level": level_id
        }
        with open(self.SAVE_FILE, 'w') as f:
            json.dump(self.data, f)

    def load(self):
        if os.path.exists(self.SAVE_FILE):
            try:
                with open(self.SAVE_FILE, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = {
                    "high_score": 0,
                    "unlocked_achievements": [],
                    "player_level": 1,
                    "player_xp": 0,
                    "current_wave": 1,
                    "current_level": 1
                }
        else:
            self.data = {
                "high_score": 0,
                "unlocked_achievements": [],
                "player_level": 1,
                "player_xp": 0,
                "current_wave": 1,
                "current_level": 1
            }
        return self.data

# ==================== 武器系统 (Weapon System) ====================
class WeaponType(Enum):
    BLASTER = "blaster"
    SHOTGUN = "shotgun"
    RAILGUN = "railgun"
    LASER = "laser"
    MISSILE = "missile"
    PLASMA = "plasma"

class Weapon:
    def __init__(self, w_type: WeaponType, damage, fire_rate, cooldown, bullet_speed, bullet_size, color):
        self.w_type = w_type
        self.damage = damage
        self.fire_rate = fire_rate  # Shots per second
        self.cooldown = 1.0 / fire_rate
        self.current_cooldown = 0
        self.bullet_speed = bullet_speed
        self.bullet_size = bullet_size
        self.color = color

    def can_fire(self, dt):
        if self.current_cooldown > 0:
            self.current_cooldown -= dt
            return False
        return True

    def reset_cooldown(self):
        self.current_cooldown = self.cooldown

# 武器工厂
def get_weapons():
    return {
        WeaponType.BLASTER: Weapon(WeaponType.BLASTER, 10, 10, 0.1, 10, 3, WHITE),
        WeaponType.SHOTGUN: Weapon(WeaponType.SHOTGUN, 8, 2, 0.5, 8, 2, YELLOW),
        WeaponType.RAILGUN: Weapon(WeaponType.RAILGUN, 50, 1, 1.0, 20, 2, CYAN),
        WeaponType.LASER: Weapon(WeaponType.LASER, 2, 20, 0.05, 15, 1, RED),
        WeaponType.MISSILE: Weapon(WeaponType.MISSILE, 30, 3, 0.33, 5, 6, ORANGE),
        WeaponType.PLASMA: Weapon(WeaponType.PLASMA, 20, 5, 0.2, 7, 8, MAGENTA)
    }

# ==================== 玩家类 (Player) ====================
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.speed = 5
        self.hp = 100
        self.max_hp = 100
        self.xp = 0
        self.level = 1
        self.xp_to_next = 100
        self.weapons = get_weapons()
        self.current_weapon = WeaponType.BLASTER
        self.score = 0
        self.shield = 0
        self.invulnerable_time = 0
        self.angle = 0  # Radians
        self.velocity = pygame.Vector2(0, 0)

    def update(self, dt, keys, mouse_pos, screen_width, screen_height):
        # Movement
        self.velocity = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            self.velocity.y -= self.speed
        if keys[pygame.K_s]:
            self.velocity.y += self.speed
        if keys[pygame.K_a]:
            self.velocity.x -= self.speed
        if keys[pygame.K_d]:
            self.velocity.x += self.speed

        # Normalize diagonal movement
        if self.velocity.length() > self.speed:
            self.velocity.scale_to_length(self.speed)

        self.x += self.velocity.x
        self.y += self.velocity.y

        # Boundary check
        self.x = max(self.width // 2, min(screen_width - self.width // 2, self.x))
        self.y = max(self.height // 2, min(screen_height - self.height // 2, self.y))

        # Rotation towards mouse
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        if dx != 0 or dy != 0:
            self.angle = math.atan2(dy, dx)

        # Invulnerability timer
        if self.invulnerable_time > 0:
            self.invulnerable_time -= dt

    def take_damage(self, amount):
        if self.invulnerable_time > 0:
            return
        if self.shield > 0:
            absorb = min(self.shield, amount)
            self.shield -= absorb
            amount -= absorb
        if amount > 0:
            self.hp -= amount
            return True
        return False

    def add_xp(self, amount):
        self.xp += amount
        if self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)
            self.hp = self.max_hp  # Heal on level up
            return True  # Level up occurred
        return False

    def draw(self, screen):
        # Draw player ship (Triangle)
        points = [
            (self.x, self.y - self.height // 2),
            (self.x - self.width // 2, self.y + self.height // 2),
            (self.x + self.width // 2, self.y + self.height // 2)
        ]
        # Rotate points
        cx, cy = self.x, self.y
        cos_a, sin_a = math.cos(self.angle), math.sin(self.angle)
        rotated_points = []
        for px, py in points:
            rx = cx + (px - cx) * cos_a - (py - cy) * sin_a
            ry = cy + (px - cx) * sin_a + (py - cy) * cos_a
            rotated_points.append((rx, ry))
        
        color = GREEN
        if self.invulnerable_time > 0 and int(pygame.time.get_ticks() / 100) % 2 == 0:
            color = GRAY
        pygame.draw.polygon(screen, color, rotated_points)

        # Draw Shield
        if self.shield > 0:
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), self.width // 2 + 5, 2)

# ==================== 敌人系统 (Enemy System) ====================
class EnemyType(Enum):
    BASIC = "basic"
    FAST = "fast"
    TANK = "tank"
    SHOOTER = "shooter"
    BOSS = "boss"

class Enemy:
    def __init__(self, x, y, e_type: EnemyType, wave_multiplier=1.0):
        self.x = x
        self.y = y
        self.e_type = e_type
        self.wave_multiplier = wave_multiplier
        
        # Stats based on type
        if e_type == EnemyType.BASIC:
            self.hp = 20 * wave_multiplier
            self.speed = 2
            self.score = 10
            self.color = RED
            self.size = 20
        elif e_type == EnemyType.FAST:
            self.hp = 10 * wave_multiplier
            self.speed = 4
            self.score = 15
            self.color = ORANGE
            self.size = 15
        elif e_type == EnemyType.TANK:
            self.hp = 50 * wave_multiplier
            self.speed = 1
            self.score = 30
            self.color = PURPLE
            self.size = 30
        elif e_type == EnemyType.SHOOTER:
            self.hp = 30 * wave_multiplier
            self.speed = 1.5
            self.score = 25
            self.color = MAGENTA
            self.size = 25
        elif e_type == EnemyType.BOSS:
            self.hp = 500 * wave_multiplier
            self.speed = 0.5
            self.score = 500
            self.color = YELLOW
            self.size = 60
            self.phase = 1
            self.phase_timer = 0

        self.max_hp = self.hp
        self.shoot_timer = 0
        self.move_pattern = 0  # For boss or complex movement

    def update(self, dt, player_x, player_y, screen_width, screen_height):
        # Basic movement towards player
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)
        
        if dist > 0:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

        # Boss specific logic
        if self.e_type == EnemyType.BOSS:
            self.phase_timer += dt
            if self.phase_timer > 10:  # Change phase every 10 seconds
                self.phase = (self.phase % 3) + 1
                self.phase_timer = 0
                self.speed = 0.5 if self.phase == 1 else (1.0 if self.phase == 2 else 2.0)

    def shoot(self, bullet_speed=5):
        # Return list of bullets to be added to enemy bullets list
        bullets = []
        if self.e_type == EnemyType.SHOOTER:
            angle = math.atan2(pygame.mouse.get_pos()[1] - self.y, pygame.mouse.get_pos()[0] - self.x)
            bullets.append({'x': self.x, 'y': self.y, 'vx': math.cos(angle) * bullet_speed, 'vy': math.sin(angle) * bullet_speed, 'color': MAGENTA, 'size': 4})
        elif self.e_type == EnemyType.BOSS:
            # Boss shoots in patterns
            if self.phase == 1:
                for i in range(8):
                    angle = (i / 8) * math.pi * 2
                    bullets.append({'x': self.x, 'y': self.y, 'vx': math.cos(angle) * bullet_speed, 'vy': math.sin(angle) * bullet_speed, 'color': YELLOW, 'size': 6})
            elif self.phase == 2:
                angle = math.atan2(pygame.mouse.get_pos()[1] - self.y, pygame.mouse.get_pos()[0] - self.x)
                for i in range(-1, 2):
                    offset_angle = angle + i * 0.2
                    bullets.append({'x': self.x, 'y': self.y, 'vx': math.cos(offset_angle) * bullet_speed * 1.5, 'vy': math.sin(offset_angle) * bullet_speed * 1.5, 'color': RED, 'size': 5})
            elif self.phase == 3:
                for i in range(16):
                    angle = (i / 16) * math.pi * 2
                    bullets.append({'x': self.x, 'y': self.y, 'vx': math.cos(angle) * bullet_speed * 0.8, 'vy': math.sin(angle) * bullet_speed * 0.8, 'color': ORANGE, 'size': 4})
        return bullets

    def draw(self, screen):
        color = self.color
        if self.e_type == EnemyType.BOSS:
            # Boss draws differently
            pygame.draw.rect(screen, color, (self.x - self.size, self.y - self.size, self.size * 2, self.size * 2))
            # Phase indicator
            phase_color = GREEN if self.phase == 1 else BLUE if self.phase == 2 else RED
            pygame.draw.circle(screen, phase_color, (int(self.x), int(self.y)), 5)
        else:
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.size // 2)
        
        # Health bar
        hp_ratio = self.hp / self.max_hp
        if hp_ratio < 1.0:
            bar_width = 40
            bar_height = 5
            pygame.draw.rect(screen, RED, (self.x - bar_width//2, self.y - self.size - 10, bar_width, bar_height))
            pygame.draw.rect(screen, GREEN, (self.x - bar_width//2, self.y - self.size - 10, bar_width * hp_ratio, bar_height))

# ==================== 道具系统 (PowerUp System) ====================
class PowerUpType(Enum):
    HEALTH = "health"
    SHIELD = "shield"
    SPEED = "speed"
    WEAPON_UPGRADE = "weapon_upgrade"
    BOMB = "bomb"
    XP_BOOST = "xp_boost"
    MEGA_SHOT = "mega_shot"
    FREEZE = "freeze"

class PowerUp:
    def __init__(self, x, y, p_type: PowerUpType):
        self.x = x
        self.y = y
        self.p_type = p_type
        self.speed = 2
        self.size = 15
        self.angle = 0

    def update(self):
        self.y += self.speed
        self.angle += 0.1

    def draw(self, screen):
        color = WHITE
        if self.p_type == PowerUpType.HEALTH: color = RED
        elif self.p_type == PowerUpType.SHIELD: color = CYAN
        elif self.p_type == PowerUpType.SPEED: color = YELLOW
        elif self.p_type == PowerUpType.WEAPON_UPGRADE: color = GREEN
        elif self.p_type == PowerUpType.BOMB: color = BLACK
        elif self.p_type == PowerUpType.XP_BOOST: color = MAGENTA
        elif self.p_type == PowerUpType.MEGA_SHOT: color = ORANGE
        elif self.p_type == PowerUpType.FREEZE: color = BLUE
        
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.size // 2)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.size // 2, 2)

# ==================== 游戏状态与场景 ====================
class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    ACHIEVEMENTS = "achievements"
    SHOP = "shop"

class Level:
    def __init__(self, level_id, bg_color, enemy_spawn_rate, enemy_types):
        self.level_id = level_id
        self.bg_color = bg_color
        self.enemy_spawn_rate = enemy_spawn_rate  # Seconds between spawns
        self.enemy_types = enemy_types
        self.spawn_timer = 0

    def update(self, dt):
        self.spawn_timer += dt

# ==================== 主游戏类 ====================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter - Agnes-2.0 Flash")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 24)
        self.big_font = pygame.font.SysFont("arial", 48)
        
        self.state = GameState.MENU
        self.sound_manager = SoundManager()
        self.achievement_manager = AchievementManager()
        self.save_system = SaveSystem()
        
        self.reset_game()
        
        # Load saved achievements
        saved_data = self.save_system.load()
        for aid in saved_data.get("unlocked_achievements", []):
            if aid in self.achievement_manager.achievements:
                self.achievement_manager.achievements[aid].unlocked = True

        self.running = True

    def reset_game(self):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.enemies = []
        self.enemy_bullets = []
        self.player_bullets = []
        self.powerups = []
        self.particles = ParticleSystem()
        self.wave = 1
        self.level_id = 1
        self.current_level = Level(1, BLACK, 1.0, [EnemyType.BASIC])
        self.wave_enemies_left = 10
        self.wave_active = False
        self.boss_spawned = False
        self.game_over = False
        self.score = 0
        self.high_score = self.save_system.data.get("high_score", 0)
        
        # Level definitions
        self.levels = {
            1: Level(1, BLACK, 1.0, [EnemyType.BASIC]),
            2: Level(2, (10, 10, 30), 0.8, [EnemyType.BASIC, EnemyType.FAST]),
            3: Level(3, (20, 0, 0), 0.6, [EnemyType.BASIC, EnemyType.TANK, EnemyType.SHOOTER])
        }

    def start_game(self):
        self.state = GameState.PLAYING
        self.reset_game()
        self.start_wave()

    def start_wave(self):
        self.wave_active = True
        self.boss_spawned = False
        if self.wave % 5 == 0:
            # Boss Wave
            self.wave_enemies_left = 1
            self.enemies.append(Enemy(SCREEN_WIDTH // 2, -100, EnemyType.BOSS, 1 + self.wave * 0.1))
        else:
            self.wave_enemies_left = 5 + self.wave * 2
            self.current_level.spawn_timer = 0

    def spawn_enemy(self):
        if not self.wave_active:
            return
        
        if self.wave % 5 == 0:
            # Boss already spawned
            return

        if self.wave_enemies_left <= 0:
            return

        # Spawn logic
        if random.random() < 0.02: # Simple rate control
            e_type = random.choice(self.current_level.enemy_types)
            x = random.randint(20, SCREEN_WIDTH - 20)
            self.enemies.append(Enemy(x, -30, e_type, 1 + self.wave * 0.05))
            self.wave_enemies_left -= 1

    def update(self, dt):
        if self.state != GameState.PLAYING:
            return

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        # Update Player
        self.player.update(dt, keys, mouse_pos, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Shooting
        if keys[pygame.K_SPACE]:
            weapon = self.player.weapons[self.player.current_weapon]
            if weapon.can_fire(dt):
                self.shoot_bullet(weapon)
                weapon.reset_cooldown()

        # Update Player Bullets
        for b in self.player_bullets[:]:
            b['x'] += b['vx']
            b['y'] += b['vy']
            if b['y'] < 0 or b['y'] > SCREEN_HEIGHT or b['x'] < 0 or b['x'] > SCREEN_WIDTH:
                self.player_bullets.remove(b)

        # Update Enemies
        for enemy in self.enemies[:]:
            enemy.update(dt, self.player.x, self.player.y, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Enemy Shooting
            if enemy.e_type in [EnemyType.SHOOTER, EnemyType.BOSS]:
                enemy.shoot_timer += dt
                if enemy.shoot_timer > 1.0: # Shoot every second
                    new_bullets = enemy.shoot()
                    self.enemy_bullets.extend(new_bullets)
                    enemy.shoot_timer = 0

            # Collision: Enemy vs Player
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist < enemy.size // 2 + self.player.width // 2:
                self.player.take_damage(10)
                self.sound_manager.play('hit')
                self.particles.emit(self.player.x, self.player.y, 10, RED)
                self.enemies.remove(enemy)
                if self.player.hp <= 0:
                    self.game_over = True
                    self.state = GameState.GAME_OVER
                    if self.score > self.high_score:
                        self.high_score = self.score

        # Update Enemy Bullets
        for b in self.enemy_bullets[:]:
            b['x'] += b['vx']
            b['y'] += b['vy']
            if b['y'] < 0 or b['y'] > SCREEN_HEIGHT or b['x'] < 0 or b['x'] > SCREEN_WIDTH:
                self.enemy_bullets.remove(b)
            
            # Collision: Enemy Bullet vs Player
            dist = math.hypot(b['x'] - self.player.x, b['y'] - self.player.y)
            if dist < 10: # Bullet size approx
                self.player.take_damage(10)
                self.sound_manager.play('hit')
                self.particles.emit(self.player.x, self.player.y, 5, RED)
                self.enemy_bullets.remove(b)
                if self.player.hp <= 0:
                    self.game_over = True
                    self.state = GameState.GAME_OVER

        # Collision: Player Bullets vs Enemies
        for pb in self.player_bullets[:]:
            for enemy in self.enemies[:]:
                dist = math.hypot(pb['x'] - enemy.x, pb['y'] - enemy.y)
                if dist < enemy.size // 2 + 5:
                    enemy.hp -= pb['damage']
                    self.particles.emit(enemy.x, enemy.y, 3, enemy.color)
                    self.player_bullets.remove(pb)
                    
                    if enemy.hp <= 0:
                        self.enemies.remove(enemy)
                        self.score += enemy.score
                        self.player.add_xp(enemy.score // 2)
                        self.achievement_manager.check_kill(enemy.e_type == EnemyType.BOSS)
                        self.sound_manager.play('explosion')
                        self.particles.emit(enemy.x, enemy.y, 20, enemy.color, size_range=(5, 10))
                        
                        # Drop PowerUp
                        if random.random() < 0.2:
                            p_type = random.choice(list(PowerUpType))
                            self.powerups.append(PowerUp(enemy.x, enemy.y, p_type))
                        
                        if enemy.e_type == EnemyType.BOSS:
                            self.boss_spawned = True
                            self.wave_active = False
                            # Next wave immediately after boss
                            self.wave += 1
                            self.start_wave()
                        break

        # Collision: Player vs PowerUps
        for pu in self.powerups[:]:
            pu.update()
            dist = math.hypot(pu.x - self.player.x, pu.y - self.player.y)
            if dist < pu.size // 2 + self.player.width // 2:
                self.apply_powerup(pu.p_type)
                self.powerups.remove(pu)
                self.sound_manager.play('powerup')
                self.achievement_manager.check_powerup()

        # Check Wave Completion
        if not self.boss_spawned and self.wave_enemies_left <= 0 and len(self.enemies) == 0:
            self.wave_active = False
            self.wave += 1
            # Check level progression
            if self.wave % 10 == 0:
                self.level_id = (self.level_id % 3) + 1
                self.current_level = self.levels[self.level_id]
                self.achievement_manager.check_level_visit(self.level_id)
            
            self.start_wave()

        # Update Achievements
        self.achievement_manager.check_wave(self.wave)
        self.achievement_manager.check_level(self.player.level)

        # Update Particles
        self.particles.update()

    def apply_powerup(self, p_type):
        if p_type == PowerUpType.HEALTH:
            self.player.hp = min(self.player.hp + 30, self.player.max_hp)
        elif p_type == PowerUpType.SHIELD:
            self.player.shield = 50
        elif p_type == PowerUpType.SPEED:
            self.player.speed = 8
            pygame.time.set_timer(pygame.USEREVENT, 5000) # Reset speed after 5s
            self.speed_timer = pygame.time.get_ticks()
        elif p_type == PowerUpType.WEAPON_UPGRADE:
            # Cycle to next weapon
            w_list = list(WeaponType)
            current_idx = w_list.index(self.player.current_weapon)
            self.player.current_weapon = w_list[(current_idx + 1) % len(w_list)]
        elif p_type == PowerUpType.BOMB:
            # Destroy all enemies on screen
            for enemy in self.enemies:
                self.enemies.remove(enemy)
                self.score += enemy.score
                self.particles.emit(enemy.x, enemy.y, 20, enemy.color)
            self.enemy_bullets.clear()
            self.sound_manager.play('explosion')
        elif p_type == PowerUpType.XP_BOOST:
            self.player.add_xp(50)
        elif p_type == PowerUpType.MEGA_SHOT:
            # Temporary double damage or rapid fire (simplified as rapid fire)
            weapon = self.player.weapons[self.player.current_weapon]
            weapon.fire_rate *= 2
            pygame.time.set_timer(pygame.USEREVENT, 10000) # Reset after 10s
        elif p_type == PowerUpType.FREEZE:
            # Freeze enemies for 3 seconds
            for enemy in self.enemies:
                enemy.speed = 0
            pygame.time.set_timer(pygame.USEREVENT, 3000)

    def shoot_bullet(self, weapon):
        angle = self.player.angle
        vx = math.cos(angle) * weapon.bullet_speed
        vy = math.sin(angle) * weapon.bullet_speed
        
        # Offset bullet start to tip of ship
        tip_x = self.player.x + math.cos(angle) * 20
        tip_y = self.player.y + math.sin(angle) * 20

        if weapon.w_type == WeaponType.SHOTGUN:
            for i in range(-1, 2):
                spread_angle = angle + i * 0.2
                self.player_bullets.append({
                    'x': tip_x, 'y': tip_y,
                    'vx': math.cos(spread_angle) * weapon.bullet_speed,
                    'vy': math.sin(spread_angle) * weapon.bullet_speed,
                    'damage': weapon.damage,
                    'color': weapon.color,
                    'size': weapon.bullet_size
                })
        elif weapon.w_type == WeaponType.RAILGUN:
            # Instant hit (simplified as fast bullet)
            self.player_bullets.append({
                'x': tip_x, 'y': tip_y,
                'vx': vx * 2, 'vy': vy * 2,
                'damage': weapon.damage,
                'color': weapon.color,
                'size': weapon.bullet_size
            })
        else:
            self.player_bullets.append({
                'x': tip_x, 'y': tip_y,
                'vx': vx, 'vy': vy,
                'damage': weapon.damage,
                'color': weapon.color,
                'size': weapon.bullet_size
            })
        
        self.sound_manager.play('shoot')
        self.particles.emit(tip_x, tip_y, 2, weapon.color, speed_range=(0, 1), size_range=(1, 2))

    def draw(self):
        self.screen.fill(self.current_level.bg_color)

        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.PLAYING:
            self.draw_game()
        elif self.state == GameState.PAUSED:
            self.draw_game()
            self.draw_overlay("PAUSED")
        elif self.state == GameState.GAME_OVER:
            self.draw_game()
            self.draw_game_over()
        elif self.state == GameState.ACHIEVEMENTS:
            self.draw_achievements()

        pygame.display.flip()

    def draw_game(self):
        # Draw Entities
        self.player.draw(self.screen)
        
        for enemy in self.enemies:
            enemy.draw(self.screen)
            
        for pb in self.player_bullets:
            pygame.draw.circle(self.screen, pb['color'], (int(pb['x']), int(pb['y'])), pb['size'])
            
        for eb in self.enemy_bullets:
            pygame.draw.circle(self.screen, eb['color'], (int(eb['x']), int(eb['y'])), eb['size'])
            
        for pu in self.powerups:
            pu.draw(self.screen)

        self.particles.draw(self.screen)

        # Draw HUD
        self.draw_hud()

    def draw_hud(self):
        # Score
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        # Wave
        wave_text = self.font.render(f"Wave: {self.wave}", True, WHITE)
        self.screen.blit(wave_text, (10, 40))

        # Level
        level_text = self.font.render(f"Level: {self.level_id}", True, WHITE)
        self.screen.blit(level_text, (10, 70))

        # HP
        hp_bar_width = 200
        hp_bar_height = 20
        pygame.draw.rect(self.screen, RED, (SCREEN_WIDTH - hp_bar_width - 20, 10, hp_bar_width, hp_bar_height))
        hp_ratio = max(0, self.player.hp / self.player.max_hp)
        pygame.draw.rect(self.screen, GREEN, (SCREEN_WIDTH - hp_bar_width - 20, 10, hp_bar_width * hp_ratio, hp_bar_height))
        hp_text = self.font.render(f"HP: {int(self.player.hp)}", True, WHITE)
        self.screen.blit(hp_text, (SCREEN_WIDTH - hp_bar_width - 20, 15))

        # Shield
        if self.player.shield > 0:
            shield_text = self.font.render(f"Shield: {int(self.player.shield)}", True, CYAN)
            self.screen.blit(shield_text, (SCREEN_WIDTH - hp_bar_width - 20, 40))

        # XP Bar
        xp_bar_width = 200
        xp_bar_height = 10
        pygame.draw.rect(self.screen, GRAY, (SCREEN_WIDTH - xp_bar_width - 20, 60, xp_bar_width, xp_bar_height))
        xp_ratio = self.player.xp / self.player.xp_to_next
        pygame.draw.rect(self.screen, BLUE, (SCREEN_WIDTH - xp_bar_width - 20, 60, xp_bar_width * xp_ratio, xp_bar_height))
        xp_text = self.font.render(f"Lvl: {self.player.level}", True, WHITE)
        self.screen.blit(xp_text, (SCREEN_WIDTH - xp_bar_width - 20, 75))

        # Weapon Name
        weapon_name = self.player.current_weapon.value.upper()
        weapon_text = self.font.render(f"Weapon: {weapon_name}", True, WHITE)
        self.screen.blit(weapon_text, (SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 30))

    def draw_menu(self):
        self.screen.fill(BLACK)
        title = self.big_font.render("SPACE SHOOTER", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        
        start_text = self.font.render("Press ENTER to Start", True, GREEN)
        self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, 300))
        
        achievements_text = self.font.render("Press A for Achievements", True, CYAN)
        self.screen.blit(achievements_text, (SCREEN_WIDTH // 2 - achievements_text.get_width() // 2, 350))
        
        high_score_text = self.font.render(f"High Score: {self.high_score}", True, YELLOW)
        self.screen.blit(high_score_text, (SCREEN_WIDTH // 2 - high_score_text.get_width() // 2, 450))

    def draw_overlay(self, text):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        t = self.big_font.render(text, True, WHITE)
        self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, SCREEN_HEIGHT // 2 - t.get_height() // 2))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        go_text = self.big_font.render("GAME OVER", True, RED)
        self.screen.blit(go_text, (SCREEN_WIDTH // 2 - go_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        
        score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2))
        
        restart_text = self.font.render("Press R to Restart", True, GREEN)
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
        
        menu_text = self.font.render("Press ESC for Menu", True, YELLOW)
        self.screen.blit(menu_text, (SCREEN_WIDTH // 2 - menu_text.get_width() // 2, SCREEN_HEIGHT // 2 + 90))

    def draw_achievements(self):
        self.screen.fill(BLACK)
        title = self.big_font.render("ACHIEVEMENTS", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        
        y = 100
        for aid, ach in self.achievement_manager.achievements.items():
            color = YELLOW if ach.unlocked else GRAY
            name_text = self.font.render(f"{ach.name}: {'Unlocked' if ach.unlocked else 'Locked'}", True, color)
            desc_text = self.font.render(f"  {ach.description}", True, WHITE)
            self.screen.blit(name_text, (100, y))
            self.screen.blit(desc_text, (100, y + 25))
            y += 60
            
        back_text = self.font.render("Press ESC to Back", True, WHITE)
        self.screen.blit(back_text, (SCREEN_WIDTH // 2 - back_text.get_width() // 2, SCREEN_HEIGHT - 50))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                # Save game state on quit
                self.save_system.save(self.score, self.achievement_manager.get_all(), self.player.level, self.player.xp, self.wave, self.level_id)
                pygame.quit()
                sys.exit()
            
            elif event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_RETURN:
                        self.start_game()
                    elif event.key == pygame.K_a:
                        self.state = GameState.ACHIEVEMENTS
                
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                
                elif self.state == GameState.PAUSED:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PLAYING
                    elif event.key == pygame.K_r:
                        self.reset_game()
                        self.state = GameState.PLAYING
                
                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.reset_game()
                        self.state = GameState.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU
                
                elif self.state == GameState.ACHIEVEMENTS:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU

            elif event.type == pygame.USEREVENT:
                # Handle powerup timers
                if self.state == GameState.PLAYING:
                    # Reset speed
                    if hasattr(self, 'speed_timer'):
                        self.player.speed = 5
                    # Reset weapon fire rate
                    if hasattr(self, 'weapon_timer'):
                        self.player.weapons[self.player.current_weapon].fire_rate /= 2
                    # Unfreeze enemies
                    for enemy in self.enemies:
                        enemy.speed = 1 if enemy.e_type == EnemyType.BOSS else (2 if enemy.e_type == EnemyType.FAST else (1 if enemy.e_type == EnemyType.TANK else 1.5))

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            
            if self.state == GameState.PLAYING:
                self.spawn_enemy()
                self.update(dt)
            
            self.draw()
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
