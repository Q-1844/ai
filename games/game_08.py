import pygame
import sys
import math
import random
import json
import os
import time

# 初始化 Pygame
pygame.init()
pygame.mixer.init()

# ================= 配置常量 =================
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (50, 50, 50)

# 游戏状态
STATE_MENU = 0
STATE_PLAYING = 1
STATE_PAUSED = 2
STATE_GAME_OVER = 3
STATE_LEVEL_TRANSITION = 4

# 场景定义
SCENE_SPACE = 0
SCENE_ASTEROID_FIELD = 1
SCENE_NEON_CITY = 2

# ================= 音效管理器 (要求9) =================
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.music_volume = 0.5
        self.effect_volume = 0.7
        self.current_music = None

    def load_sound(self, name, filepath):
        try:
            if filepath and os.path.exists(filepath):
                self.sounds[name] = pygame.mixer.Sound(filepath)
                self.sounds[name].set_volume(self.effect_volume)
            else:
                # 模拟加载成功，但实际无声，避免崩溃
                self.sounds[name] = None
        except Exception as e:
            print(f"Sound load error: {e}")
            self.sounds[name] = None

    def play_sound(self, name):
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].play()

    def set_music_volume(self, vol):
        self.music_volume = vol
        pygame.mixer.music.set_volume(vol)

    def play_music(self, filename, loops=-1):
        try:
            if filename and os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(loops)
                self.current_music = filename
        except Exception as e:
            print(f"Music load error: {e}")

    def stop_music(self):
        pygame.mixer.music.stop()

# ================= 粒子系统 (要求7) =================
class Particle:
    def __init__(self, x, y, color, speed, life, size=2):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = life
        self.max_life = life
        self.size = size
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, screen):
        alpha = int(255 * (self.life / self.max_life))
        # 简化绘制，使用半透明圆形效果在普通Surface上较难，这里简化为不透明度调整颜色亮度
        color_intensity = int(255 * (self.life / self.max_life))
        draw_color = (min(255, self.color[0] + color_intensity), 
                      min(255, self.color[1] + color_intensity), 
                      min(255, self.color[2] + color_intensity))
        pygame.draw.circle(screen, draw_color, (int(self.x), int(self.y)), self.size)

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=10, speed_range=(1, 5), life_range=(20, 50), size_range=(1, 4)):
        for _ in range(count):
            speed = random.uniform(speed_range[0], speed_range[1])
            life = random.randint(life_range[0], life_range[1])
            size = random.randint(size_range[0], size_range[1])
            self.particles.append(Particle(x, y, color, speed, life, size))

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# ================= 实体基类 =================
class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.image.set_colorkey(BLACK) # 允许透明
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.width = width
        self.height = height
        self.color = color
        self.health = 100
        self.max_health = 100
        self.dead = False
        self.exp_value = 0

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.dead = True
            self.health = 0

    def draw(self, screen):
        # 绘制血条
        if self.health < self.max_health:
            bar_width = self.width
            bar_height = 4
            x = self.rect.x
            y = self.rect.y - 8
            pygame.draw.rect(screen, RED, (x, y, bar_width, bar_height))
            pygame.draw.rect(screen, GREEN, (x, y, bar_width * (self.health / self.max_health), bar_height))

class Projectile(Entity):
    def __init__(self, x, y, vx, vy, damage, color, size=4, owner="player"):
        super().__init__(x, y, size, size, color)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.owner = owner # "player" or "enemy"
        self.lifespan = 100

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.lifespan -= 1
        if self.lifespan <= 0 or not self.rect.colliderect(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)):
            self.dead = True

class Bullet(Projectile):
    def __init__(self, x, y, vx, vy, damage, color, owner="player"):
        super().__init__(x, y, vx, vy, damage, color, 4, owner)

# ================= 玩家飞船 (要求1) =================
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40, BLUE)
        self.speed = 5
        self.max_speed = 8
        self.weapon = "basic"
        self.fire_rate = 15 # frames between shots
        self.fire_timer = 0
        self.shield = 0
        self.max_shield = 100
        self.shield_regen_rate = 0.5
        self.shield_regen_timer = 0
        self.invincible_timer = 0
        self.angle = 0 # Mouse angle
        self.experience = 0
        self.level = 1
        self.skill_points = 0
        self.skills = {
            "damage": 0,
            "speed": 0,
            "shield": 0,
            "fire_rate": 0
        }
        
        # 武器配置
        self.weapons = {
            "basic": {"damage": 10, "rate": 15, "color": YELLOW, "speed": 10},
            "spread": {"damage": 8, "rate": 25, "color": ORANGE, "speed": 9, "count": 3},
            "laser": {"damage": 2, "rate": 2, "color": CYAN, "speed": 20, "beam": True},
            "missile": {"damage": 30, "rate": 60, "color": RED, "speed": 6, "homing": True},
            "plasma": {"damage": 50, "rate": 45, "color": PURPLE, "speed": 7, "large": True},
            "minigun": {"damage": 5, "rate": 5, "color": GREEN, "speed": 12}
        }

    def update(self, keys, mouse_pos):
        # 鼠标控制方向
        dx = mouse_pos[0] - self.rect.centerx
        dy = mouse_pos[1] - self.rect.centery
        self.angle = math.atan2(dy, dx)
        
        # WASD 移动
        move_x = 0
        move_y = 0
        if keys[pygame.K_w]: move_y -= 1
        if keys[pygame.K_s]: move_y += 1
        if keys[pygame.K_a]: move_x -= 1
        if keys[pygame.K_d]: move_x += 1
        
        # 应用速度加成
        current_speed = self.speed + (self.skills["speed"] * 0.5)
        
        if move_x != 0 or move_y != 0:
            length = math.sqrt(move_x**2 + move_y**2)
            move_x /= length
            move_y /= length
            self.rect.x += move_x * current_speed
            self.rect.y += move_y * current_speed

        # 边界检查
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # 射击
        if self.fire_timer > 0:
            self.fire_timer -= 1
        
        if keys[pygame.K_SPACE]:
            self.shoot()

        # 护盾恢复
        if self.shield < self.max_shield + (self.skills["shield"] * 20):
            self.shield_regen_timer += 1
            if self.shield_regen_timer >= 60: # 每秒恢复一次
                self.shield += self.shield_regen_rate + (self.skills["shield"] * 0.2)
                self.shield = min(self.shield, self.max_shield + (self.skills["shield"] * 20))
                self.shield_regen_timer = 0

        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    def shoot(self):
        if self.fire_timer > 0:
            return
        
        weapon_stats = self.weapons[self.weapon]
        self.fire_timer = weapon_stats["rate"] - (self.skills["fire_rate"] * 2)
        if self.fire_timer < 2:
            self.fire_timer = 2
            
        damage = weapon_stats["damage"] + (self.skills["damage"] * 2)
        color = weapon_stats["color"]
        speed = weapon_stats["speed"]
        
        # 计算发射角度
        angle = self.angle
        
        if weapon_stats.get("homing"):
            # 导弹发射，稍后在Game中处理追踪
            b = Missile(self.rect.centerx, self.rect.centery, math.cos(angle)*speed, math.sin(angle)*speed, damage, color, self)
            game.add_bullet(b)
        elif weapon_stats.get("count", 1) > 1:
            # 散射
            spread_angle = 0.3
            for i in range(weapon_stats["count"]):
                a = angle - spread_angle + (spread_angle * 2 * (i / (weapon_stats["count"] - 1)))
                vx = math.cos(a) * speed
                vy = math.sin(a) * speed
                game.add_bullet(Bullet(self.rect.centerx, self.rect.centery, vx, vy, damage, color))
        elif weapon_stats.get("beam"):
            # 激光是瞬间伤害，但在本系统中简化为高速子弹或特殊处理
            # 这里简化为快速子弹流
            for i in range(5): # 激光束由多个小子弹组成
                offset = (i - 2) * 5
                nx = math.cos(angle + math.pi/2) * offset
                ny = math.sin(angle + math.pi/2) * offset
                b = Bullet(self.rect.centerx + nx, self.rect.centery + ny, 
                           math.cos(angle)*speed, math.sin(angle)*speed, damage/5, color)
                game.add_bullet(b)
        else:
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = 8 if weapon_stats.get("large") else 4
            b = Bullet(self.rect.centerx, self.rect.centery, vx, vy, damage, color)
            b.width = size
            b.height = size
            b.image = pygame.Surface((size, size))
            b.image.fill(color)
            game.add_bullet(b)

    def gain_exp(self, amount):
        self.experience += amount
        req = self.level * 100
        if self.experience >= req:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.experience = 0
        self.skill_points += 1
        # 播放升级音效
        game.sound_manager.play_sound("levelup")

    def apply_skill(self, skill_name):
        if self.skill_points > 0 and skill_name in self.skills:
            self.skills[skill_name] += 1
            self.skill_points -= 1
            # 根据技能调整属性
            if skill_name == "speed":
                self.speed += 0.5
            elif skill_name == "damage":
                pass # 在射击时计算
            elif skill_name == "shield":
                self.max_shield += 20
                self.shield = self.max_shield

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield # 扣除剩余伤害
                self.shield = 0
        else:
            self.health -= amount
        
        game.sound_manager.play_sound("hit")
        game.particles.emit(self.rect.centerx, self.rect.centery, WHITE, 5)
        
        self.invincible_timer = 30
        
        if self.health <= 0:
            self.dead = True
            game.game_over()

    def draw(self, screen):
        if self.invincible_timer > 0 and self.invincible_timer % 4 < 2:
            return # 闪烁效果
            
        # 绘制飞船三角形
        center = self.rect.center
        size = 20
        points = [
            (center[0] + math.cos(self.angle) * size, center[1] + math.sin(self.angle) * size),
            (center[0] + math.cos(self.angle + 2.5) * size, center[1] + math.sin(self.angle + 2.5) * size),
            (center[0] + math.cos(self.angle - 2.5) * size, center[1] + math.sin(self.angle - 2.5) * size)
        ]
        pygame.draw.polygon(screen, BLUE, points)
        
        # 引擎尾焰
        if random.random() > 0.5:
            game.particles.emit(
                center[0] - math.cos(self.angle) * 15,
                center[1] - math.sin(self.angle) * 15,
                ORANGE, 1, (5, 10), (2, 4)
            )

# ================= 敌人系统 (要求2, 13) =================
class Enemy(Entity):
    def __init__(self, x, y, enemy_type, wave_difficulty=1):
        super().__init__(x, y, 30, 30, RED)
        self.enemy_type = enemy_type
        self.wave_difficulty = wave_difficulty
        self.speed = 2
        self.fire_rate = 60
        self.fire_timer = random.randint(0, self.fire_rate)
        self.hp_multiplier = 1 + (wave_difficulty * 0.2)
        self.exp_value = 10 * wave_difficulty
        
        self.setup_type()

    def setup_type(self):
        types = {
            "basic": {"color": RED, "hp": 20, "speed": 2, "fire_rate": 60, "damage": 10},
            "fast": {"color": ORANGE, "hp": 10, "speed": 4, "fire_rate": 40, "damage": 5},
            "tank": {"color": DARK_GRAY, "hp": 60, "speed": 1, "fire_rate": 90, "damage": 20},
            "sniper": {"color": PURPLE, "hp": 30, "speed": 1.5, "fire_rate": 120, "damage": 30},
            "bomber": {"color": GREEN, "hp": 40, "speed": 2.5, "fire_rate": 0, "damage": 50, "explosive": True}
        }
        t = types.get(self.enemy_type, types["basic"])
        self.color = t["color"]
        self.image.fill(self.color)
        self.health = int(t["hp"] * self.hp_multiplier)
        self.max_health = self.health
        self.speed = t["speed"]
        self.fire_rate = t["fire_rate"]
        self.damage = t["damage"]
        self.explosive = t.get("explosive", False)
        self.exp_value = int(10 * self.wave_difficulty * (1 + t["hp"]/20))

    def update(self, player):
        if self.dead: return

        # 简单的AI行为
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist > 0:
            dx /= dist
            dy /= dist
            
        # 不同敌人行为
        if self.enemy_type == "basic":
            self.rect.x += dx * self.speed
            self.rect.y += dy * self.speed
        elif self.enemy_type == "fast":
            self.rect.x += dx * self.speed
            self.rect.y += dy * self.speed
        elif self.enemy_type == "tank":
            self.rect.x += dx * self.speed
            self.rect.y += dy * self.speed
        elif self.enemy_type == "sniper":
            # 保持距离
            if dist < 300:
                self.rect.x -= dx * self.speed
                self.rect.y -= dy * self.speed
            else:
                self.rect.x += dx * self.speed
                self.rect.y += dy * self.speed
        elif self.enemy_type == "bomber":
            self.rect.x += dx * self.speed
            self.rect.y += dy * self.speed

        # 射击
        if self.fire_rate > 0:
            self.fire_timer -= 1
            if self.fire_timer <= 0:
                self.fire_timer = self.fire_rate
                angle = math.atan2(dy, dx)
                vx = math.cos(angle) * 4
                vy = math.sin(angle) * 4
                b = Bullet(self.rect.centerx, self.rect.centery, vx, vy, self.damage, self.color, owner="enemy")
                game.add_bullet(b)
                if self.enemy_type == "sniper":
                    b.speed = 8 # 狙击子弹更快

        # 碰撞检测
        if self.rect.colliderect(player.rect):
            if self.explosive:
                self.explode()
                player.take_damage(self.damage)
            else:
                player.take_damage(10)
                self.take_damage(10)

    def explode(self):
        game.particles.emit(self.rect.centerx, self.rect.centery, ORANGE, 30, (10, 30), (3, 6))
        game.sound_manager.play_sound("explosion")
        # 范围伤害
        for enemy in game.enemies:
            if enemy != self and not enemy.dead:
                dist = math.hypot(enemy.rect.centerx - self.rect.centerx, enemy.rect.centery - self.rect.centery)
                if dist < 100:
                    enemy.take_damage(20)
        self.dead = True

class Boss(Entity):
    def __init__(self, x, y, wave_num):
        super().__init__(x, y, 100, 100, PURPLE)
        self.phase = 1
        self.max_phases = 3
        self.hp_multiplier = 1 + (wave_num * 0.5)
        self.health = 500 * self.hp_multiplier
        self.max_health = self.health
        self.attack_pattern = 0
        self.timer = 0
        self.move_speed = 2
        self.target_y = 100
        self.wave_num = wave_num

    def update(self, player):
        self.timer += 1
        
        # 移动模式
        if self.phase == 1:
            # 缓慢接近
            if self.rect.centery < self.target_y:
                self.rect.y += self.move_speed
            else:
                self.rect.y -= self.move_speed
            
            # 阶段转换
            if self.health < self.max_health * 0.66:
                self.phase = 2
                self.sound_manager.play_sound("boss_phase")
                
            if self.health < self.max_health * 0.33:
                self.phase = 3
                self.sound_manager.play_sound("boss_phase")

        # 攻击模式
        if self.timer % 60 == 0:
            self.attack(player)
        
        if self.timer % 120 == 0:
            self.attack_pattern = (self.attack_pattern + 1) % 3

    def attack(self, player):
        angle = math.atan2(player.rect.centery - self.rect.centery, player.rect.centerx - self.rect.centerx)
        
        if self.phase == 1:
            # 单发激光
            vx = math.cos(angle) * 5
            vy = math.sin(angle) * 5
            b = Bullet(self.rect.centerx, self.rect.centery, vx, vy, 20, RED, owner="enemy")
            game.add_bullet(b)
            
        elif self.phase == 2:
            # 扇形弹幕
            for i in range(-2, 3):
                a = angle + i * 0.2
                vx = math.cos(a) * 5
                vy = math.sin(a) * 5
                b = Bullet(self.rect.centerx, self.rect.centery, vx, vy, 15, ORANGE, owner="enemy")
                game.add_bullet(b)
                
        elif self.phase == 3:
            # 环形弹幕
            for i in range(12):
                a = (i / 12) * math.pi * 2
                vx = math.cos(a) * 4
                vy = math.sin(a) * 4
                b = Bullet(self.rect.centerx, self.rect.centery, vx, vy, 10, YELLOW, owner="enemy")
                game.add_bullet(b)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # 绘制血条
        pygame.draw.rect(screen, RED, (self.rect.x, self.rect.y - 20, self.rect.width, 10))
        pygame.draw.rect(screen, GREEN, (self.rect.x, self.rect.y - 20, self.rect.width * (self.health / self.max_health), 10))
        # 绘制阶段文字
        font = pygame.font.Font(None, 36)
        text = font.render(f"Phase {self.phase}", True, WHITE)
        screen.blit(text, (self.rect.x, self.rect.y - 50))

# ================= 道具系统 (要求6) =================
class PowerUp(Entity):
    def __init__(self, x, y, power_type):
        super().__init__(x, y, 20, 20, WHITE)
        self.power_type = power_type
        self.vy = 2
        self.setup_type()

    def setup_type(self):
        types = {
            "health": {"color": GREEN, "effect": "heal"},
            "shield": {"color": BLUE, "effect": "shield"},
            "speed": {"color": CYAN, "effect": "speed"},
            "damage": {"color": RED, "effect": "damage"},
            "bomb": {"color": ORANGE, "effect": "bomb"},
            "spread": {"color": PURPLE, "effect": "spread"},
            "missile": {"color": YELLOW, "effect": "missile"},
            "laser": {"color": WHITE, "effect": "laser"}
        }
        t = types.get(self.power_type, types["health"])
        self.color = t["color"]
        self.image.fill(self.color)
        self.effect = t["effect"]

    def update(self):
        self.rect.y += self.vy
        if self.rect.y > SCREEN_HEIGHT:
            self.dead = True

    def apply(self, player):
        if self.effect == "heal":
            player.health = min(player.health + 30, player.max_health)
        elif self.effect == "shield":
            player.shield = player.max_shield
        elif self.effect == "speed":
            player.skills["speed"] += 1
        elif self.effect == "damage":
            player.skills["damage"] += 1
        elif self.effect == "bomb":
            game.trigger_bomb()
        elif self.effect in ["spread", "missile", "laser"]:
            player.weapon = self.effect

class Missile(Projectile):
    def __init__(self, x, y, vx, vy, damage, color, owner_entity):
        super().__init__(x, y, vx, vy, damage, color, 6, "player")
        self.owner = owner_entity
        self.turn_speed = 0.05

    def update(self):
        # 追踪逻辑
        if self.owner and not self.owner.dead:
            dx = self.owner.rect.centerx - self.rect.centerx
            dy = self.owner.rect.centery - self.rect.centery
            angle = math.atan2(dy, dx)
            current_angle = math.atan2(self.vy, self.vx)
            
            # 平滑转向
            diff = angle - current_angle
            # 规范化角度差
            while diff > math.pi: diff -= 2 * math.pi
            while diff < -math.pi: diff += 2 * math.pi
            
            new_angle = current_angle + diff * self.turn_speed
            speed = math.sqrt(self.vx**2 + self.vy**2)
            self.vx = math.cos(new_angle) * speed
            self.vy = math.sin(new_angle) * speed
            
            self.rect.x += self.vx
            self.rect.y += self.vy
            self.lifespan -= 1
            if self.lifespan <= 0 or not self.rect.colliderect(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)):
                self.dead = True

# ================= 成就系统 (要求12) =================
class AchievementManager:
    def __init__(self):
        self.achievements = {
            "first_kill": {"name": "First Blood", "desc": "Kill your first enemy", "unlocked": False, "check": lambda g: g.stats["kills"] >= 1},
            "level_5": {"name": "Rookie", "desc": "Reach Level 5", "unlocked": False, "check": lambda g: g.player.level >= 5},
            "boss_kill": {"name": "Boss Slayer", "desc": "Kill a Boss", "unlocked": False, "check": lambda g: g.stats["boss_kills"] >= 1},
            "wave_5": {"name": "Survivor", "desc": "Complete Wave 5", "unlocked": False, "check": lambda g: g.wave >= 5},
            "weapon_spread": {"name": "Shotgun", "desc": "Use Spread Gun", "unlocked": False, "check": lambda g: g.player.weapon == "spread"},
            "weapon_laser": {"name": "Laser Eyes", "desc": "Use Laser Gun", "unlocked": False, "check": lambda g: g.player.weapon == "laser"},
            "weapon_missile": {"name": "Lock On", "desc": "Use Missile Gun", "unlocked": False, "check": lambda g: g.player.weapon == "missile"},
            "no_damage": {"name": "Untouchable", "desc": "Kill 100 enemies without dying", "unlocked": False, "check": lambda g: g.stats["kills"] >= 100 and g.stats["deaths"] == 0},
            "bomb_user": {"name": "Demolition", "desc": "Use a Bomb", "unlocked": False, "check": lambda g: g.stats["bombs_used"] >= 1},
            "max_level": {"name": "Godlike", "desc": "Reach Level 10", "unlocked": False, "check": lambda g: g.player.level >= 10}
        }
        self.unlocked_list = []

    def check(self, game):
        for key, ach in self.achievements.items():
            if not ach["unlocked"] and ach["check"](game):
                ach["unlocked"] = True
                self.unlocked_list.append(ach["name"])
                game.sound_manager.play_sound("achievement")
                # 显示通知
                game.show_notification(f"Achievement Unlocked: {ach['name']}")

    def draw(self, screen):
        font = pygame.font.Font(None, 24)
        y = 10
        for ach in self.achievements.values():
            color = GREEN if ach["unlocked"] else GRAY
            text = font.render(f"{'[X]' if ach['unlocked'] else '[ ]'} {ach['name']}", True, color)
            screen.blit(text, (SCREEN_WIDTH - 200, y))
            y += 25

# ================= 存档系统 (要求11) =================
class SaveSystem:
    SAVE_FILE = "savegame.json"

    @staticmethod
    def save(game):
        data = {
            "player_level": game.player.level,
            "player_exp": game.player.experience,
            "player_skills": game.player.skills,
            "player_weapon": game.player.weapon,
            "wave": game.wave,
            "score": game.score,
            "stats": game.stats
        }
        with open(SaveSystem.SAVE_FILE, 'w') as f:
            json.dump(data, f)

    @staticmethod
    def load():
        if not os.path.exists(SaveSystem.SAVE_FILE):
            return None
        try:
            with open(SaveSystem.SAVE_FILE, 'r') as f:
                return json.load(f)
        except:
            return None

# ================= 游戏主类 (核心逻辑) =================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter Ultimate")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = STATE_MENU
        
        # 管理器
        self.sound_manager = SoundManager()
        self.particles = ParticleSystem()
        self.achievement_manager = AchievementManager()
        
        # 实体容器
        self.player = None
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.boss = None
        
        # 游戏变量
        self.score = 0
        self.wave = 1
        self.scene = SCENE_SPACE
        self.wave_timer = 0
        self.enemies_to_spawn = 0
        self.spawn_timer = 0
        self.notification_text = ""
        self.notification_timer = 0
        
        # 统计
        self.stats = {
            "kills": 0,
            "deaths": 0,
            "boss_kills": 0,
            "bombs_used": 0
        }
        
        # 字体
        self.font_large = pygame.font.Font(None, 74)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)

    def start_new_game(self):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.bullets.empty()
        self.enemies.empty()
        self.powerups.empty()
        self.boss = None
        self.score = 0
        self.wave = 1
        self.scene = SCENE_SPACE
        self.start_wave()
        self.state = STATE_PLAYING
        self.sound_manager.play_music("music.mp3") # 假设存在

    def start_wave(self):
        self.enemies_to_spawn = 5 + (self.wave * 2)
        self.spawn_timer = 0
        self.wave_timer = 0
        
        # 检查是否出现Boss
        if self.wave % 5 == 0:
            self.spawn_boss()

    def spawn_boss(self):
        self.boss = Boss(SCREEN_WIDTH // 2, -150, self.wave)
        self.enemies.add(self.boss)
        self.show_notification("BOSS APPROACHING!")

    def spawn_enemy(self):
        if self.enemies_to_spawn <= 0:
            return
        
        x = random.randint(0, SCREEN_WIDTH - 30)
        y = -30
        types = ["basic", "fast", "tank", "sniper", "bomber"]
        # 难度越高，高级敌人比例越高
        if self.wave > 3:
            types.append("fast")
            types.append("tank")
        if self.wave > 5:
            types.append("sniper")
            types.append("bomber")
            
        etype = random.choice(types)
        enemy = Enemy(x, y, etype, self.wave)
        self.enemies.add(enemy)
        self.enemies_to_spawn -= 1

    def add_bullet(self, bullet):
        self.bullets.add(bullet)

    def trigger_bomb(self):
        self.stats["bombs_used"] += 1
        self.achievement_manager.check(self)
        self.sound_manager.play_sound("explosion")
        self.particles.emit(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, WHITE, 100, (30, 60), (5, 10))
        
        # 清除所有敌人和子弹
        for e in self.enemies:
            e.take_damage(1000)
            if e.dead:
                self.player.gain_exp(e.exp_value)
                self.score += e.exp_value
                self.stats["kills"] += 1
                if isinstance(e, Boss):
                    self.stats["boss_kills"] += 1
                # 掉落道具
                if random.random() < 0.3:
                    ptype = random.choice(["health", "shield", "speed", "damage", "bomb", "spread", "missile", "laser"])
                    self.powerups.add(PowerUp(e.rect.centerx, e.rect.centery, ptype))
        
        self.enemies.empty()
        self.bullets.empty()
        self.boss = None
        self.show_notification("BOMB DETONATED!")

    def update(self):
        if self.state != STATE_PLAYING:
            return

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        # 玩家更新
        self.player.update(keys, mouse_pos)

        # 子弹更新
        for b in self.bullets:
            b.update()
        
        # 碰撞检测：子弹 vs 敌人
        hits = pygame.sprite.groupcollide(self.bullets, self.enemies, False, True)
        for bullet, enemies in hits.items():
            for enemy in enemies:
                enemy.take_damage(bullet.damage)
                self.particles.emit(enemy.rect.centerx, enemy.rect.centery, enemy.color, 5)
                if enemy.dead:
                    self.player.gain_exp(enemy.exp_value)
                    self.score += enemy.exp_value
                    self.stats["kills"] += 1
                    if isinstance(enemy, Boss):
                        self.stats["boss_kills"] += 1
                        self.boss = None
                    # 掉落道具
                    if random.random() < 0.2:
                        ptype = random.choice(["health", "shield", "speed", "damage", "bomb", "spread", "missile", "laser"])
                        self.powerups.add(PowerUp(enemy.rect.centerx, enemy.rect.centery, ptype))
        
        # 碰撞检测：子弹 vs 玩家
        hits = pygame.sprite.groupcollide(self.bullets, pygame.sprite.Group([self.player]), False, False)
        for bullet, player in hits.items():
            if bullet.owner == "enemy":
                self.player.take_damage(bullet.damage)
                bullet.dead = True

        # 敌人更新
        for e in self.enemies:
            e.update(self.player)

        # 道具更新
        for p in self.powerups:
            p.update()
            if p.rect.colliderect(self.player.rect):
                p.apply(self.player)
                p.dead = True
                self.sound_manager.play_sound("powerup")

        # 清理死亡实体
        self.bullets.remove([b for b in self.bullets if b.dead])
        self.enemies.remove([e for e in self.enemies if e.dead])
        self.powerups.remove([p for p in self.powerups if p.dead])

        # 波次管理
        if self.boss is None and self.enemies_to_spawn == 0 and len(self.enemies) == 0:
            self.wave_timer += 1
            if self.wave_timer > 120: # 2秒间隔
                self.wave += 1
                self.start_wave()
                self.show_notification(f"WAVE {self.wave}")

        # 粒子更新
        self.particles.update()

        # 成就检查
        self.achievement_manager.check(self)

        # 通知计时
        if self.notification_timer > 0:
            self.notification_timer -= 1

    def draw(self):
        self.screen.fill(BLACK)
        
        # 绘制背景
        if self.scene == SCENE_SPACE:
            # 简单的星星背景
            for i in range(50):
                x = (i * 137) % SCREEN_WIDTH
                y = (i * 241 + self.wave_timer) % SCREEN_HEIGHT
                pygame.draw.circle(self.screen, WHITE, (x, y), 1)
        elif self.scene == SCENE_ASTEROID_FIELD:
            pass # 简化
        elif self.scene == SCENE_NEON_CITY:
            pygame.draw.rect(self.screen, (20, 20, 40), (0, SCREEN_HEIGHT-50, SCREEN_WIDTH, 50))
            for i in range(10):
                pygame.draw.rect(self.screen, PURPLE, (i*100, SCREEN_HEIGHT-100- (i%3)*30, 50, 100+(i%3)*30))

        if self.state == STATE_PLAYING:
            # 绘制实体
            self.player.draw(self.screen)
            self.bullets.draw(self.screen)
            self.enemies.draw(self.screen)
            self.powerups.draw(self.screen)
            self.particles.draw(self.screen)
            
            # HUD
            self.draw_hud()

        elif self.state == STATE_MENU:
            self.draw_menu()
        elif self.state == STATE_PAUSED:
            self.draw_pause()
        elif self.state == STATE_GAME_OVER:
            self.draw_game_over()

        pygame.display.flip()

    def draw_hud(self):
        # 分数
        text = self.font_medium.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(text, (10, 10))
        
        # 波次
        text = self.font_medium.render(f"Wave: {self.wave}", True, WHITE)
        self.screen.blit(text, (10, 50))
        
        # 等级
        text = self.font_small.render(f"Lvl: {self.player.level} (EXP: {self.player.experience})", True, CYAN)
        self.screen.blit(text, (10, 90))
        
        # 技能点
        if self.player.skill_points > 0:
            text = self.font_small.render(f"Skill Points: {self.player.skill_points} (Press 'S' to open)", True, YELLOW)
            self.screen.blit(text, (10, 110))

        # 武器
        text = self.font_small.render(f"Weapon: {self.player.weapon.upper()}", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH - 150, 10))
        
        # 成就
        self.achievement_manager.draw(self.screen)

        # 通知
        if self.notification_timer > 0:
            text = self.font_large.render(self.notification_text, True, YELLOW)
            rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
            self.screen.blit(text, rect)

    def draw_menu(self):
        self.screen.fill(BLACK)
        title = self.font_large.render("SPACE SHOOTER", True, BLUE)
        rect = title.get_rect(center=(SCREEN_WIDTH//2, 200))
        self.screen.blit(title, rect)
        
        start_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, 400, 200, 50)
        pygame.draw.rect(self.screen, GREEN, start_btn)
        text = self.font_medium.render("START GAME", True, BLACK)
        self.screen.blit(text, text.get_rect(center=start_btn.center))
        
        load_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, 500, 200, 50)
        pygame.draw.rect(self.screen, GRAY, load_btn)
        text = self.font_medium.render("LOAD GAME", True, BLACK)
        self.screen.blit(text, text.get_rect(center=load_btn.center))

        # 检查鼠标点击
        mouse = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            if start_btn.collidepoint(mouse):
                self.start_new_game()
            elif load_btn.collidepoint(mouse):
                data = SaveSystem.load()
                if data:
                    self.start_new_game()
                    self.player.level = data["player_level"]
                    self.player.experience = data["player_exp"]
                    self.player.skills = data["player_skills"]
                    self.player.weapon = data["player_weapon"]
                    self.wave = data["wave"]
                    self.score = data["score"]
                    self.stats = data["stats"]
                    self.start_wave()
                    self.state = STATE_PLAYING
                else:
                    self.show_notification("No Save Found!")

    def draw_pause(self):
        self.screen.fill((0, 0, 0, 128))
        title = self.font_large.render("PAUSED", True, WHITE)
        rect = title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
        self.screen.blit(title, rect)
        
        resume_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2, 200, 50)
        pygame.draw.rect(self.screen, BLUE, resume_btn)
        text = self.font_medium.render("RESUME", True, BLACK)
        self.screen.blit(text, text.get_rect(center=resume_btn.center))
        
        quit_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 60, 200, 50)
        pygame.draw.rect(self.screen, RED, quit_btn)
        text = self.font_medium.render("QUIT", True, BLACK)
        self.screen.blit(text, text.get_rect(center=quit_btn.center))
        
        mouse = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            if resume_btn.collidepoint(mouse):
                self.state = STATE_PLAYING
            if quit_btn.collidepoint(mouse):
                self.state = STATE_MENU

    def draw_game_over(self):
        self.screen.fill(BLACK)
        title = self.font_large.render("GAME OVER", True, RED)
        rect = title.get_rect(center=(SCREEN_WIDTH//2, 200))
        self.screen.blit(title, rect)
        
        score_text = self.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH//2, 300)))
        
        restart_btn = pygame.Rect(SCREEN_WIDTH//2 - 100, 400, 200, 50)
        pygame.draw.rect(self.screen, GREEN, restart_btn)
        text = self.font_medium.render("RESTART", True, BLACK)
        self.screen.blit(text, text.get_rect(center=restart_btn.center))
        
        mouse = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            if restart_btn.collidepoint(mouse):
                self.start_new_game()

    def game_over(self):
        self.state = STATE_GAME_OVER
        self.stats["deaths"] += 1
        self.sound_manager.stop_music()

    def show_notification(self, text):
        self.notification_text = text
        self.notification_timer = 120

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.KEYDOWN:
                    if self.state == STATE_PLAYING:
                        if event.key == pygame.K_ESCAPE:
                            self.state = STATE_PAUSED
                        if event.key == pygame.K_s:
                            # 打开技能菜单简化版：直接加点
                            if self.player.skill_points > 0:
                                # 循环加点
                                skills = ["damage", "speed", "shield", "fire_rate"]
                                for s in skills:
                                    if self.player.skill_points > 0:
                                        self.player.apply_skill(s)
                                self.show_notification("Skills Upgraded!")
                        if event.key == pygame.K_s: # 保存
                             SaveSystem.save(self)
                             self.show_notification("Game Saved!")
                    elif self.state == STATE_PAUSED:
                        if event.key == pygame.K_ESCAPE:
                            self.state = STATE_PLAYING
                    elif self.state == STATE_GAME_OVER:
                        if event.key == pygame.K_RETURN:
                            self.start_new_game()

            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

# ================= 入口 =================
if __name__ == "__main__":
    # 创建游戏实例
    game = Game()
    
    # 尝试加载音效（如果文件存在）
    # 在实际使用中，请确保目录中有 music.mp3, explosion.wav, hit.wav, levelup.wav, boss_phase.wav, powerup.wav, achievement.wav
    # 这里为了代码可运行性，我们假设这些文件不存在，SoundManager会静默处理
    
    game.run()
