import pygame
import sys
import math
import random
import json
import os
import copy
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

# 初始化 Pygame
pygame.init()
pygame.mixer.init()

# ================= 常量定义 =================
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
DARK_GRAY = (50, 50, 50)
GOLD = (255, 215, 0)

# 游戏状态枚举
class GameState(Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3
    SHOP = 4
    ACHIEVEMENTS = 5

# 武器类型枚举
class WeaponType(Enum):
    BLASTER = 0
    LASER = 1
    SPREAD = 2
    MISSILE = 3
    PLASMA = 4
    RAILGUN = 5

# 敌人类型枚举
class EnemyType(Enum):
    DRONE = 0
    FIGHTER = 1
    TANK = 2
    SPEEDER = 3
    BOSS = 4

# 关卡场景枚举
class SceneType(Enum):
    SPACE = 0
    ASTEROID_FIELD = 1
    NEBULA = 2

# ================= 音效管理器 =================
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.music_volume = 0.5
        self.sfx_volume = 0.7
        self.enabled = True
        
        # 尝试加载资源，如果失败则使用合成音效
        try:
            self.load_sounds()
        except Exception as e:
            print(f"Warning: Could not load sound files. Using generated sounds if possible or silent.")
            self.enabled = False

    def load_sounds(self):
        sound_files = {
            'shoot': 'shoot.wav',
            'explosion': 'explosion.wav',
            'hit': 'hit.wav',
            'powerup': 'powerup.wav',
            'level_up': 'level_up.wav',
            'menu_select': 'click.wav',
            'boss_spawn': 'boss_spawn.wav'
        }
        for name, filename in sound_files.items():
            try:
                if os.path.exists(filename):
                    self.sounds[name] = pygame.mixer.Sound(filename)
                    self.sounds[name].set_volume(self.sfx_volume)
                else:
                    # 如果文件不存在，创建一个空的 Sound 对象或留空
                    # 为了演示，这里我们尝试生成简单的 beep，但 pygame mixer 生成 beep 较复杂
                    # 所以我们留空，并在 play 中检查
                    self.sounds[name] = None
            except Exception:
                self.sounds[name] = None

    def play(self, sound_name):
        if not self.enabled:
            return
        if sound_name in self.sounds and self.sounds[sound_name]:
            try:
                self.sounds[sound_name].play()
            except:
                pass

    def set_music_volume(self, vol):
        self.music_volume = vol

    def set_sfx_volume(self, vol):
        self.sfx_volume = vol
        for s in self.sounds.values():
            if s:
                s.set_volume(self.sfx_volume)

# ================= 粒子系统 =================
class Particle:
    def __init__(self, x, y, color, speed, life, size=2):
        self.x = x
        self.y = y
        self.color = color
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = speed
        self.life = life
        self.max_life = life
        self.size = size
        self.vx = math.cos(self.angle) * speed
        self.vy = math.sin(self.angle) * speed

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size *= 0.95

    def draw(self, screen):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        # 简单的圆形粒子
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), max(1, int(self.size)))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=10, speed=2, life=30, size=3):
        for _ in range(count):
            self.particles.append(Particle(x, y, color, random.uniform(0.5, speed), life, random.uniform(1, size)))

    def update(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# ================= 道具系统 =================
class PowerUp:
    def __init__(self, x, y, power_type):
        self.x = x
        self.y = y
        self.power_type = power_type
        self.width = 20
        self.height = 20
        self.speed = 2
        self.active = True

    def update(self):
        self.y += self.speed

    def draw(self, screen):
        if not self.active:
            return
        color = WHITE
        if self.power_type == 'SHIELD':
            color = BLUE
        elif self.power_type == 'SPEED':
            color = GREEN
        elif self.power_type == 'BOMB':
            color = RED
        elif self.power_type == 'SCORE':
            color = GOLD
        
        pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height), 1)

# ================= 玩家类 =================
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.speed = 5
        self.health = 100
        self.max_health = 100
        self.shield = 0
        self.max_shield = 50
        self.shield_regen_rate = 0.1
        self.exp = 0
        self.level = 1
        self.xp_to_next_level = 100
        
        # 武器系统
        self.weapon_type = WeaponType.BLASTER
        self.weapon_stats = {
            WeaponType.BLASTER: {'damage': 10, 'cooldown': 15, 'speed': 10, 'color': YELLOW, 'count': 1},
            WeaponType.LASER: {'damage': 5, 'cooldown': 5, 'speed': 15, 'color': CYAN, 'count': 1},
            WeaponType.SPREAD: {'damage': 8, 'cooldown': 40, 'speed': 8, 'color': MAGENTA, 'count': 5},
            WeaponType.MISSILE: {'damage': 20, 'cooldown': 60, 'speed': 5, 'color': RED, 'count': 1},
            WeaponType.PLASMA: {'damage': 15, 'cooldown': 25, 'speed': 12, 'color': GREEN, 'count': 1},
            WeaponType.RAILGUN: {'damage': 50, 'cooldown': 120, 'speed': 20, 'color': WHITE, 'count': 1}
        }
        self.cooldown_timer = 0
        self.shoot_key_pressed = False
        
        # 状态
        self.invincible = False
        self.invincible_timer = 0
        self.acceleration = False
        self.accel_timer = 0
        
        # 技能树 (简化版)
        self.skills = {
            'damage_boost': 0,
            'speed_boost': 0,
            'shield_boost': 0
        }

    def update(self, keys, mouse_pos, screen_rect):
        # 移动控制
        move_x = 0
        move_y = 0
        current_speed = self.speed + (self.skills['speed_boost'] * 0.5)
        if self.acceleration:
            current_speed *= 1.5
            
        if keys[pygame.K_w]:
            move_y = -current_speed
        if keys[pygame.K_s]:
            move_y = current_speed
        if keys[pygame.K_a]:
            move_x = -current_speed
        if keys[pygame.K_d]:
            move_x = current_speed
            
        self.x += move_x
        self.y += move_y
        
        # 边界限制
        self.x = max(0, min(screen_rect.width - self.width, self.x))
        self.y = max(0, min(screen_rect.height - self.height, self.y))
        
        # 射击
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        else:
            if keys[pygame.K_SPACE]:
                self.shoot(screen_rect)
                self.cooldown_timer = self.weapon_stats[self.weapon_type]['cooldown']
                
        # 护盾恢复
        if self.shield < self.max_shield:
            self.shield += self.shield_regen_rate + (self.skills['shield_boost'] * 0.05)
            
        # 无敌时间
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False
                
        # 加速时间
        if self.acceleration:
            self.accel_timer -= 1
            if self.accel_timer <= 0:
                self.acceleration = False

    def shoot(self, screen_rect):
        stats = self.weapon_stats[self.weapon_type]
        damage = stats['damage'] + (self.skills['damage_boost'] * 2)
        count = stats['count']
        speed = stats['speed']
        color = stats['color']
        
        # 计算鼠标方向
        mouse_x, mouse_y = pygame.mouse.get_pos()
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        dx = mouse_x - center_x
        dy = mouse_y - center_y
        angle = math.atan2(dy, dx)
        
        projectiles = []
        
        if self.weapon_type == WeaponType.SPREAD:
            for i in range(count):
                offset_angle = angle + (i - (count-1)/2) * 0.2
                vx = math.cos(offset_angle) * speed
                vy = math.sin(offset_angle) * speed
                projectiles.append(Projectile(
                    center_x, center_y, vx, vy, damage, color, self.weapon_type
                ))
        else:
            for _ in range(count):
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                projectiles.append(Projectile(
                    center_x, center_y, vx, vy, damage, color, self.weapon_type
                ))
                
        return projectiles

    def take_damage(self, damage):
        if self.invincible:
            return
        if self.shield > 0:
            if self.shield >= damage:
                self.shield -= damage
                damage = 0
            else:
                damage -= self.shield
                self.shield = 0
        self.health -= damage
        if self.health <= 0:
            self.health = 0

    def gain_xp(self, amount):
        self.exp += amount
        if self.exp >= self.xp_to_next_level:
            self.exp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = int(self.xp_to_next_level * 1.2)
            self.max_health += 10
            self.health = self.max_health
            return True # Level Up
        return False

    def draw(self, screen):
        color = GREEN
        if self.invincible:
            if int(pygame.time.get_ticks() / 100) % 2 == 0:
                color = RED
            else:
                color = GREEN
        
        # 绘制飞船 (三角形)
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        
        # 引擎尾焰
        if random.random() > 0.5:
            py.emit(center_x, self.y + self.height, ORANGE, 2, 10, 2)
            
        pygame.draw.polygon(screen, color, [
            (center_x, self.y),
            (self.x, self.y + self.height),
            (self.x + self.width, self.y + self.height)
        ])
        
        # 护盾视觉效果
        if self.shield > 0:
            pygame.draw.circle(screen, (0, 100, 255), (int(center_x), int(center_y)), 30, 2)

# ================= 投射物类 =================
class Projectile:
    def __init__(self, x, y, vx, vy, damage, color, p_type):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.color = color
        self.p_type = p_type
        self.width = 6
        self.height = 6
        self.active = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.active = False

    def draw(self, screen):
        if not self.active:
            return
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 4)
        # 拖尾效果
        if self.p_type == WeaponType.RAILGUN:
            pygame.draw.line(screen, self.color, (self.x, self.y), (self.x - self.vx*2, self.y - self.vy*2), 2)

# ================= 敌人类 =================
class Enemy:
    def __init__(self, x, y, enemy_type, wave_level):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.wave_level = wave_level
        self.active = True
        self.shoot_timer = 0
        
        # 根据类型设置属性
        if enemy_type == EnemyType.DRONE:
            self.width = 30
            self.height = 30
            self.health = 20 + wave_level * 5
            self.max_health = self.health
            self.speed = 2 + wave_level * 0.1
            self.color = RED
            self.score_value = 10
        elif enemy_type == EnemyType.FIGHTER:
            self.width = 40
            self.height = 40
            self.health = 50 + wave_level * 10
            self.max_health = self.health
            self.speed = 1.5 + wave_level * 0.05
            self.color = ORANGE
            self.score_value = 20
        elif enemy_type == EnemyType.TANK:
            self.width = 60
            self.height = 60
            self.health = 150 + wave_level * 20
            self.max_health = self.health
            self.speed = 0.5 + wave_level * 0.02
            self.color = DARK_GRAY
            self.score_value = 50
        elif enemy_type == EnemyType.SPEEDER:
            self.width = 20
            self.height = 20
            self.health = 10 + wave_level * 2
            self.max_health = self.health
            self.speed = 4 + wave_level * 0.2
            self.color = MAGENTA
            self.score_value = 15
        elif enemy_type == EnemyType.BOSS:
            self.width = 120
            self.height = 80
            self.health = 1000 + wave_level * 500
            self.max_health = self.health
            self.speed = 1
            self.color = PURPLE
            self.score_value = 500
            self.phase = 1
            self.target_y = 100
        else:
            self.width = 30
            self.height = 30
            self.health = 10
            self.max_health = 10
            self.speed = 1
            self.color = WHITE
            self.score_value = 5

    def update(self, player):
        # 行为模式
        if self.enemy_type == EnemyType.DRONE:
            self.y += self.speed
            self.x += math.sin(pygame.time.get_ticks() / 500) * 2
        elif self.enemy_type == EnemyType.FIGHTER:
            self.y += self.speed
            # 尝试向玩家水平移动
            if self.x < player.x:
                self.x += 1
            elif self.x > player.x:
                self.x -= 1
        elif self.enemy_type == EnemyType.TANK:
            self.y += self.speed
        elif self.enemy_type == EnemyType.SPEEDER:
            # 追踪玩家
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed
        elif self.enemy_type == EnemyType.BOSS:
            self.update_boss(player)
            
        # 边界检查
        if self.y > SCREEN_HEIGHT:
            self.active = False
            
        # 射击逻辑
        self.shoot_timer += 1
        shoot_interval = 60 # 默认帧
        if self.enemy_type == EnemyType.BOSS:
            shoot_interval = 30
        elif self.enemy_type == EnemyType.TANK:
            shoot_interval = 90
        elif self.enemy_type == EnemyType.SPEEDER:
            shoot_interval = 120
            
        if self.shoot_timer > shoot_interval:
            self.shoot(player)
            self.shoot_timer = 0

    def update_boss(self, player):
        # Boss 阶段逻辑
        health_pct = self.health / self.max_health
        
        if health_pct > 0.6:
            # 阶段 1: 缓慢下降，左右摆动
            self.y += 0.5
            self.x += math.sin(pygame.time.get_ticks() / 1000) * 3
            if self.y > self.target_y:
                self.y = self.target_y
        elif health_pct > 0.3:
            # 阶段 2: 快速移动，追踪
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.x += (dx / dist) * 2
                self.y += (dy / dist) * 2
        else:
            # 阶段 3: 疯狂弹幕
            self.y += math.sin(pygame.time.get_ticks() / 200) * 2
            self.x += math.cos(pygame.time.get_ticks() / 200) * 2
            
        # 限制在屏幕内
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
        self.y = max(0, min(SCREEN_HEIGHT - self.height, self.y))

    def shoot(self, player):
        projectiles = []
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        
        if self.enemy_type == EnemyType.BOSS:
            # Boss 多种弹幕
            for i in range(8):
                angle = (i / 8) * math.pi * 2 + pygame.time.get_ticks() / 1000
                vx = math.cos(angle) * 4
                vy = math.sin(angle) * 4
                projectiles.append(Projectile(
                    center_x, center_y, vx, vy, 10, RED, WeaponType.BLASTER
                ))
        else:
            # 普通敌人向玩家射击
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                vx = (dx / dist) * 5
                vy = (dy / dist) * 5
                projectiles.append(Projectile(
                    center_x, center_y, vx, vy, 5, RED, WeaponType.BLASTER
                ))
        return projectiles

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.active = False

    def draw(self, screen):
        if not self.active:
            return
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        
        # 血条
        bar_width = self.width
        bar_height = 5
        health_pct = self.health / self.max_health
        pygame.draw.rect(screen, RED, (self.x, self.y - 10, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, (self.x, self.y - 10, bar_width * health_pct, bar_height))

# ================= 游戏核心类 =================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter 2000")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 24)
        self.big_font = pygame.font.SysFont("arial", 48)
        
        self.state = GameState.MENU
        self.sound_manager = SoundManager()
        self.particles = ParticleSystem()
        
        # 游戏数据
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.enemies = []
        self.projectiles = []
        self.enemy_projectiles = []
        self.powerups = []
        
        # 关卡系统
        self.current_wave = 1
        self.wave_enemies_left = 0
        self.wave_delay = 0
        self.current_scene = SceneType.SPACE
        self.wave_number = 1
        self.boss_spawned = False
        
        # 存档系统
        self.save_file = "savegame.json"
        self.load_game_data()
        
        # 成就系统
        self.achievements = {
            "first_blood": False,
            "wave_5": False,
            "boss_killer": False,
            "level_5": False,
            "level_10": False,
            "no_damage": False, # 暂未实现完全无伤，简化为通关
            "weapon_master": False,
            "powerup_collector": False,
            "speed_demon": False,
            "survivor": False
        }
        self.achievement_unlocked_count = 0
        
        # 升级/技能树 UI
        self.upgrade_available = False
        self.upgrade_options = []
        
        # 输入
        self.keys = pygame.key.get_pressed()
        self.mouse_pos = (0, 0)
        
        # 场景背景
        self.stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)) for _ in range(100)]

    def load_game_data(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    data = json.load(f)
                    self.player.level = data.get('level', 1)
                    self.player.exp = data.get('exp', 0)
                    self.player.health = data.get('health', 100)
                    self.player.max_health = data.get('max_health', 100)
                    self.player.weapon_type = WeaponType(data.get('weapon', 0))
                    self.player.skills = data.get('skills', {'damage_boost': 0, 'speed_boost': 0, 'shield_boost': 0})
                    self.achievements = data.get('achievements', self.achievements)
                    self.achievement_unlocked_count = sum(1 for v in self.achievements.values() if v)
            except Exception as e:
                print(f"Error loading save: {e}")
        else:
            self.save_game()

    def save_game(self):
        data = {
            'level': self.player.level,
            'exp': self.player.exp,
            'health': self.player.health,
            'max_health': self.player.max_health,
            'weapon': self.player.weapon_type.value,
            'skills': self.player.skills,
            'achievements': self.achievements
        }
        with open(self.save_file, 'w') as f:
            json.dump(data, f)

    def start_game(self):
        self.state = GameState.PLAYING
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.enemies = []
        self.projectiles = []
        self.enemy_projectiles = []
        self.powerups = []
        self.wave_number = 1
        self.boss_spawned = False
        self.sound_manager.play('menu_select')

    def spawn_wave(self):
        if self.wave_delay > 0:
            self.wave_delay -= 1
            return

        # 每5波出现Boss
        if self.wave_number % 5 == 0 and not self.boss_spawned:
            self.enemies.append(Enemy(SCREEN_WIDTH // 2 - 60, -100, EnemyType.BOSS, self.wave_number))
            self.boss_spawned = True
            self.sound_manager.play('boss_spawn')
            self.wave_delay = 100
            return

        # 生成普通敌人
        count = 5 + self.wave_number * 2
        for _ in range(count):
            x = random.randint(0, SCREEN_WIDTH - 40)
            y = random.randint(-500, -50)
            r = random.random()
            if r < 0.5:
                etype = EnemyType.DRONE
            elif r < 0.7:
                etype = EnemyType.FIGHTER
            elif r < 0.85:
                etype = EnemyType.TANK
            else:
                etype = EnemyType.SPEEDER
            
            self.enemies.append(Enemy(x, y, etype, self.wave_number))
            
        self.wave_delay = 100 + self.wave_number * 10

    def update(self):
        if self.state != GameState.PLAYING:
            return

        self.keys = pygame.key.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()
        
        # 更新玩家
        self.player.update(self.keys, self.mouse_pos, self.screen.get_rect())
        
        # 生成波次
        self.spawn_wave()
        
        # 更新敌人
        for enemy in self.enemies[:]:
            enemy.update(self.player)
            if not enemy.active:
                # 死亡逻辑
                self.particles.emit(enemy.x + enemy.width/2, enemy.y + enemy.height/2, enemy.color, 20, 30, 5)
                self.sound_manager.play('explosion')
                
                # 掉落经验
                xp_gain = enemy.score_value
                level_up = self.player.gain_xp(xp_gain)
                
                # 掉落道具
                if random.random() < 0.1:
                    types = ['SHIELD', 'SPEED', 'BOMB', 'SCORE']
                    p_type = random.choice(types)
                    self.powerups.append(PowerUp(enemy.x, enemy.y, p_type))
                
                self.enemies.remove(enemy)
                
                # 检查Boss击杀成就
                if enemy.enemy_type == EnemyType.BOSS:
                    self.unlock_achievement('boss_killer')
                    self.boss_spawned = False
                    self.wave_number += 1
                    self.save_game()
                
                if level_up:
                    self.unlock_achievement('level_5' if self.player.level >= 5 else 'level_10' if self.player.level >= 10 else None)
                    self.show_upgrade_menu()

        # 更新投射物
        for proj in self.projectiles[:]:
            proj.update()
            if not proj.active:
                self.projectiles.remove(proj)
                
        for e_proj in self.enemy_projectiles[:]:
            e_proj.update()
            if not e_proj.active:
                self.enemy_projectiles.remove(e_proj)

        # 碰撞检测: 玩家投射物 vs 敌人
        for proj in self.projectiles[:]:
            for enemy in self.enemies[:]:
                if proj.active and enemy.active:
                    if (proj.x > enemy.x and proj.x < enemy.x + enemy.width and
                        proj.y > enemy.y and proj.y < enemy.y + enemy.height):
                        proj.active = False
                        enemy.take_damage(proj.damage)
                        self.particles.emit(proj.x, proj.y, proj.color, 5, 10, 2)
                        self.sound_manager.play('hit')
                        if not enemy.active:
                            pass # 处理在 enemy update 中
                        break

        # 碰撞检测: 敌人投射物 vs 玩家
        for e_proj in self.enemy_projectiles[:]:
            if e_proj.active:
                if (e_proj.x > self.player.x and e_proj.x < self.player.x + self.player.width and
                    e_proj.y > self.player.y and e_proj.y < self.player.y + self.player.height):
                    e_proj.active = False
                    self.player.take_damage(e_proj.damage)
                    self.particles.emit(self.player.x + 20, self.player.y + 20, RED, 10, 20, 3)
                    self.sound_manager.play('hit')

        # 碰撞检测: 敌人 vs 玩家 (撞击)
        for enemy in self.enemies[:]:
            if enemy.active:
                if (self.player.x < enemy.x + enemy.width and
                    self.player.x + self.player.width > enemy.x and
                    self.player.y < enemy.y + enemy.height and
                    self.player.height + self.player.y > enemy.y):
                    self.player.take_damage(20)
                    enemy.take_damage(100) # 撞击对敌人伤害大
                    self.particles.emit((self.player.x+enemy.x)/2, (self.player.y+enemy.y)/2, YELLOW, 15, 25, 4)
                    if not enemy.active:
                         self.enemies.remove(enemy)

        # 更新道具
        for powerup in self.powerups[:]:
            powerup.update()
            if powerup.y > SCREEN_HEIGHT:
                self.powerups.remove(powerup)
                continue
                
            # 收集道具
            if (self.player.x < powerup.x + powerup.width and
                self.player.x + self.player.width > powerup.x and
                self.player.y < powerup.y + powerup.height and
                self.player.height + self.player.y > powerup.y):
                
                self.apply_powerup(powerup.power_type)
                self.powerups.remove(powerup)
                self.sound_manager.play('powerup')
                self.unlock_achievement('powerup_collector')

        # 更新粒子
        self.particles.update()
        
        # 检查游戏结束
        if self.player.health <= 0:
            self.state = GameState.GAME_OVER
            self.save_game()
            self.unlock_achievement('survivor') # 即使死了也算经历了一场战斗

    def apply_powerup(self, p_type):
        if p_type == 'SHIELD':
            self.player.shield = self.player.max_shield
        elif p_type == 'SPEED':
            self.player.acceleration = True
            self.player.accel_timer = 300
        elif p_type == 'BOMB':
            # 全屏炸弹
            for enemy in self.enemies[:]:
                enemy.take_damage(100)
                if not enemy.active:
                    self.enemies.remove(enemy)
                    self.particles.emit(enemy.x, enemy.y, RED, 10, 20, 3)
            self.enemy_projectiles = []
            self.sound_manager.play('explosion')
        elif p_type == 'SCORE':
            self.player.gain_xp(50)

    def unlock_achievement(self, name):
        if name and name in self.achievements and not self.achievements[name]:
            self.achievements[name] = True
            self.achievement_unlocked_count += 1
            # 可以添加解锁提示

    def show_upgrade_menu(self):
        self.state = GameState.SHOP
        # 生成3个随机选项
        options_pool = [
            {'type': 'damage', 'name': 'Damage Boost', 'desc': '+10% Damage'},
            {'type': 'speed', 'name': 'Speed Boost', 'desc': '+10% Move Speed'},
            {'type': 'health', 'name': 'Health Boost', 'desc': '+20 Max Health'},
            {'type': 'weapon', 'name': 'Change Weapon', 'desc': 'Random Weapon'},
            {'type': 'shield', 'name': 'Shield Regen', 'desc': '+20% Shield Regen'},
            {'type': 'xp', 'name': 'XP Boost', 'desc': '+20% XP Gain'}
        ]
        self.upgrade_options = random.sample(options_pool, 3)
        self.upgrade_available = True

    def handle_upgrade_selection(self, index):
        if 0 <= index < len(self.upgrade_options):
            opt = self.upgrade_options[index]
            if opt['type'] == 'damage':
                self.player.skills['damage_boost'] += 1
            elif opt['type'] == 'speed':
                self.player.skills['speed_boost'] += 1
            elif opt['type'] == 'health':
                self.player.max_health += 20
                self.player.health += 20
            elif opt['type'] == 'weapon':
                self.player.weapon_type = random.choice(list(WeaponType))
            elif opt['type'] == 'shield':
                self.player.skills['shield_boost'] += 1
            elif opt['type'] == 'xp':
                self.player.xp_to_next_level = int(self.player.xp_to_next_level * 0.8)
                
        self.state = GameState.PLAYING
        self.upgrade_available = False

    def draw(self):
        self.screen.fill(BLACK)
        
        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.PLAYING:
            self.draw_game()
        elif self.state == GameState.PAUSED:
            self.draw_game()
            self.draw_overlay("PAUSED", "Press ESC to Resume")
        elif self.state == GameState.GAME_OVER:
            self.draw_game()
            self.draw_overlay("GAME OVER", "Press R to Restart or M for Menu")
        elif self.state == GameState.SHOP:
            self.draw_game()
            self.draw_upgrade_menu()
        elif self.state == GameState.ACHIEVEMENTS:
            self.draw_achievements()

        pygame.display.flip()

    def draw_menu(self):
        title = self.big_font.render("SPACE SHOOTER", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        start_text = self.font.render("Press ENTER to Start", True, GREEN)
        self.screen.blit(start_text, (SCREEN_WIDTH//2 - start_text.get_width()//2, 300))
        
        settings_text = self.font.render("Press S for Settings (Not Implemented)", True, GRAY)
        self.screen.blit(settings_text, (SCREEN_WIDTH//2 - settings_text.get_width()//2, 350))
        
        achievements_text = self.font.render("Press A for Achievements", True, GRAY)
        self.screen.blit(achievements_text, (SCREEN_WIDTH//2 - achievements_text.get_width()//2, 400))

    def draw_game(self):
        # 背景星星
        for star in self.stars:
            pygame.draw.circle(self.screen, WHITE, star, 1)
            star[1] += 1
            if star[1] > SCREEN_HEIGHT:
                star[1] = 0
        
        # 绘制实体
        self.player.draw(self.screen)
        for enemy in self.enemies:
            enemy.draw(self.screen)
        for proj in self.projectiles:
            proj.draw(self.screen)
        for e_proj in self.enemy_projectiles:
            e_proj.draw(self.screen)
        for powerup in self.powerups:
            powerup.draw(self.screen)
        self.particles.draw(self.screen)
        
        # HUD
        self.draw_hud()

    def draw_hud(self):
        # 血条
        pygame.draw.rect(self.screen, RED, (10, 10, 200, 20))
        pygame.draw.rect(self.screen, GREEN, (10, 10, 200 * (self.player.health / self.player.max_health), 20))
        
        # 护盾
        if self.player.shield > 0:
            pygame.draw.rect(self.screen, BLUE, (10, 35, 200, 10))
            pygame.draw.rect(self.screen, (0, 100, 255), (10, 35, 200 * (self.player.shield / self.player.max_shield), 10))
            
        # 等级和XP
        xp_text = self.font.render(f"LVL: {self.player.level}  XP: {int(self.player.exp)}/{self.player.xp_to_next_level}", True, WHITE)
        self.screen.blit(xp_text, (10, 50))
        
        # 波次
        wave_text = self.font.render(f"WAVE: {self.wave_number}", True, WHITE)
        self.screen.blit(wave_text, (SCREEN_WIDTH - 100, 10))
        
        # 武器
        weapon_text = self.font.render(f"Weapon: {self.player.weapon_type.name}", True, WHITE)
        self.screen.blit(weapon_text, (SCREEN_WIDTH - 100, 40))
        
        # 成就计数
        ach_text = self.font.render(f"Achievements: {self.achievement_unlocked_count}/10", True, GOLD)
        self.screen.blit(ach_text, (SCREEN_WIDTH - 100, 70))

    def draw_overlay(self, title, subtitle):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        t = self.big_font.render(title, True, WHITE)
        self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, SCREEN_HEIGHT//2 - 50))
        
        s = self.font.render(subtitle, True, GRAY)
        self.screen.blit(s, (SCREEN_WIDTH//2 - s.get_width()//2, SCREEN_HEIGHT//2 + 50))

    def draw_upgrade_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        title = self.big_font.render("LEVEL UP!", True, GOLD)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        for i, opt in enumerate(self.upgrade_options):
            y = 200 + i * 100
            rect = pygame.Rect(SCREEN_WIDTH//2 - 200, y, 400, 80)
            pygame.draw.rect(self.screen, GRAY, rect)
            pygame.draw.rect(self.screen, WHITE, rect, 2)
            
            name = self.font.render(opt['name'], True, WHITE)
            desc = self.font.render(opt['desc'], True, GRAY)
            self.screen.blit(name, (rect.x + 10, rect.y + 10))
            self.screen.blit(desc, (rect.x + 10, rect.y + 40))
            
            # 存储矩形以便点击检测
            opt.rect = rect

    def draw_achievements(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        title = self.big_font.render("ACHIEVEMENTS", True, GOLD)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        y = 150
        for name, unlocked in self.achievements.items():
            text = self.font.render(f"{name.replace('_', ' ').title()}: {'Unlocked' if unlocked else 'Locked'}", True, GOLD if unlocked else GRAY)
            self.screen.blit(text, (50, y))
            y += 30
            
        back_text = self.font.render("Press ESC to Back", True, WHITE)
        self.screen.blit(back_text, (SCREEN_WIDTH//2 - back_text.get_width()//2, SCREEN_HEIGHT - 50))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.save_game()
                    
                if event.type == pygame.KEYDOWN:
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
                    elif self.state == GameState.GAME_OVER:
                        if event.key == pygame.K_r:
                            self.start_game()
                        elif event.key == pygame.K_m:
                            self.state = GameState.MENU
                    elif self.state == GameState.ACHIEVEMENTS:
                        if event.key == pygame.K_ESCAPE:
                            self.state = GameState.MENU
                    elif self.state == GameState.SHOP:
                        if event.key == pygame.K_ESCAPE:
                            self.state = GameState.PLAYING # 取消升级，继续游戏

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.state == GameState.SHOP and self.upgrade_available:
                        if event.button == 1: # Left click
                            mouse_x, mouse_y = event.pos
                            for i, opt in enumerate(self.upgrade_options):
                                if opt.rect:
                                    if opt.rect.collidepoint(mouse_x, mouse_y):
                                        self.handle_upgrade_selection(i)
                                        break

            self.update()
            self.draw()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    # 定义一些常量用于绘图，如果之前没定义
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    
    game = Game()
    game.run()
