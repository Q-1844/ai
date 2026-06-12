import pygame
import sys
import math
import random
import json
import os
from enum import Enum
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Any

# 初始化 Pygame
pygame.init()
pygame.mixer.init()

# ==================== 常量定义 ====================
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_BLUE = (173, 216, 230)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

# 游戏状态枚举
class GameState(Enum):
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    VICTORY = 5
    SHOP = 6

# 武器类型枚举
class WeaponType(Enum):
    BLASTER = 1
    RAILGUN = 2
    SPREAD_SHOT = 3
    MISSILE = 4
    LASER = 5
    PLASMA = 6

# 敌人类型枚举
class EnemyType(Enum):
    DRONE = 1
    FIGHTER = 2
    TANK = 3
    SPEEDER = 4
    BOSS = 5

# 道具类型枚举
class ItemType(Enum):
    SHIELD = 1
    SPEED_BOOST = 2
    BOMB = 3
    HEALTH_PACK = 4
    WEAPON_UPGRADE = 5
    SHIELD_RECHARGE = 6
    MAGNET = 7
    FREEZE = 8

# 场景类型枚举
class SceneType(Enum):
    SPACE_DEEP = 1
    ASTEROID_FIELD = 2
    NEBULA = 3

# ==================== 音效管理器 ====================
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.volume = 0.5
        
    def load_sound(self, name, frequency=440, duration=0.1, wave_type='sine'):
        """生成简单的合成音效"""
        try:
            # 创建音频缓冲区
            samples = []
            for i in range(int(44100 * duration)):
                t = i / 44100.0
                if wave_type == 'sine':
                    val = math.sin(2 * math.pi * frequency * t)
                elif wave_type == 'square':
                    val = 1 if math.sin(2 * math.pi * frequency * t) > 0 else -1
                elif wave_type == 'noise':
                    val = random.uniform(-1, 1)
                else:
                    val = 0
                samples.append(int(val * 32767))
            
            sound_array = pygame.sndarray.make_sound(pygame.sndarray.array(samples).reshape(-1, 1))
            sound_array.set_volume(self.volume)
            self.sounds[name] = sound_array
        except Exception as e:
            print(f"Error loading sound {name}: {e}")

    def play(self, name):
        if name in self.sounds:
            try:
                self.sounds[name].play()
            except:
                pass

    def set_volume(self, vol):
        self.volume = max(0.0, min(1.0, vol))
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    def init_sounds(self):
        self.load_sound('shoot', 800, 0.1, 'square')
        self.load_sound('hit', 200, 0.15, 'noise')
        self.load_sound('explosion', 100, 0.5, 'noise')
        self.load_sound('powerup', 600, 0.3, 'sine')
        self.load_sound('boss_enter', 50, 1.0, 'square')
        self.load_sound('level_up', 1000, 0.4, 'sine')
        self.load_sound('game_over', 100, 1.5, 'sine')

# ==================== 粒子系统 ====================
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=2):
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
        self.vx *= 0.95
        self.vy *= 0.95

    def draw(self, screen):
        alpha = int((self.life / self.max_life) * 255)
        # 简化绘制，实际项目中可用 Surface 处理 alpha
        s = max(1, int(self.size * (self.life / self.max_life)))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), s)

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, count, color, speed_range=(1, 3), life_range=(20, 40), size_range=(1, 3)):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.randint(*life_range)
            size = random.uniform(*size_range)
            self.particles.append(Particle(x, y, vx, vy, color, life, size))

    def update(self):
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# ==================== 基础实体类 ====================
class Entity:
    def __init__(self, x, y, width, height, speed):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.health = 100
        self.max_health = 100
        self.dead = False
        self.rect = pygame.Rect(x, y, width, height)

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.dead = True

    def update_rect(self):
        self.rect.x = self.x
        self.rect.y = self.y

    def check_collision(self, other):
        return self.rect.colliderect(other.rect)

class Projectile(Entity):
    def __init__(self, x, y, vx, vy, damage, color, weapon_type, is_enemy=False):
        super().__init__(x, y, 6, 6, 0)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.color = color
        self.weapon_type = weapon_type
        self.is_enemy = is_enemy
        self.trail = []

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.update_rect()
        
        # 添加尾迹
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)

        # 边界检查
        if (self.x < -10 or self.x > SCREEN_WIDTH + 10 or 
            self.y < -10 or self.y > SCREEN_HEIGHT + 10):
            self.dead = True

    def draw(self, screen):
        # 绘制尾迹
        for i, pos in enumerate(self.trail):
            alpha = i / len(self.trail)
            s = max(1, int(4 * alpha))
            c = tuple(int(c * alpha) for c in self.color)
            pygame.draw.circle(screen, c, (int(pos[0]), int(pos[1])), s)
        
        # 绘制本体
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 4)

class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 30, 30, 5)
        self.weapon_level = 1
        self.current_weapon = WeaponType.BLASTER
        self.shield = 0
        self.max_shield = 100
        self.exp = 0
        self.level = 1
        self.skills = {
            'damage': 0,
            'speed': 0,
            'health': 0,
            'shield_regen': 0
        }
        self.fire_rate = 0.2
        self.last_shot_time = 0
        self.invincible = False
        self.invincible_timer = 0

    def update(self, keys, mouse_pos, dt, sound_manager):
        dx, dy = 0, 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1

        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length
        
        speed = self.speed + (self.skills['speed'] * 1.5)
        self.x += dx * speed * dt * 60
        self.y += dy * speed * dt * 60

        # 边界限制
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
        self.y = max(0, min(SCREEN_HEIGHT - self.height, self.y))
        self.update_rect()

        # 无敌时间更新
        if self.invincible:
            self.invincible_timer -= dt
            if self.invincible_timer <= 0:
                self.invincible = False

        # 护盾恢复
        if self.skills['shield_regen'] > 0 and self.shield < self.max_shield:
            self.shield = min(self.max_shield, self.shield + self.skills['shield_regen'] * dt)

    def shoot(self, current_time, projectiles, sound_manager):
        if current_time - self.last_shot_time >= self.fire_rate:
            self.last_shot_time = current_time
            cx = self.x + self.width // 2
            cy = self.y
            
            # 根据武器类型生成子弹
            if self.current_weapon == WeaponType.BLASTER:
                projectiles.append(Projectile(cx, cy, 0, -15, 10 + self.skills['damage'], YELLOW, self.current_weapon))
                sound_manager.play('shoot')
            
            elif self.current_weapon == WeaponType.SPREAD_SHOT:
                for angle in [-0.2, 0, 0.2]:
                    vx = math.sin(angle) * 12
                    vy = -math.cos(angle) * 12
                    projectiles.append(Projectile(cx, cy, vx, vy, 8 + self.skills['damage'], CYAN, self.current_weapon))
                sound_manager.play('shoot')

            elif self.current_weapon == WeaponType.RAILGUN:
                # 激光束效果，这里用高速细子弹模拟
                projectiles.append(Projectile(cx, cy, 0, -25, 25 + self.skills['damage'] * 2, RED, self.current_weapon))
                sound_manager.play('shoot')

            elif self.current_weapon == WeaponType.MISSILE:
                # 追踪导弹逻辑稍后处理，这里先发射慢速高伤
                projectiles.append(Projectile(cx, cy, 0, -8, 30 + self.skills['damage'], ORANGE, self.current_weapon))
                sound_manager.play('shoot')

            elif self.current_weapon == WeaponType.LASER:
                # 持续伤害模拟，发射一串快速子弹
                for i in range(3):
                    projectiles.append(Projectile(cx, cy, 0, -20, 5 + self.skills['damage'], MAGENTA, self.current_weapon))
                sound_manager.play('shoot')

            elif self.current_weapon == WeaponType.PLASMA:
                projectiles.append(Projectile(cx, cy, 0, -10, 40 + self.skills['damage'], PURPLE, self.current_weapon))
                sound_manager.play('shoot')

    def gain_exp(self, amount):
        self.exp += amount
        threshold = self.level * 100
        if self.exp >= threshold:
            self.exp -= threshold
            self.level += 1
            return True
        return False

    def apply_skill(self, skill_name):
        if skill_name in self.skills:
            self.skills[skill_name] += 1

# ==================== 敌人系统 ====================
class Enemy(Entity):
    def __init__(self, x, y, enemy_type, level_scaling=1.0):
        self.enemy_type = enemy_type
        self.move_pattern = 'straight'
        self.timer = 0
        self.angle = 0
        
        # 根据类型设置初始属性
        if enemy_type == EnemyType.DRONE:
            super().__init__(x, y, 20, 20, 3)
            self.health = 20 * level_scaling
            self.max_health = self.health
            self.color = GREEN
            self.score_value = 10
        elif enemy_type == EnemyType.FIGHTER:
            super().__init__(x, y, 25, 25, 4)
            self.health = 40 * level_scaling
            self.max_health = self.health
            self.color = BLUE
            self.score_value = 20
            self.move_pattern = 'zigzag'
        elif enemy_type == EnemyType.TANK:
            super().__init__(x, y, 40, 40, 1.5)
            self.health = 100 * level_scaling
            self.max_health = self.health
            self.color = GRAY
            self.score_value = 50
        elif enemy_type == EnemyType.SPEEDER:
            super().__init__(x, y, 15, 15, 8)
            self.health = 15 * level_scaling
            self.max_health = self.health
            self.color = YELLOW
            self.score_value = 15
            self.move_pattern = 'chase'
        elif enemy_type == EnemyType.BOSS:
            super().__init__(x, y, 80, 80, 1)
            self.health = 500 * level_scaling
            self.max_health = self.health
            self.color = RED
            self.score_value = 500
            self.phase = 1
            self.move_pattern = 'boss'

        self.update_rect()

    def update(self, player, dt):
        self.timer += dt
        self.angle += dt
        
        if self.enemy_type == EnemyType.DRONE:
            self.y += self.speed * dt * 60
        elif self.enemy_type == EnemyType.FIGHTER:
            self.y += self.speed * dt * 60
            self.x += math.sin(self.timer * 2) * 2
        elif self.enemy_type == EnemyType.TANK:
            self.y += self.speed * dt * 60
        elif self.enemy_type == EnemyType.SPEEDER:
            if player:
                dx = (player.x + player.width//2) - (self.x + self.width//2)
                dy = (player.y + player.height//2) - (self.y + self.height//2)
                dist = math.hypot(dx, dy)
                if dist > 0:
                    self.x += (dx / dist) * self.speed * dt * 60
                    self.y += (dy / dist) * self.speed * dt * 60
        elif self.enemy_type == EnemyType.BOSS:
            # Boss 移动逻辑
            if self.phase == 1:
                self.x += math.sin(self.timer) * 2
                self.y += 0.5 * dt * 60
                if self.y > 100:
                    self.phase = 2
            elif self.phase == 2:
                self.x += math.cos(self.timer * 2) * 3
                self.y = 150 + math.sin(self.timer) * 50

        self.update_rect()

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # 绘制血条
        bar_width = self.width
        bar_height = 4
        health_pct = self.health / self.max_health
        pygame.draw.rect(screen, BLACK, (self.rect.x, self.rect.y - 10, bar_width, bar_height))
        pygame.draw.rect(screen, RED, (self.rect.x, self.rect.y - 10, bar_width * health_pct, bar_height))

class Boss(Enemy):
    def __init__(self, x, y, level_scaling):
        super().__init__(x, y, EnemyType.BOSS, level_scaling)
        self.attack_timer = 0
        self.projectiles = []

    def update(self, player, dt, all_projectiles):
        super().update(player, dt)
        self.attack_timer += dt
        
        # Boss 攻击逻辑
        if self.phase == 1:
            if self.attack_timer > 1.0:
                self.attack_timer = 0
                # 扇形弹幕
                for i in range(-2, 3):
                    angle = math.pi / 2 + i * 0.3
                    vx = math.cos(angle) * 5
                    vy = math.sin(angle) * 5
                    proj = Projectile(self.x + 40, self.y + 40, vx, vy, 10, ORANGE, None, is_enemy=True)
                    all_projectiles.append(proj)
        elif self.phase == 2:
            if self.attack_timer > 0.5:
                self.attack_timer = 0
                # 环绕弹幕
                for i in range(8):
                    angle = (i / 8) * math.pi * 2 + self.timer
                    vx = math.cos(angle) * 4
                    vy = math.sin(angle) * 4
                    proj = Projectile(self.x + 40, self.y + 40, vx, vy, 15, RED, None, is_enemy=True)
                    all_projectiles.append(proj)

# ==================== 道具系统 ====================
class Item(Entity):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20, 20, 0)
        self.item_type = item_type
        self.vy = 2
        self.color = WHITE
        
        if item_type == ItemType.SHIELD:
            self.color = CYAN
        elif item_type == ItemType.HEALTH_PACK:
            self.color = GREEN
        elif item_type == ItemType.BOMB:
            self.color = ORANGE
        elif item_type == ItemType.WEAPON_UPGRADE:
            self.color = MAGENTA
        elif item_type == ItemType.SPEED_BOOST:
            self.color = YELLOW
        elif item_type == ItemType.SHIELD_RECHARGE:
            self.color = LIGHT_BLUE
        elif item_type == ItemType.MAGNET:
            self.color = PURPLE
        elif item_type == ItemType.FREEZE:
            self.color = WHITE

    def update(self):
        self.y += self.vy
        self.update_rect()
        if self.y > SCREEN_HEIGHT:
            self.dead = True

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x + 10), int(self.y + 10)), 10)
        pygame.draw.circle(screen, BLACK, (int(self.x + 10), int(self.y + 10)), 10, 2)

# ==================== 成就系统 ====================
class AchievementManager:
    def __init__(self):
        self.unlocked = set()
        self.achievements = {
            'first_kill': {'name': 'First Blood', 'desc': 'Kill your first enemy'},
            'wave_5': {'name': 'Survivor', 'desc': 'Reach Wave 5'},
            'boss_slayer': {'name': 'Boss Slayer', 'desc': 'Defeat a Boss'},
            'level_5': {'name': 'Veteran', 'desc': 'Reach Level 5'},
            'full_weapons': {'name': 'Arsenal', 'desc': 'Unlock all weapons'},
            'no_damage': {'name': 'Untouchable', 'desc': 'Complete a wave without taking damage'},
            'combo_10': {'name': 'Combo Master', 'desc': 'Kill 10 enemies in quick succession'},
            'item_collector': {'name': 'Collector', 'desc': 'Collect 50 items'},
            'speed_demon': {'name': 'Speed Demon', 'desc': 'Move at max speed for 10 seconds'},
            'rich': {'name': 'Millionaire', 'desc': 'Earn 1,000,000 points'}
        }
        self.stats = defaultdict(int)

    def unlock(self, key):
        if key not in self.unlocked:
            self.unlocked.add(key)
            # 可以在这里播放音效或显示通知
            return True
        return False

    def check_stat(self, stat_name, value):
        self.stats[stat_name] += value

    def has_achievement(self, key):
        return key in self.unlocked

# ==================== 存档系统 ====================
class SaveSystem:
    @staticmethod
    def save_game(filename, player, wave, score):
        data = {
            'player': {
                'x': player.x,
                'y': player.y,
                'level': player.level,
                'exp': player.exp,
                'skills': player.skills,
                'current_weapon': player.current_weapon.value,
                'max_shield': player.max_shield,
                'shield': player.shield
            },
            'wave': wave,
            'score': score,
            'timestamp': time.time()
        }
        with open(filename, 'w') as f:
            json.dump(data, f)

    @staticmethod
    def load_game(filename, player):
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            player.x = data['player']['x']
            player.y = data['player']['y']
            player.level = data['player']['level']
            player.exp = data['player']['exp']
            player.skills = data['player']['skills']
            player.current_weapon = WeaponType(data['player']['current_weapon'])
            player.max_shield = data['player']['max_shield']
            player.shield = data['player']['shield']
            return True
        except Exception as e:
            print(f"Failed to load save: {e}")
            return False

# ==================== 主游戏类 ====================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter Ultimate")
        self.clock = pygame.time.Clock()
        
        self.sound_manager = SoundManager()
        self.sound_manager.init_sounds()
        
        self.particle_system = ParticleSystem()
        self.achievement_mgr = AchievementManager()
        
        self.reset_game()
        
        # 字体
        self.font_large = pygame.font.SysFont('arial', 48)
        self.font_medium = pygame.font.SysFont('arial', 24)
        self.font_small = pygame.font.SysFont('arial', 18)

    def reset_game(self):
        self.state = GameState.MENU
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.enemies = []
        self.projectiles = []
        self.items = []
        self.wave = 1
        self.score = 0
        self.wave_timer = 0
        self.enemy_spawn_timer = 0
        self.scene = SceneType.SPACE_DEEP
        self.boss_defeated = False
        self.difficulty_mult = 1.0

    def start_new_game(self):
        self.reset_game()
        self.state = GameState.PLAYING
        self.sound_manager.play('level_up')

    def load_saved_game(self):
        if SaveSystem.load_game('save.json', self.player):
            self.state = GameState.PLAYING
            self.sound_manager.play('level_up')
        else:
            self.start_new_game()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if self.state == GameState.MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.start_new_game()
                    elif event.key == pygame.K_l:
                        self.load_saved_game()
            
            elif self.state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                    elif event.key == pygame.K_SPACE:
                        pass # Handled in update loop for continuous fire or single shot
                    elif event.key == pygame.K_b:
                        self.use_bomb()
                    elif event.key == pygame.K_1: self.player.current_weapon = WeaponType.BLASTER
                    elif event.key == pygame.K_2: self.player.current_weapon = WeaponType.SPREAD_SHOT
                    elif event.key == pygame.K_3: self.player.current_weapon = WeaponType.RAILGUN
                    elif event.key == pygame.K_4: self.player.current_weapon = WeaponType.MISSILE
                    elif event.key == pygame.K_5: self.player.current_weapon = WeaponType.LASER
                    elif event.key == pygame.K_6: self.player.current_weapon = WeaponType.PLASMA
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # Left click
                        pass # Mouse controls direction handled in player movement logic if needed, currently WASD

            elif self.state == GameState.PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PLAYING
                    elif event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()

            elif self.state == GameState.GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.start_new_game()
                    elif event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()

    def use_bomb(self):
        """全屏炸弹"""
        self.sound_manager.play('explosion')
        self.particle_system.emit(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 100, YELLOW, speed_range=(5, 15), life_range=(60, 120))
        
        # 消灭所有非Boss敌人，伤害Boss
        for enemy in self.enemies:
            if enemy.enemy_type == EnemyType.BOSS:
                enemy.take_damage(50)
            else:
                enemy.dead = True
                self.score += enemy.score_value
        
        # 清除所有敌方子弹
        self.projectiles = [p for p in self.projectiles if not p.is_enemy]
        
        self.achievement_mgr.check_stat('bomb_used', 1)

    def spawn_enemies(self, dt):
        self.enemy_spawn_timer += dt
        spawn_rate = max(0.1, 1.0 - (self.wave * 0.05))
        
        if self.enemy_spawn_timer > spawn_rate:
            self.enemy_spawn_timer = 0
            
            # 每5波出现Boss
            if self.wave % 5 == 0 and not self.boss_defeated:
                if not any(isinstance(e, Boss) for e in self.enemies):
                    boss = Boss(SCREEN_WIDTH // 2, -100, self.difficulty_mult)
                    self.enemies.append(boss)
                    self.sound_manager.play('boss_enter')
                    return
            else:
                # 普通敌人
                x = random.randint(0, SCREEN_WIDTH - 30)
                y = -30
                
                # 根据波次选择敌人类型
                r = random.random()
                if r < 0.5:
                    etype = EnemyType.DRONE
                elif r < 0.7:
                    etype = EnemyType.FIGHTER
                elif r < 0.85:
                    etype = EnemyType.TANK
                else:
                    etype = EnemyType.SPEEDER
                
                self.enemies.append(Enemy(x, y, etype, self.difficulty_mult))

    def update(self, dt):
        if self.state != GameState.PLAYING:
            return

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        current_time = pygame.time.get_ticks() / 1000.0

        # 更新玩家
        self.player.update(keys, mouse_pos, dt, self.sound_manager)
        self.player.shoot(current_time, self.projectiles, self.sound_manager)

        # 生成敌人
        self.spawn_enemies(dt)

        # 更新敌人
        for enemy in self.enemies:
            enemy.update(self.player, dt)
            if enemy.dead:
                # 爆炸效果
                self.particle_system.emit(enemy.x + enemy.width//2, enemy.y + enemy.height//2, 20, enemy.color, speed_range=(2, 5), life_range=(30, 60))
                self.sound_manager.play('explosion')
                
                # 掉落道具
                if random.random() < 0.15:
                    item_type = random.choice(list(ItemType))
                    self.items.append(Item(enemy.x, enemy.y, item_type))
                
                # 经验值
                exp_gain = enemy.score_value // 5
                if self.player.gain_exp(exp_gain):
                    self.sound_manager.play('level_up')
                    # 简单的升级提示，实际应进入技能树界面
                    self.player.apply_skill('damage') # 默认升级加伤害
                
                self.score += enemy.score_value
                self.achievement_mgr.check_stat('kills', 1)
                
                if enemy.enemy_type == EnemyType.BOSS:
                    self.boss_defeated = True
                    self.achievement_mgr.unlock('boss_slayer')
                    self.wave += 1
                    self.difficulty_mult += 0.5
                    self.sound_manager.play('level_up')
                else:
                    self.achievement_mgr.check_stat('points', enemy.score_value)

        # 更新子弹
        for proj in self.projectiles:
            proj.update()
            # 碰撞检测：子弹 vs 敌人
            if not proj.is_enemy:
                for enemy in self.enemies:
                    if not enemy.dead and proj.check_collision(enemy):
                        enemy.take_damage(proj.damage)
                        proj.dead = True
                        self.particle_system.emit(proj.x, proj.y, 5, proj.color, speed_range=(1, 3), life_range=(10, 20))
                        self.sound_manager.play('hit')
                        break
            
            # 碰撞检测：敌方子弹 vs 玩家
            elif proj.is_enemy:
                if not self.player.invincible and proj.check_collision(self.player):
                    self.player.take_damage(proj.damage)
                    proj.dead = True
                    self.player.invincible = True
                    self.player.invincible_timer = 1.0
                    self.particle_system.emit(self.player.x, self.player.y, 10, RED, speed_range=(2, 4), life_range=(20, 40))
                    self.sound_manager.play('hit')
                    
                    if self.player.health <= 0:
                        self.state = GameState.GAME_OVER
                        self.sound_manager.play('game_over')

        # 更新道具
        for item in self.items:
            item.update()
            if self.player.check_collision(item):
                item.dead = True
                self.apply_item(item.item_type)
                self.sound_manager.play('powerup')
                self.achievement_mgr.check_stat('items_collected', 1)

        # 清理死亡实体
        self.enemies = [e for e in self.enemies if not e.dead]
        self.projectiles = [p for p in self.projectiles if not p.dead]
        self.items = [i for i in self.items if not i.dead]

        # 粒子更新
        self.particle_system.update()

        # 检查波次完成（如果没有敌人且没有正在生成的）
        if not self.enemies and not any(p.is_enemy for p in self.projectiles):
             # 简单逻辑：如果玩家活着且没有敌人，增加波次
             # 实际游戏中应有明确的波次计数器和过渡阶段
             pass

        # 自动保存
        if int(current_time) % 60 == 0: # 每分钟保存一次
             SaveSystem.save_game('save.json', self.player, self.wave, self.score)

    def apply_item(self, item_type):
        if item_type == ItemType.SHIELD:
            self.player.shield = min(self.player.max_shield, self.player.shield + 50)
        elif item_type == ItemType.HEALTH_PACK:
            self.player.health = min(self.player.max_health, self.player.health + 30)
        elif item_type == ItemType.BOMB:
            self.use_bomb()
        elif item_type == ItemType.WEAPON_UPGRADE:
            self.player.weapon_level += 1
            self.player.fire_rate = max(0.05, self.player.fire_rate - 0.02)
        elif item_type == ItemType.SPEED_BOOST:
            self.player.speed += 1
        elif item_type == ItemType.SHIELD_RECHARGE:
            self.player.skills['shield_regen'] += 1
        elif item_type == ItemType.MAGNET:
            # 暂时只改变道具吸引逻辑，这里简化为直接获取
            pass
        elif item_type == ItemType.FREEZE:
            # 冻结所有敌人几秒
            for e in self.enemies:
                e.y -= 50 # 向上推一点，模拟冻结效果
            self.sound_manager.play('powerup')

    def draw_background(self):
        if self.scene == SceneType.SPACE_DEEP:
            self.screen.fill(BLACK)
            # 绘制星星
            for _ in range(100):
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(0, SCREEN_HEIGHT)
                pygame.draw.circle(self.screen, WHITE, (x, y), 1)
        elif self.scene == SceneType.ASTEROID_FIELD:
            self.screen.fill(DARK_GRAY)
        elif self.scene == SceneType.NEBULA:
            self.screen.fill((20, 0, 30))

    def draw_hud(self):
        # 分数
        text = self.font_medium.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(text, (10, 10))
        
        # 波次
        text = self.font_medium.render(f"Wave: {self.wave}", True, WHITE)
        self.screen.blit(text, (10, 40))
        
        # 等级
        text = self.font_medium.render(f"Lvl: {self.player.level}", True, CYAN)
        self.screen.blit(text, (10, 70))

        # 玩家血条
        bar_width = 200
        bar_height = 20
        health_pct = self.player.health / self.player.max_health
        pygame.draw.rect(self.screen, RED, (10, SCREEN_HEIGHT - 50, bar_width, bar_height))
        pygame.draw.rect(self.screen, GREEN, (10, SCREEN_HEIGHT - 50, bar_width * health_pct, bar_height))
        
        # 护盾条
        shield_pct = self.player.shield / self.player.max_shield
        pygame.draw.rect(self.screen, BLUE, (10, SCREEN_HEIGHT - 30, bar_width, 10))
        pygame.draw.rect(self.screen, LIGHT_BLUE, (10, SCREEN_HEIGHT - 30, bar_width * shield_pct, 10))

        # 武器指示
        text = self.font_small.render(f"Weapon: {self.player.current_weapon.name}", True, YELLOW)
        self.screen.blit(text, (10, SCREEN_HEIGHT - 100))

    def draw_menu(self):
        self.screen.fill(BLACK)
        title = self.font_large.render("SPACE SHOOTER", True, WHITE)
        rect = title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
        self.screen.blit(title, rect)

        start = self.font_medium.render("Press ENTER to Start", True, GREEN)
        rect = start.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(start, rect)

        load = self.font_medium.render("Press L to Load Game", True, CYAN)
        rect = load.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(load, rect)

    def draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        text = self.font_large.render("PAUSED", True, WHITE)
        rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(text, rect)

        resume = self.font_medium.render("Press ESC to Resume", True, YELLOW)
        rect = resume.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(resume, rect)

    def draw_game_over(self):
        self.screen.fill(BLACK)
        text = self.font_large.render("GAME OVER", True, RED)
        rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
        self.screen.blit(text, rect)

        score_text = self.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        rect = score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(score_text, rect)

        restart = self.font_medium.render("Press R to Restart", True, GREEN)
        rect = restart.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(restart, rect)

    def run(self):
        last_time = pygame.time.get_ticks()
        
        while True:
            current_time = pygame.time.get_ticks()
            dt = (current_time - last_time) / 1000.0
            last_time = current_time

            self.handle_events()

            self.update(dt)

            # 绘制
            self.screen.fill(BLACK) # Clear
            
            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.PLAYING:
                self.draw_background()
                
                # 绘制粒子
                self.particle_system.draw(self.screen)
                
                # 绘制道具
                for item in self.items:
                    item.draw(self.screen)
                
                # 绘制敌人
                for enemy in self.enemies:
                    enemy.draw(self.screen)
                
                # 绘制子弹
                for proj in self.projectiles:
                    proj.draw(self.screen)
                
                # 绘制玩家
                if self.state == GameState.PLAYING:
                    color = self.player.color if hasattr(self.player, 'color') else WHITE
                    if self.player.invincible and int(current_time / 100) % 2 == 0:
                        color = GRAY # 闪烁效果
                    pygame.draw.rect(self.screen, color, self.player.rect)
                
                self.draw_hud()
                
                if self.state == GameState.PAUSED:
                    self.draw_pause()

            elif self.state == GameState.GAME_OVER:
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
