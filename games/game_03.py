import pygame
import sys
import random
import math
import json
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# 初始化Pygame
pygame.init()

# =================常量定义=================
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
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)

# 游戏状态枚举
class GameState(Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3
    VICTORY = 4
    SHOP = 5

# 敌人类型枚举
class EnemyType(Enum):
    DRONE = 0      # 基础，直线移动
    BOMBER = 1     # 投弹，较慢
    SPEEDER = 2    # 快速，Z字形移动
    TANK = 3       # 高血量，发射弹幕
    ELITE = 4      # 精英，混合行为
    BOSS = 100     # Boss

# 武器类型枚举
class WeaponType(Enum):
    BLASTER = 0    # 基础激光
    SHOTGUN = 1    # 散弹
    MISSILE = 2    # 追踪导弹
    LASER_BEAM = 3 # 持续激光
    PLASMA = 4     # 穿透弹
    RAPID = 5      # 高速连发

# 道具类型枚举
class PowerUpType(Enum):
    SHIELD = 0
    SPEED = 1
    BOMB = 2
    HEALTH = 3
    EXP_BONUS = 4
    WEAPON_UPGRADE = 5
    MAGNET = 6
    FREEZE = 7

# 场景枚举
class SceneType(Enum):
    SPACE = 0
    ASTEROID_FIELD = 1
    NEBULA = 2

# =================数据结构=================
@dataclass
class SaveData:
    high_score: int = 0
    level: int = 1
    wave: int = 1
    xp: int = 0
    level_xp_needed: int = 100
    skills: Dict[str, int] = field(default_factory=lambda: {"damage": 0, "speed": 0, "health": 0})
    unlocked_weapons: List[int] = field(default_factory=lambda: [0])
    current_weapon: int = 0
    achievements: List[str] = field(default_factory=list)
    scene: int = 0
    boss_defeated: bool = False

# =================音效管理器=================
class SoundManager:
    def __init__(self):
        self.sounds = {}
        # 在实际项目中，这里应该加载 .wav 或 .ogg 文件
        # 为了演示可运行性，我们模拟音效，实际使用时取消注释并加载文件
        try:
            self.sounds['shoot'] = pygame.mixer.Sound('assets/shoot.wav')
            self.sounds['explosion'] = pygame.mixer.Sound('assets/explosion.wav')
            self.sounds['powerup'] = pygame.mixer.Sound('assets/powerup.wav')
            self.sounds['hit'] = pygame.mixer.Sound('assets/hit.wav')
            self.sounds['boss_enter'] = pygame.mixer.Sound('assets/boss_enter.wav')
        except Exception as e:
            print(f"Warning: Sound files not found. Audio disabled. Error: {e}")
            self.sounds = {}

    def play(self, sound_name: str):
        if sound_name in self.sounds:
            self.sounds[sound_name].play()

    def stop(self):
        pygame.mixer.stop()

# =================粒子系统=================
class Particle:
    def __init__(self, x, y, color, speed, size, life):
        self.x = x
        self.y = y
        self.color = color
        self.speed_x = speed * math.cos(random.uniform(0, 2 * math.pi))
        self.speed_y = speed * math.sin(random.uniform(0, 2 * math.pi))
        self.size = size
        self.life = life
        self.max_life = life
        self.active = True

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.life -= 1
        self.size *= 0.95
        if self.life <= 0:
            self.active = False

    def draw(self, screen):
        alpha = int(255 * (self.life / self.max_life))
        # 简单绘制圆形粒子
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(max(1, self.size)))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=10, speed_range=(1, 3), size_range=(2, 5), life_range=(20, 40)):
        for _ in range(count):
            speed = random.uniform(*speed_range)
            size = random.uniform(*size_range)
            life = random.randint(*life_range)
            self.particles.append(Particle(x, y, color, speed, size, life))

    def update(self):
        self.particles = [p for p in self.particles if p.active]
        for p in self.particles:
            p.update()

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# =================武器系统=================
class Projectile:
    def __init__(self, x, y, angle, speed, damage, weapon_type, is_player=True):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.damage = damage
        self.weapon_type = weapon_type
        self.is_player = is_player
        self.active = True
        self.radius = 3
        
        # 特定武器行为
        if weapon_type == WeaponType.MISSILE:
            self.tracking = True
            self.target = None
        elif weapon_type == WeaponType.LASER_BEAM:
            self.active = True # 持续存在

    def update(self, target_player=None, target_enemies=None):
        if self.tracking and self.weapon_type == WeaponType.MISSILE:
            # 简单的追踪逻辑
            if self.is_player and target_enemies:
                min_dist = float('inf')
                for e in target_enemies:
                    dist = math.hypot(e.x - self.x, e.y - self.y)
                    if dist < min_dist:
                        min_dist = dist
                        self.target = e
            elif not self.is_player and target_player:
                self.target = target_player

            if self.target:
                desired_angle = math.atan2(self.target.y - self.y, self.target.x - self.x)
                # 平滑转向
                diff = desired_angle - self.angle
                while diff < -math.pi: diff += 2 * math.pi
                while diff > math.pi: diff -= 2 * math.pi
                self.angle += diff * 0.1
                self.speed += 0.1 # 导弹加速

        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed

        # 边界检查
        if (self.x < 0 or self.x > SCREEN_WIDTH or 
            self.y < 0 or self.y > SCREEN_HEIGHT):
            self.active = False

    def draw(self, screen):
        color = WHITE
        if self.is_player:
            if self.weapon_type == WeaponType.SHOTGUN: color = YELLOW
            elif self.weapon_type == WeaponType.PLASMA: color = CYAN
            elif self.weapon_type == WeaponType.MISSILE: color = MAGENTA
            else: color = BLUE
        else:
            color = RED

        if self.weapon_type == WeaponType.LASER_BEAM:
            pygame.draw.line(screen, color, (self.x, self.y), 
                             (self.x + math.cos(self.angle)*50, self.y + math.sin(self.angle)*50), 2)
        else:
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)

class Weapon:
    def __init__(self, weapon_type: WeaponType, damage_mult=1.0, fire_rate_mult=1.0):
        self.type = weapon_type
        self.damage_mult = damage_mult
        self.fire_rate_mult = fire_rate_mult
        self.cooldown = 0
        self.max_cooldown = self.get_max_cooldown()

    def get_max_cooldown(self) -> int:
        base_cooldowns = {
            WeaponType.BLASTER: 15,
            WeaponType.SHOTGUN: 30,
            WeaponType.MISSILE: 60,
            WeaponType.LASER_BEAM: 5,
            WeaponType.PLASMA: 20,
            WeaponType.RAPID: 5
        }
        return int(base_cooldowns.get(self.type, 15) * self.fire_rate_mult)

    def can_fire(self) -> bool:
        return self.cooldown <= 0

    def fire(self) -> List[Projectile]:
        self.cooldown = self.max_cooldown
        projectiles = []
        
        # 根据武器类型生成不同的弹道
        if self.type == WeaponType.SHOTGUN:
            for i in range(-2, 3):
                angle = math.radians(i * 10)
                # 假设玩家朝向是0度(向右)，这里简化处理，实际需结合玩家角度
                # 为简化，假设玩家始终向右射击，角度偏移
                p = Projectile(0, 0, angle, 10, 10 * self.damage_mult, self.type, True)
                projectiles.append(p)
        elif self.type == WeaponType.LASER_BEAM:
            # 激光是持续的，这里只生成一个长条对象，实际由Player类处理持续伤害
            p = Projectile(0, 0, 0, 20, 2 * self.damage_mult, self.type, True)
            projectiles.append(p)
        else:
            # 单发武器
            p = Projectile(0, 0, 0, 12, 15 * self.damage_mult, self.type, True)
            projectiles.append(p)
            
        return projectiles

# =================实体基类=================
class Entity:
    def __init__(self, x, y, width, height, health):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.health = health
        self.max_health = health
        self.active = True
        self.rect = pygame.Rect(x, y, width, height)

    def update(self):
        self.rect.x = self.x
        self.rect.y = self.y

    def draw(self, screen):
        pass # 子类实现

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.active = False

    def get_center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)

# =================玩家类=================
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40, 100)
        self.speed = 5
        self.weapon = Weapon(WeaponType.BLASTER)
        self.projectiles = []
        self.explosion_particles = ParticleSystem()
        self.engine_particles = ParticleSystem()
        self.shield = 0
        self.invulnerable = 0
        self.angle = 0 # 鼠标角度
        
        # 技能加成
        self.skill_damage = 1.0
        self.skill_speed = 1.0

    def update(self, keys, mouse_pos, enemies):
        self.update_rect()
        
        # 移动
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        
        # 归一化向量
        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length
        
        self.x += dx * self.speed * self.skill_speed
        self.y += dy * self.speed * self.skill_speed

        # 边界限制
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
        self.y = max(0, min(SCREEN_HEIGHT - self.height, self.y))

        # 鼠标角度
        mx, my = mouse_pos
        self.angle = math.atan2(my - (self.y + self.height/2), mx - (self.x + self.width/2))

        # 引擎尾焰
        self.engine_particles.emit(self.x + self.width/2, self.y + self.height, 
                                   (0, 100, 255), 2, (1, 2), (2, 4), (10, 20))

        # 冷却更新
        if self.weapon.cooldown > 0:
            self.weapon.cooldown -= 1
        
        if self.invulnerable > 0:
            self.invulnerable -= 1

        # 更新子弹
        for p in self.projectiles:
            p.update(target_enemies=enemies)
        self.projectiles = [p for p in self.projectiles if p.active]
        
        # 更新粒子
        self.explosion_particles.update()
        self.engine_particles.update()

    def shoot(self):
        if self.weapon.can_fire():
            projectiles = self.weapon.fire()
            # 调整子弹起始位置到船头
            cx, cy = self.get_center()
            for p in projectiles:
                p.x = cx
                p.y = cy
                p.angle = self.angle
            self.projectiles.extend(projectiles)
            return True
        return False

    def update_rect(self):
        self.rect.x = self.x
        self.rect.y = self.y

    def draw(self, screen):
        # 绘制飞船
        if self.invulnerable > 0 and pygame.time.get_ticks() % 10 < 5:
            return # 闪烁效果
            
        cx, cy = self.get_center()
        
        # 飞船主体
        pygame.draw.polygon(screen, BLUE, [
            (cx + 20, cy),
            (cx - 20, cy - 15),
            (cx - 10, cy),
            (cx - 20, cy + 15)
        ])
        
        # 绘制武器指向
        length = 20
        end_x = cx + math.cos(self.angle) * length
        end_y = cy + math.sin(self.angle) * length
        pygame.draw.line(screen, CYAN, (cx, cy), (end_x, end_y), 2)

        # 绘制子弹
        for p in self.projectiles:
            p.draw(screen)

        # 绘制粒子
        self.explosion_particles.draw(screen)
        self.engine_particles.draw(screen)

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

# =================敌人类=================
class Enemy(Entity):
    def __init__(self, x, y, enemy_type: EnemyType, wave_difficulty=1.0):
        self.enemy_type = enemy_type
        self.wave_difficulty = wave_difficulty
        
        # 根据类型初始化属性
        if enemy_type == EnemyType.DRONE:
            super().__init__(x, y, 30, 30, 20 * wave_difficulty)
            self.speed = 2
            self.score = 10
            self.color = RED
        elif enemy_type == EnemyType.BOMBER:
            super().__init__(x, y, 40, 40, 50 * wave_difficulty)
            self.speed = 1
            self.score = 20
            self.color = DARK_GRAY
            self.shoot_timer = 0
        elif enemy_type == EnemyType.SPEEDER:
            super().__init__(x, y, 25, 25, 15 * wave_difficulty)
            self.speed = 4
            self.score = 15
            self.color = MAGENTA
            self.time = 0
        elif enemy_type == EnemyType.TANK:
            super().__init__(x, y, 50, 50, 100 * wave_difficulty)
            self.speed = 0.5
            self.score = 50
            self.color = GRAY
            self.shoot_timer = 0
        elif enemy_type == EnemyType.ELITE:
            super().__init__(x, y, 35, 35, 80 * wave_difficulty)
            self.speed = 2.5
            self.score = 40
            self.color = YELLOW
            self.shoot_timer = 0
        else:
            super().__init__(x, y, 60, 60, 500 * wave_difficulty)
            self.speed = 1
            self.score = 100
            self.color = WHITE
            self.shoot_timer = 0
            self.phase = 0

        self.projectiles = []
        self.explosion_particles = ParticleSystem()
        self.active = True

    def update(self, player):
        self.update_rect()
        
        # 行为模式
        if self.enemy_type == EnemyType.DRONE:
            self.y += self.speed
        
        elif self.enemy_type == EnemyType.BOMBER:
            self.y += self.speed
            self.shoot_timer += 1
            if self.shoot_timer > 100:
                self.shoot(player)
                self.shoot_timer = 0

        elif self.enemy_type == EnemyType.SPEEDER:
            self.time += 0.1
            self.y += self.speed
            self.x += math.sin(self.time) * 3

        elif self.enemy_type == EnemyType.TANK:
            self.y += self.speed
            self.shoot_timer += 1
            if self.shoot_timer > 150:
                self.shoot_aoe(player)
                self.shoot_timer = 0

        elif self.enemy_type == EnemyType.ELITE:
            # 混合：偶尔追踪
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.x += (dx / dist) * self.speed * 0.5
                self.y += (dy / dist) * self.speed * 0.5
            
            self.shoot_timer += 1
            if self.shoot_timer > 80:
                self.shoot(player)
                self.shoot_timer = 0

        elif self.enemy_type == EnemyType.BOSS:
            self.boss_behavior(player)

        # 子弹更新
        for p in self.projectiles:
            p.update(target_player=player)
        self.projectiles = [p for p in self.projectiles if p.active]

        # 粒子更新
        self.explosion_particles.update()

        # 边界移除
        if self.y > SCREEN_HEIGHT + 50:
            self.active = False

    def boss_behavior(self, player):
        # 简单的Boss阶段
        if self.health < self.max_health * 0.5 and self.phase == 0:
            self.phase = 1
            self.speed *= 1.5
        
        if self.phase == 0:
            self.y += self.speed
            self.x += math.sin(pygame.time.get_ticks() / 500) * 2
        else:
            self.y += self.speed * 0.5
            self.x += math.cos(pygame.time.get_ticks() / 200) * 3
            
        self.shoot_timer += 1
        if self.shoot_timer > 30:
            # 扇形弹幕
            for i in range(-2, 3):
                p = Projectile(self.x, self.y, math.pi/2 + i*0.2, 5, 10, WeaponType.BLASTER, False)
                self.projectiles.append(p)
            self.shoot_timer = 0

    def shoot(self, player):
        angle = math.atan2(player.y - self.y, player.x - self.x)
        p = Projectile(self.x, self.y, angle, 6, 10, WeaponType.BLASTER, False)
        self.projectiles.append(p)

    def shoot_aoe(self, player):
        for i in range(8):
            angle = i * (math.pi / 4)
            p = Projectile(self.x, self.y, angle, 4, 8, WeaponType.BLASTER, False)
            self.projectiles.append(p)

    def take_damage(self, amount):
        super().take_damage(amount)
        if not self.active:
            self.explosion_particles.emit(self.x + self.width/2, self.y + self.height/2, self.color, 20, (2, 5), (3, 6), (30, 60))

    def draw(self, screen):
        self.update_rect()
        pygame.draw.rect(screen, self.color, self.rect)
        
        # 绘制子弹
        for p in self.projectiles:
            p.draw(screen)
        
        # 绘制粒子
        self.explosion_particles.draw(screen)

    def get_center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)

# =================道具系统=================
class PowerUp(Entity):
    def __init__(self, x, y, p_type: PowerUpType):
        super().__init__(x, y, 20, 20, 1)
        self.p_type = p_type
        self.speed = 2
        
        if p_type == PowerUpType.HEALTH:
            self.color = GREEN
        elif p_type == PowerUpType.SHIELD:
            self.color = CYAN
        elif p_type == PowerUpType.BOMB:
            self.color = RED
        elif p_type == PowerUpType.SPEED:
            self.color = YELLOW
        elif p_type == PowerUpType.EXP_BONUS:
            self.color = MAGENTA
        elif p_type == PowerUpType.WEAPON_UPGRADE:
            self.color = WHITE
        elif p_type == PowerUpType.MAGNET:
            self.color = BLUE
        elif p_type == PowerUpType.FREEZE:
            self.color = (100, 200, 255)
        else:
            self.color = GRAY

    def update(self):
        self.y += self.speed
        self.rect.y = self.y
        if self.y > SCREEN_HEIGHT:
            self.active = False

    def draw(self, screen):
        self.update_rect()
        pygame.draw.circle(screen, self.color, (int(self.x + 10), int(self.y + 10)), 10)
        # 简单图标
        pygame.draw.circle(screen, BLACK, (int(self.x + 10), int(self.y + 10)), 8, 1)

# =================成就系统=================
class AchievementManager:
    def __init__(self):
        self.achievements = {
            "first_blood": {"name": "First Blood", "desc": "Kill your first enemy", "unlocked": False},
            "wave_5": {"name": "Survivor", "desc": "Reach Wave 5", "unlocked": False},
            "boss_slayer": {"name": "Boss Slayer", "desc": "Defeat a Boss", "unlocked": False},
            "speed_demon": {"name": "Speed Demon", "desc": "Kill 50 enemies in 1 minute", "unlocked": False},
            "collector": {"name": "Collector", "desc": "Collect 10 powerups", "unlocked": False},
            "sharpshooter": {"name": "Sharpshooter", "desc": "Kill 100 enemies", "unlocked": False},
            "tank": {"name": "Tank", "desc": "Survive with 10% health", "unlocked": False},
            "rich": {"name": "Rich", "desc": "Accumulate 1000 XP", "unlocked": False},
            "weapon_master": {"name": "Weapon Master", "desc": "Unlock all weapons", "unlocked": False},
            "max_level": {"name": "Max Level", "desc": "Reach Level 10", "unlocked": False}
        }
        self.stats = {
            "enemies_killed": 0,
            "powerups_collected": 0,
            "xp_gained": 0,
            "waves_survived": 0,
            "bombs_used": 0
        }

    def check(self, game_state):
        # 检查成就逻辑
        if self.stats["enemies_killed"] >= 1 and not self.achievements["first_blood"]["unlocked"]:
            self.unlock("first_blood")
        
        if self.stats["waves_survived"] >= 5 and not self.achievements["wave_5"]["unlocked"]:
            self.unlock("wave_5")
            
        if self.stats["xp_gained"] >= 1000 and not self.achievements["rich"]["unlocked"]:
            self.unlock("rich")

    def unlock(self, key):
        if key in self.achievements and not self.achievements[key]["unlocked"]:
            self.achievements[key]["unlocked"] = True
            print(f"Achievement Unlocked: {self.achievements[key]['name']}")

    def save(self, save_data):
        save_data.achievements = [k for k, v in self.achievements.items() if v["unlocked"]]
        
    def load(self, save_data):
        for k in save_data.achievements:
            if k in self.achievements:
                self.achievements[k]["unlocked"] = True
        # 重置统计以便重新检查
        self.stats["enemies_killed"] = 0 
        self.stats["xp_gained"] = 0

# =================存档系统=================
class SaveManager:
    FILE_NAME = "save_data.json"

    @staticmethod
    def save(data: SaveData):
        try:
            with open(SaveManager.FILE_NAME, 'w') as f:
                # 转换SaveData为字典
                d = data.__dict__
                json.dump(d, f)
        except Exception as e:
            print(f"Failed to save: {e}")

    @staticmethod
    def load() -> SaveData:
        if os.path.exists(SaveManager.FILE_NAME):
            try:
                with open(SaveManager.FILE_NAME, 'r') as f:
                    d = json.load(f)
                    return SaveData(**d)
            except Exception as e:
                print(f"Failed to load: {e}")
        return SaveData()

# =================UI系统=================
class UI:
    def __init__(self):
        self.font_large = pygame.font.SysFont('arial', 48)
        self.font_medium = pygame.font.SysFont('arial', 24)
        self.font_small = pygame.font.SysFont('arial', 18)

    def draw_text(self, text, x, y, color=WHITE, font=None, center=False):
        if font is None:
            font = self.font_medium
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        return rect

    def draw_menu(self, screen, game_state, score, level, wave):
        screen.fill(BLACK)
        
        if game_state == GameState.MENU:
            title = self.font_large.render("SPACE SHOOTER", True, WHITE, center=True)
            title.center = (SCREEN_WIDTH/2, 200)
            screen.blit(title, title)
            
            start = self.font_medium.render("Press ENTER to Start", True, GREEN)
            start.center = (SCREEN_WIDTH/2, 400)
            screen.blit(start, start)
            
            load = self.font_small.render("Press L to Load Game", True, GRAY)
            load.center = (SCREEN_WIDTH/2, 450)
            screen.blit(load, load)

        elif game_state == GameState.PAUSED:
            pause = self.font_large.render("PAUSED", True, WHITE, center=True)
            pause.center = (SCREEN_WIDTH/2, 300)
            screen.blit(pause, pause)
            
            resume = self.font_medium.render("Press ESC to Resume", True, GREEN)
            resume.center = (SCREEN_WIDTH/2, 400)
            screen.blit(resume, resume)

        elif game_state == GameState.GAME_OVER:
            go = self.font_large.render("GAME OVER", True, RED, center=True)
            go.center = (SCREEN_WIDTH/2, 300)
            screen.blit(go, go)
            
            score_text = self.font_medium.render(f"Score: {score}", True, WHITE)
            score_text.center = (SCREEN_WIDTH/2, 400)
            screen.blit(score_text, score_text)
            
            restart = self.font_medium.render("Press ENTER to Restart", True, GREEN)
            restart.center = (SCREEN_WIDTH/2, 500)
            screen.blit(restart, restart)

        elif game_state == GameState.VICTORY:
            vic = self.font_large.render("VICTORY!", True, YELLOW, center=True)
            vic.center = (SCREEN_WIDTH/2, 300)
            screen.blit(vic, vic)

    def draw_hud(self, screen, player, wave, score, level, xp, xp_needed, achievements):
        # 血条
        pygame.draw.rect(screen, RED, (10, 10, 200, 20))
        health_ratio = player.health / player.max_health
        pygame.draw.rect(screen, GREEN, (10, 10, 200 * health_ratio, 20))
        pygame.draw.rect(screen, WHITE, (10, 10, 200, 20), 1)
        
        # 经验条
        pygame.draw.rect(screen, DARK_GRAY, (10, 40, 200, 10))
        xp_ratio = xp / xp_needed
        pygame.draw.rect(screen, BLUE, (10, 40, 200 * xp_ratio, 10))
        
        # 文字
        score_text = self.font_small.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 60))
        
        wave_text = self.font_small.render(f"Wave: {wave}", True, WHITE)
        screen.blit(wave_text, (10, 80))
        
        level_text = self.font_small.render(f"Lvl: {level}", True, WHITE)
        screen.blit(level_text, (10, 100))
        
        # 成就提示（如果有新的）
        # 简化：只显示已解锁的成就数量
        unlocked_count = sum(1 for v in achievements.achievements.values() if v["unlocked"])
        ach_text = self.font_small.render(f"Achievements: {unlocked_count}", True, YELLOW)
        screen.blit(ach_text, (SCREEN_WIDTH - 150, 10))

# =================主游戏类=================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter by Agnes-2.0-Flash")
        self.clock = pygame.time.Clock()
        
        # 系统初始化
        self.sound_mgr = SoundManager()
        self.ui = UI()
        self.achieve_mgr = AchievementManager()
        self.save_data = SaveManager.load()
        
        # 游戏状态
        self.state = GameState.MENU
        self.score = 0
        self.wave = 1
        self.wave_enemies_left = 0
        self.wave_delay = 0
        self.scene = SceneType.SPACE
        
        # 实体
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.enemies = []
        self.powerups = []
        self.projectiles = [] # 全局子弹用于碰撞检测
        
        # 难度控制
        self.enemy_spawn_timer = 0
        self.bomb_active = False
        self.bomb_timer = 0

    def start_game(self):
        self.state = GameState.PLAYING
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.enemies = []
        self.powerups = []
        self.score = 0
        self.wave = 1
        self.start_wave()
        self.sound_mgr.play('powerup') # 重置音效

    def start_wave(self):
        # 计算波次敌人数量
        base_count = 5 + self.wave * 2
        if self.wave % 5 == 0:
            # Boss Wave
            self.enemies.append(Enemy(SCREEN_WIDTH // 2, -100, EnemyType.BOSS, 1.0 + self.wave * 0.1))
            self.wave_enemies_left = 1
            self.sound_mgr.play('boss_enter')
        else:
            self.wave_enemies_left = base_count
            self.wave_delay = 60 # 生成间隔

    def spawn_enemy(self):
        if self.wave_delay > 0:
            self.wave_delay -= 1
            return

        if self.wave_enemies_left > 0:
            # 选择敌人类型，基于波次
            r = random.random()
            etype = EnemyType.DRONE
            if self.wave > 2 and r > 0.7: etype = EnemyType.BOMBER
            if self.wave > 4 and r > 0.8: etype = EnemyType.SPEEDER
            if self.wave > 6 and r > 0.9: etype = EnemyType.TANK
            if self.wave > 8 and r > 0.95: etype = EnemyType.ELITE
            
            x = random.randint(0, SCREEN_WIDTH - 40)
            self.enemies.append(Enemy(x, -50, etype, 1.0 + self.wave * 0.1))
            self.wave_enemies_left -= 1
            self.wave_delay = max(10, 60 - self.wave * 2)

    def check_collisions(self):
        # 玩家子弹击中敌人
        for p in self.player.projectiles:
            if not p.active: continue
            for e in self.enemies:
                if not e.active: continue
                if p.rect.colliderect(e.rect):
                    e.take_damage(p.damage)
                    p.active = False
                    self.player.explosion_particles.emit(p.x, p.y, WHITE, 5, (1, 2), (2, 3), 10)
                    self.sound_mgr.play('hit')
                    
                    if not e.active:
                        self.score += e.score
                        self.player.explosion_particles.emit(e.x + e.width/2, e.y + e.height/2, e.color, 30, (3, 6), (4, 8), 40)
                        self.sound_mgr.play('explosion')
                        self.achieve_mgr.stats["enemies_killed"] += 1
                        
                        # 掉落道具
                        if random.random() < 0.2:
                            p_type = random.choice(list(PowerUpType))
                            self.powerups.append(PowerUp(e.x, e.y, p_type))
                        
                        # 检查Boss击杀
                        if e.enemy_type == EnemyType.BOSS:
                            self.achieve_mgr.stats["waves_survived"] = max(self.achieve_mgr.stats["waves_survived"], self.wave)
                            self.achieve_mgr.check(self.state)
                            self.save_data.boss_defeated = True
                            # 下一波
                            self.wave += 1
                            self.start_wave()
                            return

        # 敌人子弹击中玩家
        for e in self.enemies:
            if not e.active: continue
            for p in e.projectiles:
                if not p.active: continue
                if p.rect.colliderect(self.player.rect):
                    if self.player.invulnerable <= 0:
                        self.player.take_damage(p.damage)
                        p.active = False
                        self.player.explosion_particles.emit(self.player.x + 20, self.player.y + 20, RED, 10, (2, 4), (2, 4), 20)
                        self.sound_mgr.play('hit')
                        if self.player.health < 10:
                            self.achieve_mgr.stats["waves_survived"] = self.wave # 简化检查
                    else:
                        p.active = False

        # 玩家碰撞敌人
        for e in self.enemies:
            if not e.active: continue
            if self.player.rect.colliderect(e.rect):
                if self.player.invulnerable <= 0:
                    self.player.take_damage(20)
                    self.player.invulnerable = 60
                    e.take_damage(50) # 撞击伤害
                    if not e.active:
                        self.score += e.score
                        self.achieve_mgr.stats["enemies_killed"] += 1

        # 玩家收集道具
        for pu in self.powerups:
            if pu.active and self.player.rect.colliderect(pu.rect):
                self.apply_powerup(pu.p_type)
                pu.active = False
                self.sound_mgr.play('powerup')
                self.achieve_mgr.stats["powerups_collected"] += 1

    def apply_powerup(self, p_type):
        if p_type == PowerUpType.HEALTH:
            self.player.heal(30)
        elif p_type == PowerUpType.SHIELD:
            self.player.shield = 50
        elif p_type == PowerUpType.BOMB:
            self.bomb_active = True
            self.bomb_timer = 10
            self.sound_mgr.play('explosion')
            # 清除屏幕敌人
            for e in self.enemies:
                e.take_damage(1000)
                self.player.explosion_particles.emit(e.x, e.y, e.color, 20, (2, 5), (3, 6), 30)
            self.achieve_mgr.stats["bombs_used"] += 1
        elif p_type == PowerUpType.SPEED:
            self.player.skill_speed = 1.5
            pygame.time.set_timer(pygame.USEREVENT, 5000) # 5秒后重置
        elif p_type == PowerUpType.EXP_BONUS:
            self.score += 500

    def update(self):
        if self.state != GameState.PLAYING:
            return

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        # 玩家更新
        self.player.update(keys, mouse_pos, self.enemies)
        
        # 生成敌人
        self.spawn_enemy()

        # 敌人更新
        for e in self.enemies:
            e.update(self.player)

        # 道具更新
        for pu in self.powerups:
            pu.update()
        self.powerups = [p for p in self.powerups if p.active]

        # 清理非活跃实体
        self.enemies = [e for e in self.enemies if e.active]

        # 碰撞检测
        self.check_collisions()

        # 波次检查
        if len(self.enemies) == 0 and self.wave_enemies_left <= 0 and self.wave_delay <= 0:
            # 波次结束
            self.wave += 1
            self.start_wave()
            self.achieve_mgr.stats["waves_survived"] = self.wave

        # 炸弹计时
        if self.bomb_active:
            self.bomb_timer -= 1
            if self.bomb_timer <= 0:
                self.bomb_active = False

        # 玩家死亡
        if self.player.health <= 0:
            self.state = GameState.GAME_OVER
            self.sound_mgr.stop()

        # 成就检查
        self.achieve_mgr.check(self.state)

    def draw(self):
        # 背景
        if self.scene == SceneType.SPACE:
            self.screen.fill(BLACK)
        elif self.scene == SceneType.ASTEROID_FIELD:
            self.screen.fill((20, 20, 30))
        elif self.scene == SceneType.NEBULA:
            self.screen.fill((10, 0, 20))

        if self.state == GameState.PLAYING:
            # 绘制实体
            for e in self.enemies:
                e.draw(self.screen)
            
            for pu in self.powerups:
                pu.draw(self.screen)
                
            self.player.draw(self.screen)
            
            # 绘制炸弹特效
            if self.bomb_active:
                self.screen.fill((255, 255, 255, 100), special_flags=pygame.BLEND_RGBA_ADD)

            # 绘制UI
            self.ui.draw_hud(self.screen, self.player, self.wave, self.score, 
                             self.save_data.level, self.save_data.xp, self.save_data.level_xp_needed, 
                             self.achieve_mgr)

        else:
            self.ui.draw_menu(self.screen, self.state, self.score, self.save_data.level, self.wave)

        pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_RETURN:
                        self.start_game()
                    if event.key == pygame.K_l:
                        # 尝试加载存档继续
                        self.save_data = SaveManager.load()
                        self.start_game()
                        # 恢复玩家状态等... (简化处理)
                
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                    if event.key == pygame.K_SPACE:
                        if self.player.shoot():
                            self.sound_mgr.play('shoot')
                    if event.key == pygame.K_b:
                        # 使用炸弹（如果有道具逻辑扩展）
                        pass
                    if event.key == pygame.K_s:
                        SaveManager.save(self.save_data)

                elif self.state == GameState.PAUSED:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PLAYING

                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_RETURN:
                        self.state = GameState.MENU

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == GameState.PLAYING:
                    # 鼠标点击可能触发特殊武器或道具
                    pass

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
