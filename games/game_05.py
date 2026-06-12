import pygame
import sys
import math
import random
import json
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# ==========================
# 1. 初始化与常量定义
# ==========================
pygame.init()
pygame.mixer.init()

# 屏幕设置
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)

# 游戏状态枚举
class GameState(Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3
    SHOP = 4
    ACHIEVEMENTS = 5

# ==========================
# 2. 音效管理器 (要求8)
# ==========================
class SoundManager:
    def __init__(self):
        self.sounds = {}
        # 由于没有外部文件，我们创建一个简单的合成音效生成器作为占位符
        # 在实际项目中，你会使用 pygame.mixer.Sound.load('path/to/file.wav')
        self.active = True

    def play_sound(self, name, pitch=1.0, volume=0.5):
        if not self.active:
            return
        
        # 模拟音效 (这里为了代码可运行性，不生成真实音频文件，而是打印日志或忽略)
        # 如果需要真实音效，请取消注释下面的加载代码并放入对应的wav文件
        # path = f"assets/sounds/{name}.wav"
        # if os.path.exists(path):
        #     if name not in self.sounds:
        #         self.sounds[name] = pygame.mixer.Sound(path)
        #     sound = self.sounds[name]
        #     sound.set_volume(volume)
        #     sound.play()
        pass

    def stop_all(self):
        pygame.mixer.stop()

# ==========================
# 3. 粒子系统 (要求7)
# ==========================
class Particle:
    def __init__(self, x, y, color, speed, life, size):
        self.x = x
        self.y = y
        self.color = color
        self.vx = speed * math.cos(random.uniform(0, math.pi * 2))
        self.vy = speed * math.sin(random.uniform(0, math.pi * 2))
        self.life = life
        self.max_life = life
        self.size = size
        self.alpha = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.alpha = int(255 * (self.life / self.max_life))
        # 简单的摩擦力
        self.vx *= 0.95
        self.vy *= 0.95

    def draw(self, screen):
        if self.life <= 0:
            return
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, self.alpha), (self.size, self.size), self.size)
        screen.blit(s, (self.x - self.size, self.y - self.size))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=10, speed_range=(1, 3), life_range=(20, 40), size_range=(2, 5)):
        for _ in range(count):
            speed = random.uniform(*speed_range)
            life = random.randint(*life_range)
            size = random.randint(*size_range)
            self.particles.append(Particle(x, y, color, speed, life, size))

    def update(self):
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# ==========================
# 4. 武器系统 (要求4)
# ==========================
class WeaponType(Enum):
    BLASTER = 0
    SHOTGUN = 1
    RAILGUN = 2
    MISSILE = 3
    LASER = 4
    PLASMA = 5

@dataclass
class WeaponStats:
    damage: float
    fire_rate: int  # frames between shots
    bullet_speed: float
    bullet_color: Tuple[int, int, int]
    bullet_size: int
    spread: float = 0.0
    type: WeaponType = WeaponType.BLASTER

WEAPONS = {
    WeaponType.BLASTER: WeaponStats(10, 10, 10, CYAN, 3),
    WeaponType.SHOTGUN: WeaponStats(5, 40, 8, YELLOW, 2, spread=0.3),
    WeaponType.RAILGUN: WeaponStats(50, 60, 20, RED, 1),
    WeaponType.MISSILE: WeaponStats(30, 80, 5, ORANGE, 4),
    WeaponType.LASER: WeaponStats(2, 2, 15, PURPLE, 1),
    WeaponType.PLASMA: WeaponStats(20, 25, 7, GREEN, 5),
}

class Bullet:
    def __init__(self, x, y, angle, weapon_type, owner="player"):
        stats = WEAPONS[weapon_type]
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * stats.bullet_speed
        self.vy = math.sin(angle) * stats.bullet_speed
        self.damage = stats.damage
        self.color = stats.bullet_color
        self.size = stats.bullet_size
        self.weapon_type = weapon_type
        self.owner = owner  # "player" or "enemy"
        self.life = 100
        self.is_homing = weapon_type == WeaponType.MISSILE
        self.target = None
        self.angle = angle

    def update(self, enemies):
        if self.is_homing and self.owner == "enemy" and not self.target:
            # 简单的追踪逻辑
            pass
        
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        
        # 屏幕边界检查
        if (self.x < 0 or self.x > SCREEN_WIDTH or 
            self.y < 0 or self.y > SCREEN_HEIGHT):
            self.life = 0

    def draw(self, screen):
        if self.life <= 0:
            return
        if self.weapon_type == WeaponType.RAILGUN:
            pygame.draw.line(screen, self.color, (self.x - self.vx*2, self.y - self.vy*2), (self.x, self.y), 2)
        else:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)

# ==========================
# 5. 道具系统 (要求6)
# ==========================
class ItemType(Enum):
    HEALTH = 0
    SHIELD = 1
    SPEED_BOOST = 2
    BOMB = 3
    DOUBLE_DAMAGE = 4
    RAPID_FIRE = 5
    FREEZE = 6
    LUCKY_STAR = 7

class PowerUp:
    def __init__(self, x, y, item_type):
        self.x = x
        self.y = y
        self.item_type = item_type
        self.width = 20
        self.height = 20
        self.vy = 2
        self.angle = 0

    def update(self):
        self.y += self.vy
        self.angle += 0.1

    def draw(self, screen):
        # 简单的图标绘制
        color = WHITE
        if self.item_type == ItemType.HEALTH: color = RED
        elif self.item_type == ItemType.SHIELD: color = BLUE
        elif self.item_type == ItemType.SPEED_BOOST: color = YELLOW
        elif self.item_type == ItemType.BOMB: color = ORANGE
        elif self.item_type == ItemType.DOUBLE_DAMAGE: color = PURPLE
        elif self.item_type == ItemType.RAPID_FIRE: color = GREEN
        elif self.item_type == ItemType.FREEZE: color = CYAN
        elif self.item_type == ItemType.LUCKY_STAR: color = WHITE
        
        pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 2)
        
        # 内部符号
        center_x = int(self.x + self.width/2)
        center_y = int(self.y + self.height/2)
        font = pygame.font.SysFont("arial", 12)
        text = ""
        if self.item_type == ItemType.HEALTH: text = "+"
        elif self.item_type == ItemType.SHIELD: text = "S"
        elif self.item_type == ItemType.BOMB: text = "B"
        else: text = "*"
        
        txt_surf = font.render(text, True, BLACK)
        screen.blit(txt_surf, (center_x - 6, center_y - 6))

# ==========================
# 6. 玩家类 (要求1)
# ==========================
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.speed = 5
        self.max_health = 100
        self.health = self.max_health
        self.shield = 0
        self.max_shield = 50
        self.current_weapon = WeaponType.BLASTER
        self.fire_rate_timer = 0
        self.angle = 0  # 鼠标指向的角度
        self.invulnerable = 0
        
        # 升级相关
        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        
        # 技能树状态
        self.skills = {
            "rapid_fire": False,
            "extra_life": False,
            "magnet": False,
            "crit_chance": False,
            "speed_boost": False
        }
        
        # 临时增益
        self.buffs = {
            "double_damage": 0,
            "rapid_fire": 0,
            "freeze": 0
        }

    def update(self, mouse_pos, keys, particles, sound_mgr):
        # 移动 (WASD)
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = 1
        
        # 归一化对角线移动
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
            
        # 应用速度
        current_speed = self.speed
        if self.skills["speed_boost"]:
            current_speed *= 1.5
        if self.buffs["freeze"] > 0:
            current_speed *= 0.5
            
        self.x += dx * current_speed
        self.y += dy * current_speed
        
        # 边界限制
        self.x = max(self.width/2, min(SCREEN_WIDTH - self.width/2, self.x))
        self.y = max(self.height/2, min(SCREEN_HEIGHT - self.height/2, self.y))
        
        # 鼠标控制方向
        self.angle = math.atan2(mouse_pos[1] - self.y, mouse_pos[0] - self.x)
        
        # 射击
        if self.fire_rate_timer > 0:
            self.fire_rate_timer -= 1
        if keys[pygame.K_SPACE] and self.fire_rate_timer <= 0:
            self.shoot(particles, sound_mgr)
            self.fire_rate_timer = self.get_fire_rate()
            
        # 更新增益时间
        if self.buffs["double_damage"] > 0: self.buffs["double_damage"] -= 1
        if self.buffs["rapid_fire"] > 0: self.buffs["rapid_fire"] -= 1
        if self.buffs["freeze"] > 0: self.buffs["freeze"] -= 1
        if self.invulnerable > 0: self.invulnerable -= 1
        
        # 引擎尾焰
        if random.random() < 0.5:
            particles.emit(self.x, self.y + 20, (100, 150, 255), 1, (10, 20), (2, 4))

    def shoot(self, particles, sound_mgr):
        # 计算实际射速
        rate = self.get_fire_rate()
        if self.buffs["rapid_fire"] > 0:
            rate = max(1, rate // 2)
            
        # 创建子弹
        bullet_count = 1
        if self.skills["multi_shot"]: # 假设有一个技能
             pass 
            
        # 基础射击
        stats = WEAPONS[self.current_weapon]
        
        # 散射
        if self.current_weapon == WeaponType.SHOTGUN:
            for i in range(-2, 3):
                angle = self.angle + i * stats.spread
                bullet = Bullet(self.x, self.y, angle, self.current_weapon)
                bullet.damage *= 0.8
                game_instance.add_bullet(bullet)
        else:
            bullet = Bullet(self.x, self.y, self.angle, self.current_weapon)
            if self.skills["crit_chance"] and random.random() < 0.2:
                bullet.damage *= 2
            game_instance.add_bullet(bullet)
            
        sound_mgr.play_sound("shoot")
        
        # 后坐力效果
        particles.emit(self.x, self.y, (200, 200, 255), 2, (5, 10), (1, 2))

    def get_fire_rate(self):
        base_rate = WEAPONS[self.current_weapon].fire_rate
        if self.skills["rapid_fire"]:
            return max(5, base_rate // 2)
        return base_rate

    def take_damage(self, amount):
        if self.invulnerable > 0:
            return
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield # 剩余伤害转移到生命
                self.shield = 0
        else:
            self.health -= amount
            
        if self.health <= 0:
            game_instance.game_over()

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_to_next:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next
        self.exp_to_next = int(self.exp_to_next * 1.2)
        self.health = self.max_health # 升级回满血
        # 这里可以打开升级菜单
        game_instance.set_state(GameState.SHOP)

    def draw(self, screen):
        if self.invulnerable > 0 and self.invulnerable % 4 < 2:
            return # 闪烁效果
            
        pygame.draw.polygon(screen, BLUE, [
            (self.x, self.y - 20),
            (self.x - 15, self.y + 15),
            (self.x + 15, self.y + 15)
        ])
        
        # 护盾显示
        if self.shield > 0:
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), 25, 2)

# ==========================
# 7. 敌人类 (要求2)
# ==========================
class Enemy:
    def __init__(self, x, y, enemy_type, wave):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.wave = wave
        self.width = 30
        self.height = 30
        self.angle = 0
        self.shoot_timer = 0
        self.move_timer = 0
        self.path = []
        self.path_index = 0
        
        # 根据类型和波次设置属性
        self.set_properties()

    def set_properties(self):
        if self.enemy_type == 0: # 基础型
            self.health = 20 + self.wave * 2
            self.speed = 2
            self.color = RED
            self.score = 10
        elif self.enemy_type == 1: # 快速型
            self.health = 10 + self.wave
            self.speed = 4
            self.color = ORANGE
            self.score = 15
        elif self.enemy_type == 2: # 坦克型
            self.health = 60 + self.wave * 5
            self.speed = 1
            self.color = PURPLE
            self.width = 40
            self.height = 40
            self.score = 30
        elif self.enemy_type == 3: # 射击型
            self.health = 25 + self.wave * 2
            self.speed = 1.5
            self.color = GREEN
            self.score = 20
        elif self.enemy_type == 4: # 分裂型
            self.health = 15 + self.wave
            self.speed = 2.5
            self.color = CYAN
            self.score = 25

    def update(self, player, bullets, particles, sound_mgr):
        # 移动逻辑
        if self.enemy_type == 1: # 快速型：直接冲向玩家
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed
        
        elif self.enemy_type == 3: # 射击型：保持距离并射击
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist > 300:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed
            elif dist < 150:
                self.x -= (dx / dist) * self.speed
                self.y -= (dy / dist) * self.speed
            
            # 射击
            self.shoot_timer += 1
            if self.shoot_timer > 60:
                angle = math.atan2(dy, dx)
                bullet = Bullet(self.x, self.y, angle, WeaponType.BLASTER, owner="enemy")
                bullet.damage = 10
                bullets.append(bullet)
                self.shoot_timer = 0
                
        else:
            # 其他类型：缓慢向下移动
            self.y += self.speed

        self.angle = math.atan2(player.y - self.y, player.x - self.x)
        
        # 边界检查
        if self.y > SCREEN_HEIGHT + 50:
            return False # 移除
            
        return True

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            return True # Dead
        return False

    def draw(self, screen):
        color = self.color
        if self.enemy_type == 0:
            pygame.draw.rect(screen, color, (self.x - self.width/2, self.y - self.height/2, self.width, self.height))
        elif self.enemy_type == 2:
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.width/2)
        else:
            pygame.draw.polygon(screen, color, [
                (self.x, self.y - self.height/2),
                (self.x - self.width/2, self.y + self.height/2),
                (self.x + self.width/2, self.y + self.height/2)
            ])

# ==========================
# 8. Boss类 (要求3)
# ==========================
class Boss:
    def __init__(self, wave):
        self.x = SCREEN_WIDTH / 2
        self.y = -100
        self.target_y = 100
        self.health = 500 + wave * 100
        self.max_health = self.health
        self.width = 80
        self.height = 80
        self.phase = 1
        self.shoot_timer = 0
        self.move_timer = 0
        self.angle = 0
        self.active = True
        self.entered = False

    def update(self, player, bullets, particles, sound_mgr):
        # 入场动画
        if not self.entered:
            self.y += 2
            if self.y >= self.target_y:
                self.entered = True
            return
            
        # 移动逻辑
        self.move_timer += 1
        if self.move_timer % 60 == 0:
            self.x = random.randint(100, SCREEN_WIDTH - 100)
            
        # 攻击逻辑
        self.shoot_timer += 1
        attack_rate = 30 if self.phase == 1 else 15
        
        if self.shoot_timer > attack_rate:
            self.attack(bullets, particles, sound_mgr)
            self.shoot_timer = 0
            
        # 阶段转换
        if self.health < self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            particles.emit(self.x, self.y, RED, 50, (5, 10), (5, 10))

    def attack(self, bullets, particles, sound_mgr):
        if self.phase == 1:
            # 扇形弹幕
            for i in range(-2, 3):
                angle = math.atan2(player.y - self.y, player.x - self.x) + i * 0.2
                b = Bullet(self.x, self.y, angle, WeaponType.BLASTER, owner="enemy")
                b.damage = 15
                bullets.append(b)
        else:
            # 环形弹幕
            for i in range(12):
                angle = i * (math.pi * 2 / 12)
                b = Bullet(self.x, self.y, angle, WeaponType.RAILGUN, owner="enemy")
                b.damage = 20
                bullets.append(b)
                
        sound_mgr.play_sound("boss_attack")

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.active = False
            return True
        return False

    def draw(self, screen):
        if not self.entered:
            return
            
        # 绘制Boss主体
        pygame.draw.rect(screen, RED, (self.x - self.width/2, self.y - self.height/2, self.width, self.height))
        
        # 血条
        bar_width = 200
        bar_height = 10
        x_pos = (SCREEN_WIDTH - bar_width) // 2
        y_pos = 20
        pygame.draw.rect(screen, DARK_GRAY, (x_pos, y_pos, bar_width, bar_height))
        health_pct = max(0, self.health / self.max_health)
        pygame.draw.rect(screen, RED if self.phase == 1 else PURPLE, (x_pos, y_pos, bar_width * health_pct, bar_height))
        
        font = pygame.font.SysFont("arial", 20)
        text = font.render("BOSS", True, WHITE)
        screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y_pos + 15))

# ==========================
# 9. 成就系统 (要求12)
# ==========================
class AchievementManager:
    def __init__(self):
        self.achievements = {
            "first_kill": {"name": "First Blood", "desc": "Kill your first enemy", "unlocked": False},
            "level_5": {"name": "Veteran", "desc": "Reach level 5", "unlocked": False},
            "boss_slayer": {"name": "Boss Slayer", "desc": "Defeat a boss", "unlocked": False},
            "no_damage": {"name": "Flawless", "desc": "Complete a wave without taking damage", "unlocked": False},
            "speed_demon": {"name": "Speed Demon", "desc": "Reach max speed skill", "unlocked": False},
            "collector": {"name": "Collector", "desc": "Collect 10 power-ups", "unlocked": False},
            "survivor": {"name": "Survivor", "desc": "Survive 10 waves", "unlocked": False},
            "sharpshooter": {"name": "Sharpshooter", "desc": "Kill 100 enemies", "unlocked": False},
            "rich": {"name": "Millionaire", "desc": "Have 1,000,000 score", "unlocked": False},
            "explorer": {"name": "Explorer", "desc": "Unlock all weapons", "unlocked": False},
        }
        self.load()

    def unlock(self, key):
        if key in self.achievements and not self.achievements[key]["unlocked"]:
            self.achievements[key]["unlocked"] = True
            self.save()
            print(f"Achievement Unlocked: {self.achievements[key]['name']}")

    def save(self):
        with open("achievements.json", "w") as f:
            json.dump(self.achievements, f)

    def load(self):
        if os.path.exists("achievements.json"):
            with open("achievements.json", "r") as f:
                self.achievements = json.load(f)
            # 确保所有键都存在
            for k in self.achievements:
                if k not in ["unlocked"]:
                    pass # 结构检查

# ==========================
# 10. 存档系统 (要求11)
# ==========================
class SaveManager:
    def __init__(self):
        self.filename = "savegame.json"

    def save_game(self, player, wave, score, achievements):
        data = {
            "player_level": player.level,
            "player_exp": player.exp,
            "player_skills": player.skills,
            "wave": wave,
            "score": score,
            "achievements": achievements
        }
        with open(self.filename, "w") as f:
            json.dump(data, f)

    def load_game(self):
        if not os.path.exists(self.filename):
            return None
        with open(self.filename, "r") as f:
            return json.load(f)

# ==========================
# 11. 关卡与场景管理 (要求9)
# ==========================
class LevelManager:
    def __init__(self):
        self.current_scene = 0 # 0: Space, 1: Asteroid, 2: Nebula
        self.scene_colors = [BLACK, (20, 20, 40), (10, 0, 20)]
        self.stars = []
        self.generate_stars()

    def generate_stars(self):
        self.stars = []
        for _ in range(100):
            self.stars.append({
                "x": random.randint(0, SCREEN_WIDTH),
                "y": random.randint(0, SCREEN_HEIGHT),
                "size": random.randint(1, 3),
                "speed": random.uniform(0.1, 1)
            })

    def update(self):
        for star in self.stars:
            star["y"] += star["speed"]
            if star["y"] > SCREEN_HEIGHT:
                star["y"] = 0
                star["x"] = random.randint(0, SCREEN_WIDTH)

    def draw(self, screen):
        color = self.scene_colors[self.current_scene]
        screen.fill(color)
        
        # 绘制星星
        for star in self.stars:
            pygame.draw.circle(screen, WHITE, (int(star["x"]), int(star["y"])), star["size"])

# ==========================
# 12. UI系统 (要求10)
# ==========================
class UIManager:
    def __init__(self):
        self.font_large = pygame.font.SysFont("arial", 48)
        self.font_medium = pygame.font.SysFont("arial", 24)
        self.font_small = pygame.font.SysFont("arial", 18)

    def draw_text(self, screen, text, x, y, color=WHITE, font=None, center=False):
        if font is None:
            font = self.font_medium
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        screen.blit(surf, rect)

    def draw_hud(self, screen, player, wave, score, sound_mgr):
        # 血条
        bar_width = 200
        bar_height = 15
        x, y = 10, 10
        
        # 生命
        pygame.draw.rect(screen, DARK_GRAY, (x, y, bar_width, bar_height))
        health_pct = player.health / player.max_health
        pygame.draw.rect(screen, RED, (x, y, bar_width * health_pct, bar_height))
        self.draw_text(screen, f"HP: {int(player.health)}/{player.max_health}", x, y + 20, WHITE, self.font_small)
        
        # 经验
        y += 40
        pygame.draw.rect(screen, DARK_GRAY, (x, y, bar_width, bar_height))
        exp_pct = player.exp / player.exp_to_next
        pygame.draw.rect(screen, BLUE, (x, y, bar_width * exp_pct, bar_height))
        self.draw_text(screen, f"LVL: {player.level}", x, y + 20, WHITE, self.font_small)
        
        # 分数
        self.draw_text(screen, f"Score: {score}", SCREEN_WIDTH - 150, 10, WHITE, self.font_medium)
        
        # 波次
        self.draw_text(screen, f"WAVE: {wave}", SCREEN_WIDTH - 150, 40, WHITE, self.font_small)

    def draw_menu(self, screen):
        screen.fill(BLACK)
        self.draw_text(screen, "SPACE SHOOTER", SCREEN_WIDTH//2, SCREEN_HEIGHT//3, CYAN, self.font_large, True)
        self.draw_text(screen, "Press ENTER to Start", SCREEN_WIDTH//2, SCREEN_HEIGHT//2, WHITE, self.font_medium, True)
        self.draw_text(screen, "Press M for Menu", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50, GRAY, self.font_small, True)

    def draw_pause(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        self.draw_text(screen, "PAUSED", SCREEN_WIDTH//2, SCREEN_HEIGHT//3, WHITE, self.font_large, True)
        self.draw_text(screen, "Press P to Resume", SCREEN_WIDTH//2, SCREEN_HEIGHT//2, WHITE, self.font_medium, True)
        self.draw_text(screen, "Press ESC to Quit", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 40, WHITE, self.font_medium, True)

    def draw_game_over(self, screen, score):
        screen.fill(BLACK)
        self.draw_text(screen, "GAME OVER", SCREEN_WIDTH//2, SCREEN_HEIGHT//3, RED, self.font_large, True)
        self.draw_text(screen, f"Final Score: {score}", SCREEN_WIDTH//2, SCREEN_HEIGHT//2, WHITE, self.font_medium, True)
        self.draw_text(screen, "Press ENTER to Restart", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 60, WHITE, self.font_medium, True)

    def draw_shop(self, screen, player):
        screen.fill((20, 20, 30))
        self.draw_text(screen, "UPGRADE SHOP", SCREEN_WIDTH//2, 50, CYAN, self.font_large, True)
        
        y_start = 150
        options = [
            ("Rapid Fire", "skills.rapid_fire", "Double fire rate"),
            ("Speed Boost", "skills.speed_boost", "Move 50% faster"),
            ("Crit Chance", "skills.crit_chance", "20% chance for double damage"),
            ("Health Upgrade", "health", "Heal and increase max HP")
        ]
        
        for i, (name, key, desc) in enumerate(options):
            y = y_start + i * 80
            btn_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, y, 300, 60)
            
            # 检查是否已购买
            is_bought = False
            if key.startswith("skills"):
                sk = key.split(".")[1]
                if player.skills.get(sk, False):
                    is_bought = True
            
            color = GREEN if is_bought else BLUE
            pygame.draw.rect(screen, color, btn_rect)
            pygame.draw.rect(screen, WHITE, btn_rect, 2)
            
            self.draw_text(screen, f"{name} {'[OWNED]' if is_bought else '[BUY]'}", SCREEN_WIDTH//2, y + 20, WHITE, self.font_medium, True)
            self.draw_text(screen, desc, SCREEN_WIDTH//2, y + 40, GRAY, self.font_small, True)
            
            # 简单的点击检测逻辑需要在主循环中处理，这里只负责绘制

# ==========================
# 13. 主游戏类
# ==========================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter Pro")
        self.clock = pygame.time.Clock()
        
        self.state = GameState.MENU
        self.sound_mgr = SoundManager()
        self.particles = ParticleSystem()
        self.level_mgr = LevelManager()
        self.ui = UIManager()
        self.save_mgr = SaveManager()
        self.achievement_mgr = AchievementManager()
        
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.bullets = []
        self.enemies = []
        self.powerups = []
        self.boss = None
        
        self.wave = 1
        self.score = 0
        self.wave_timer = 0
        self.enemies_to_spawn = 0
        self.spawn_timer = 0
        
        self.mouse_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.keys = pygame.key.get_pressed()
        
        self.last_save = 0

    def set_state(self, new_state):
        self.state = new_state

    def reset_game(self):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.bullets = []
        self.enemies = []
        self.powerups = []
        self.boss = None
        self.wave = 1
        self.score = 0
        self.wave_timer = 0
        self.enemies_to_spawn = 10
        self.spawn_timer = 0
        self.particles = ParticleSystem()
        self.level_mgr.current_scene = 0
        self.set_state(GameState.PLAYING)
        self.start_wave()

    def start_wave(self):
        # 根据波次增加难度
        base_enemies = 5 + self.wave * 2
        self.enemies_to_spawn = base_enemies
        self.spawn_timer = 0
        
        # Boss Wave
        if self.wave % 5 == 0:
            self.boss = Boss(self.wave)
            self.achievement_mgr.unlock("boss_slayer") # 标记检查，实际解锁在击败时

    def update(self):
        if self.state == GameState.PLAYING:
            self.handle_playing()
        elif self.state == GameState.SHOP:
            self.handle_shop()
            
        # 全局更新
        self.level_mgr.update()
        self.particles.update()
        
        # 自动存档 (每30秒)
        self.last_save += 1
        if self.last_save > 1800: # ~30 seconds at 60fps
            self.save_mgr.save_game(self.player, self.wave, self.score, self.achievement_mgr.achievements)
            self.last_save = 0

    def handle_playing(self):
        # 玩家更新
        self.player.update(self.mouse_pos, self.keys, self.particles, self.sound_mgr)
        
        # Boss更新
        if self.boss:
            dead = self.boss.update(self.player, self.bullets, self.particles, self.sound_mgr)
            if dead:
                self.score += 1000
                self.wave += 1
                self.boss = None
                self.start_wave()
                # 检查成就
                self.achievement_mgr.unlock("boss_slayer")
                self.achievement_mgr.unlock("survivor")
        else:
            # 敌人生成
            if self.enemies_to_spawn > 0:
                self.spawn_timer += 1
                if self.spawn_timer > 60: # 每秒生成一个
                    self.spawn_enemy()
                    self.enemies_to_spawn -= 1
                    self.spawn_timer = 0
            
            # 检查波次结束
            if self.enemies_to_spawn == 0 and len(self.enemies) == 0:
                self.wave += 1
                self.start_wave()
                self.achievement_mgr.unlock("survivor")

        # 子弹更新
        for b in self.bullets[:]:
            b.update(self.enemies)
            if b.life <= 0:
                self.bullets.remove(b)
                continue
                
            # 子弹碰撞检测
            if b.owner == "player":
                # 击中敌人
                for e in self.enemies[:]:
                    if math.hypot(b.x - e.x, b.y - e.y) < (e.width/2 + b.size):
                        if e.take_damage(b.damage):
                            self.kill_enemy(e)
                        self.bullets.remove(b)
                        break
                # 击中Boss
                if self.boss and self.boss.active and self.boss.entered:
                    if math.hypot(b.x - self.boss.x, b.y - self.boss.y) < (self.boss.width/2 + b.size):
                        if self.boss.take_damage(b.damage):
                            pass # Boss死亡处理在update中
                        self.bullets.remove(b)
                        
            elif b.owner == "enemy":
                # 击中玩家
                if math.hypot(b.x - self.player.x, b.y - self.player.y) < (self.player.width/2 + b.size):
                    self.player.take_damage(b.damage)
                    self.bullets.remove(b)

        # 敌人更新
        for e in self.enemies[:]:
            active = e.update(self.player, self.bullets, self.particles, self.sound_mgr)
            if not active:
                self.enemies.remove(e)
            else:
                # 碰撞玩家
                if math.hypot(e.x - self.player.x, e.y - self.player.y) < (e.width/2 + self.player.width/2):
                    self.player.take_damage(10)
                    self.kill_enemy(e)

        # 道具更新
        for p in self.powerups[:]:
            p.update()
            if p.y > SCREEN_HEIGHT:
                self.powerups.remove(p)
            elif math.hypot(p.x - self.player.x, p.y - self.player.y) < 30:
                self.collect_powerup(p)
                self.powerups.remove(p)

    def spawn_enemy(self):
        x = random.randint(50, SCREEN_WIDTH - 50)
        y = -50
        # 根据波次决定敌人类型
        r = random.random()
        if r < 0.5:
            etype = 0
        elif r < 0.7:
            etype = 1
        elif r < 0.85:
            etype = 2
        else:
            etype = 3
            
        self.enemies.append(Enemy(x, y, etype, self.wave))

    def kill_enemy(self, enemy):
        self.score += enemy.score
        self.player.gain_exp(enemy.score)
        self.particles.emit(enemy.x, enemy.y, enemy.color, 20, (2, 5), (10, 30))
        self.sound_mgr.play_sound("explosion")
        
        # 掉落道具
        if random.random() < 0.2:
            item_type = random.choice(list(ItemType))
            self.powerups.append(PowerUp(enemy.x, enemy.y, item_type))
            
        # 成就检查
        self.achievement_mgr.unlock("first_kill")
        if self.score > 1000000:
            self.achievement_mgr.unlock("rich")

    def collect_powerup(self, powerup):
        if powerup.item_type == ItemType.HEALTH:
            self.player.heal(20)
        elif powerup.item_type == ItemType.SHIELD:
            self.player.shield = min(self.player.max_shield, self.player.shield + 20)
        elif powerup.item_type == ItemType.SPEED_BOOST:
            self.player.skills["speed_boost"] = True
            self.achievement_mgr.unlock("speed_demon")
        elif powerup.item_type == ItemType.BOMB:
            # 全屏清除敌人
            for e in self.enemies[:]:
                self.kill_enemy(e)
            self.enemies = []
            self.particles.emit(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, WHITE, 100, (1, 10), (50, 100))
            self.sound_mgr.play_sound("bomb")
        elif powerup.item_type == ItemType.DOUBLE_DAMAGE:
            self.player.buffs["double_damage"] = 600 # 10 seconds
        elif powerup.item_type == ItemType.RAPID_FIRE:
            self.player.buffs["rapid_fire"] = 600
        elif powerup.item_type == ItemType.FREEZE:
            self.player.buffs["freeze"] = 600
        elif powerup.item_type == ItemType.LUCKY_STAR:
            self.score += 500

    def handle_shop(self):
        # 简单的商店交互：按数字键选择
        keys = pygame.key.get_pressed()
        if keys[pygame.K_1]:
            if not self.player.skills["rapid_fire"]:
                self.player.skills["rapid_fire"] = True
                self.set_state(GameState.PLAYING)
        if keys[pygame.K_2]:
            if not self.player.skills["speed_boost"]:
                self.player.skills["speed_boost"] = True
                self.set_state(GameState.PLAYING)
        if keys[pygame.K_3]:
            if not self.player.skills["crit_chance"]:
                self.player.skills["crit_chance"] = True
                self.set_state(GameState.PLAYING)
        if keys[pygame.K_4]:
            self.player.heal(50)
            self.player.max_health += 10
            self.set_state(GameState.PLAYING)
        if keys[pygame.K_ESCAPE]:
            self.set_state(GameState.PLAYING)

    def game_over(self):
        self.set_state(GameState.GAME_OVER)
        self.sound_mgr.play_sound("game_over")

    def draw(self):
        self.level_mgr.draw(self.screen)
        
        if self.state == GameState.MENU:
            self.ui.draw_menu(self.screen)
        elif self.state == GameState.PLAYING:
            # 绘制游戏实体
            for p in self.powerups:
                p.draw(self.screen)
            for e in self.enemies:
                e.draw(self.screen)
            for b in self.bullets:
                b.draw(self.screen)
            if self.boss:
                self.boss.draw(self.screen)
            self.player.draw(self.screen)
            self.particles.draw(self.screen)
            self.ui.draw_hud(self.screen, self.player, self.wave, self.score, self.sound_mgr)
            
        elif self.state == GameState.PAUSED:
            self.ui.draw_pause(self.screen)
        elif self.state == GameState.GAME_OVER:
            self.ui.draw_game_over(self.screen, self.score)
        elif self.state == GameState.SHOP:
            self.ui.draw_shop(self.screen, self.player)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = event.pos
                    
                if event.type == pygame.KEYDOWN:
                    if self.state == GameState.MENU:
                        if event.key == pygame.K_RETURN:
                            self.reset_game()
                    elif self.state == GameState.PLAYING:
                        if event.key == pygame.K_p:
                            self.set_state(GameState.PAUSED)
                    elif self.state == GameState.PAUSED:
                        if event.key == pygame.K_p:
                            self.set_state(GameState.PLAYING)
                        elif event.key == pygame.K_ESCAPE:
                            running = False
                    elif self.state == GameState.GAME_OVER:
                        if event.key == pygame.K_RETURN:
                            self.reset_game()
                            
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

# ==========================
# 启动游戏
# ==========================
if __name__ == "__main__":
    game = Game()
    game.run()
