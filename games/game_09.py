import pygame
import sys
import math
import random
import json
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# 初始化Pygame
pygame.init()
pygame.mixer.init()

# 常量配置
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

# ==================== 音效管理器 ====================
class SoundManager:
    """音效管理器，使用合成音效或占位符"""
    def __init__(self):
        self.sounds = {}
        # 由于没有外部文件，我们使用简单的蜂鸣声或静默
        # 在实际游戏中，你会加载 .wav 或 .mp3 文件
        self.enabled = True

    def play_sound(self, sound_name: str, pitch: float = 1.0):
        if not self.enabled:
            return
        # 这里可以扩展为实际加载文件
        # sound = self.sounds[sound_name]
        # sound.set_pitch(pitch)
        # sound.play()
        pass

    def load_sound(self, name: str, path: str):
        try:
            # self.sounds[name] = pygame.mixer.Sound(path)
            self.sounds[name] = None
        except Exception as e:
            print(f"Error loading sound {name}: {e}")

    def stop_all(self):
        pygame.mixer.stop()

# ==================== 成就系统 ====================
class Achievement:
    def __init__(self, id: str, title: str, description: str, condition_func):
        self.id = id
        self.title = title
        self.description = description
        self.condition_func = condition_func
        self.achieved = False

    def check(self, game_state):
        if not self.achieved and self.condition_func(game_state):
            self.achieved = True
            return True
        return False

class AchievementSystem:
    def __init__(self):
        self.achievements: List[Achievement] = []
        self.load_achievements()

    def load_achievements(self):
        # 定义10个成就
        self.achievements = [
            Achievement("first_blood", "初生牛犊", "击杀第一个敌人", 
                        lambda gs: gs.stats['kills'] >= 1),
            Achievement("sharpshooter", "神射手", "单波击杀50个敌人", 
                        lambda gs: gs.current_wave_kills >= 50),
            Achievement("boss_slayer", "屠龙者", "击杀第一个Boss", 
                        lambda gs: gs.stats['boss_kills'] >= 1),
            Achievement("survivor", "幸存者", "存活10分钟", 
                        lambda gs: gs.stats['survival_time'] >= 600),
            Achievement("collector", "收藏家", "收集10种不同道具", 
                        lambda gs: len(gs.stats['items_collected']) >= 10),
            Achievement("max_level", "满级专家", "达到最高等级(假设10)", 
                        lambda gs: gs.player.level >= 10),
            Achievement("weapon_master", "武器大师", "使用所有类型的武器至少一次", 
                        lambda gs: len(gs.stats['weapons_used']) >= 6),
            Achievement("perfect_run", "完美通关", "无伤通过第一关", 
                        lambda gs: gs.stats['damage_taken'] == 0 and gs.stats['waves_completed'] >= 1),
            Achievement("speed_demon", "极速先锋", "在10秒内完成第一波", 
                        lambda gs: gs.stats['wave1_time'] <= 10),
            Achievement("rich_man", "富翁", "拥有10000金币", 
                        lambda gs: gs.player.money >= 10000),
        ]

    def check_all(self, game_state):
        new_achievements = []
        for ach in self.achievements:
            if ach.check(game_state):
                new_achievements.append(ach.title)
        return new_achievements

# ==================== 存档系统 ====================
class SaveSystem:
    def __init__(self, filename="save_data.json"):
        self.filename = filename

    def save(self, player_stats: dict, achievements_achieved: List[str]):
        data = {
            "stats": player_stats,
            "achievements": achievements_achieved
        }
        with open(self.filename, 'w') as f:
            json.dump(data, f)

    def load(self) -> Optional[dict]:
        if not os.path.exists(self.filename):
            return None
        with open(self.filename, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None

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
        self.size *= 0.95

    def draw(self, screen):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            # 简单绘制圆形
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), max(1, int(self.size)))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, count, color, speed_range=(1, 3), life_range=(20, 40), size_range=(1, 4)):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
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

# ==================== 实体基类 ====================
class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.width = width
        self.height = height
        self.color = color
        self.health = 100
        self.max_health = 100
        self.dead = False

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.dead = True

    def draw(self, screen):
        screen.blit(self.image, self.rect)

# ==================== 玩家飞船 ====================
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40, BLUE)
        self.speed = 5
        self.score = 0
        self.money = 0
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = 100
        self.weapon_index = 0
        self.weapons = [
            Weapon("Basic Blaster", 2, 10, 10, 0, 0, 5), # Name, Damage, Speed, Cooldown, Spread, Type, Rate
            Weapon("Shotgun", 5, 8, 15, 0.3, 0, 3),
            Weapon("Laser", 1, 15, 0.5, 0, 1, 20), # 高射速低伤害
            Weapon("Missile", 20, 5, 30, 0, 2, 1), # 追踪
            Weapon("Plasma", 10, 12, 20, 0.1, 0, 2),
            Weapon("Railgun", 100, 20, 60, 0, 3, 0.5) # 穿透
        ]
        self.last_shot_time = 0
        self.shield = 0
        self.max_shield = 100
        self.invincible = False
        self.invincible_timer = 0
        self.skill_points = 0
        self.skills = {
            "damage_up": 0,
            "speed_up": 0,
            "shield_up": 0,
            "exp_bonus": 0
        }

    def update(self, keys, mouse_pos, screen_rect):
        # 移动
        dx, dy = 0, 0
        if keys[pygame.K_w]: dy -= self.speed
        if keys[pygame.K_s]: dy += self.speed
        if keys[pygame.K_a]: dx -= self.speed
        if keys[pygame.K_d]: dx += self.speed
        
        # 鼠标控制方向（影响射击角度或移动倾向，这里简化为移动倾向）
        # 如果鼠标在屏幕外，向鼠标方向移动
        if mouse_pos[0] < 0: dx -= 2
        if mouse_pos[0] > screen_rect.width: dx += 2
        if mouse_pos[1] < 0: dy -= 2
        if mouse_pos[1] > screen_rect.height: dy += 2

        self.rect.x += dx
        self.rect.y += dy

        # 边界限制
        self.rect.clamp_ip(screen_rect)

        # 无敌时间处理
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

    def shoot(self, bullets, current_time):
        weapon = self.weapons[self.weapon_index]
        if current_time - self.last_shot_time >= weapon.cooldown:
            self.last_shot_time = current_time
            # 计算射击方向（向鼠标方向）
            # 这里简化为向上射击，实际可改为向鼠标方向
            angle = -math.pi / 2 # 向上
            
            for i in range(int(weapon.spread * 10) + 1):
                spread_angle = angle + random.uniform(-weapon.spread, weapon.spread)
                vx = math.cos(spread_angle) * weapon.speed
                vy = math.sin(spread_angle) * weapon.speed
                
                bullet = Bullet(
                    self.rect.centerx, 
                    self.rect.top, 
                    vx, vy, 
                    weapon.damage * (1 + self.skills['damage_up'] * 0.2),
                    weapon.type,
                    weapon.name
                )
                bullets.add(bullet)

    def gain_exp(self, amount):
        self.exp += amount * (1 + self.skills['exp_bonus'] * 0.2)
        if self.exp >= self.exp_to_next_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next_level
        self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
        self.skill_points += 1
        self.max_health += 10
        self.health = self.max_health

    def heal(self, amount):
        self.health = min(self.health + amount, self.max_health)

    def take_damage(self, amount):
        if self.invincible:
            return
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield
                self.shield = 0
        else:
            self.health -= amount
        
        if self.health <= 0:
            self.dead = True
        else:
            self.invincible = True
            self.invincible_timer = 60 # 1秒无敌

# ==================== 子弹 ====================
class Bullet(Entity):
    def __init__(self, x, y, vx, vy, damage, bullet_type, name):
        color = WHITE
        if bullet_type == 0: color = YELLOW
        elif bullet_type == 1: color = CYAN
        elif bullet_type == 2: color = MAGENTA
        elif bullet_type == 3: color = RED
        
        super().__init__(x, y, 8, 8, color)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.bullet_type = bullet_type
        self.name = name
        self.life = 300 # 子弹存在时间

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.life -= 1
        if self.life <= 0 or not SCREEN_rect.contains(self.rect):
            self.dead = True

# ==================== 敌人系统 ====================
class EnemyType(Enum):
    DRONE = 1
    FIGHTER = 2
    TANK = 3
    SPEEDER = 4
    BOSS = 5

class Enemy(Entity):
    def __init__(self, enemy_type: EnemyType, x, y, wave_level=1):
        super().__init__(x, y, 30, 30, RED)
        self.enemy_type = enemy_type
        self.wave_level = wave_level
        
        # 属性配置
        if enemy_type == EnemyType.DRONE:
            self.health = 20 + wave_level * 5
            self.speed = 2
            self.score = 10
            self.color = RED
        elif enemy_type == EnemyType.FIGHTER:
            self.health = 40 + wave_level * 10
            self.speed = 3
            self.score = 20
            self.color = ORANGE
        elif enemy_type == EnemyType.TANK:
            self.health = 100 + wave_level * 20
            self.speed = 1
            self.score = 50
            self.color = BROWN
        elif enemy_type == EnemyType.SPEEDER:
            self.health = 15 + wave_level * 3
            self.speed = 5
            self.score = 15
            self.color = PINK
        elif enemy_type == EnemyType.BOSS:
            self.health = 1000 + wave_level * 100
            self.speed = 1
            self.score = 500
            self.color = PURPLE
            self.width = 100
            self.height = 100
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill(self.color)
            self.rect = self.image.get_rect()
            self.rect.x = x
            self.rect.y = y
            self.phase = 1

        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        self.move_pattern = random.choice(["straight", "sine", "zigzag"])
        self.move_timer = 0

    def update(self, player):
        self.move_timer += 1
        
        if self.enemy_type == EnemyType.BOSS:
            self.update_boss(player)
            return

        if self.move_pattern == "straight":
            self.rect.y += self.speed
        elif self.move_pattern == "sine":
            self.rect.y += self.speed
            self.rect.x += math.sin(self.move_timer * 0.05) * 2
        elif self.move_pattern == "zigzag":
            if self.move_timer % 60 < 30:
                self.rect.x += self.speed
            else:
                self.rect.x -= self.speed
            self.rect.y += self.speed * 0.5

        # 边界检查
        if self.rect.bottom > SCREEN_HEIGHT:
            self.dead = True

    def update_boss(self, player):
        # 简单的Boss行为：在顶部左右移动，偶尔向下
        self.rect.x += math.sin(self.move_timer * 0.02) * 3
        if self.rect.y < 50:
            self.rect.y += 0.5
        
        # 阶段切换
        if self.health < self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.speed *= 1.5
        if self.health < self.max_health * 0.2 and self.phase == 2:
            self.phase = 3
            self.speed *= 1.5

# ==================== 武器系统 ====================
class Weapon:
    def __init__(self, name, damage, speed, cooldown, spread, type, rate):
        self.name = name
        self.damage = damage
        self.speed = speed
        self.cooldown = cooldown # 帧数
        self.spread = spread
        self.type = type # 0: normal, 1: laser, 2: missile, 3: rail
        self.rate = rate # 射速因子

# ==================== 道具系统 ====================
class Item(Entity):
    def __init__(self, x, y, item_type):
        super().__init__(x, y, 20, 20, WHITE)
        self.item_type = item_type
        self.color = self.get_color(item_type)
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vy = 2

    def get_color(self, item_type):
        if item_type == "health": return GREEN
        elif item_type == "shield": return CYAN
        elif item_type == "money": return YELLOW
        elif item_type == "bomb": return RED
        elif item_type == "exp": return MAGENTA
        elif item_type == "speed": return WHITE
        elif item_type == "weapon_swap": return BLUE
        elif item_type == "invincible": return PURPLE
        return WHITE

    def update(self):
        self.rect.y += self.vy
        if self.rect.top > SCREEN_HEIGHT:
            self.dead = True

# ==================== 游戏状态机 ====================
class GameState(Enum):
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    SHOP = 5
    ACHIEVEMENTS = 6

# ==================== 主游戏类 ====================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter Pro")
        self.clock = pygame.time.Clock()
        
        self.state = GameState.MENU
        self.sound_manager = SoundManager()
        self.achievement_system = AchievementSystem()
        self.save_system = SaveSystem()
        self.particle_system = ParticleSystem()
        
        self.font = pygame.font.SysFont("arial", 24)
        self.big_font = pygame.font.SysFont("arial", 48)
        
        self.reset_game()

    def reset_game(self):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.items = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        
        self.wave = 1
        self.wave_kills = 0
        self.wave_timer = 0
        self.wave_active = False
        self.enemies_to_spawn = 0
        self.spawn_timer = 0
        
        self.stats = {
            'kills': 0,
            'boss_kills': 0,
            'survival_time': 0,
            'items_collected': set(),
            'weapons_used': set(),
            'damage_taken': 0,
            'wave1_time': 0,
            'waves_completed': 0
        }
        
        self.current_wave_kills = 0
        self.game_time = 0

    def start_wave(self):
        self.wave_active = True
        self.wave_kills = 0
        # 计算敌人数量
        base_count = 5 + self.wave * 2
        if self.wave % 5 == 0:
            self.enemies_to_spawn = 1 # Boss
        else:
            self.enemies_to_spawn = base_count
        self.spawn_timer = 0

    def spawn_enemy(self):
        if self.enemies_to_spawn <= 0:
            return

        x = random.randint(0, SCREEN_WIDTH - 30)
        y = -50
        
        if self.wave % 5 == 0 and self.enemies_to_spawn == 1:
            enemy = Enemy(EnemyType.BOSS, SCREEN_WIDTH // 2, -100, self.wave)
        else:
            r = random.random()
            if r < 0.5:
                enemy = Enemy(EnemyType.DRONE, x, y, self.wave)
            elif r < 0.7:
                enemy = Enemy(EnemyType.FIGHTER, x, y, self.wave)
            elif r < 0.85:
                enemy = Enemy(EnemyType.TANK, x, y, self.wave)
            else:
                enemy = Enemy(EnemyType.SPEEDER, x, y, self.wave)
        
        self.enemies.add(enemy)
        self.enemies_to_spawn -= 1

    def check_collisions(self):
        # 子弹击中敌人
        for bullet in self.bullets:
            hit_enemies = pygame.sprite.spritecollide(bullet, self.enemies, False)
            if hit_enemies:
                enemy = hit_enemies[0]
                enemy.take_damage(bullet.damage)
                self.particle_system.emit(bullet.rect.centerx, bullet.rect.centery, 5, YELLOW, size_range=(1,3))
                if bullet.bullet_type == 3: # Railgun穿透
                    pass # 逻辑简化
                else:
                    bullet.dead = True
                
                if enemy.dead:
                    self.player.gain_exp(enemy.score // 5)
                    self.player.score += enemy.score
                    self.stats['kills'] += 1
                    self.current_wave_kills += 1
                    self.particle_system.emit(enemy.rect.centerx, enemy.rect.centery, 20, enemy.color)
                    
                    # 掉落道具
                    if random.random() < 0.3:
                        item_type = random.choice(["health", "shield", "money", "bomb", "exp", "speed", "weapon_swap", "invincible"])
                        self.items.add(Item(enemy.rect.centerx, enemy.rect.centery, item_type))
                    
                    if enemy.enemy_type == EnemyType.BOSS:
                        self.stats['boss_kills'] += 1
                        self.stats['waves_completed'] += 1

        # 敌人击中玩家
        for enemy in self.enemies:
            if pygame.sprite.collide_rect(self.player, enemy):
                self.player.take_damage(10)
                self.stats['damage_taken'] += 10
                self.particle_system.emit(self.player.rect.centerx, self.player.rect.centery, 10, RED)

        # 玩家拾取道具
        for item in self.items:
            if pygame.sprite.collide_rect(self.player, item):
                self.apply_item(item.item_type)
                self.stats['items_collected'].add(item.item_type)
                item.dead = True

        # 敌人子弹击中玩家
        for e_bullet in self.enemy_bullets:
            if pygame.sprite.collide_rect(self.player, e_bullet):
                self.player.take_damage(e_bullet.damage)
                self.stats['damage_taken'] += e_bullet.damage
                e_bullet.dead = True

    def apply_item(self, item_type):
        if item_type == "health":
            self.player.heal(30)
        elif item_type == "shield":
            self.player.shield = min(self.player.shield + 50, self.player.max_shield)
        elif item_type == "money":
            self.player.money += 100
        elif item_type == "bomb":
            # 全屏清除敌人
            for enemy in self.enemies:
                enemy.take_damage(1000)
                if enemy.dead:
                    self.player.score += enemy.score
                    self.stats['kills'] += 1
            self.particle_system.emit(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 100, WHITE, speed_range=(5, 10))
        elif item_type == "exp":
            self.player.gain_exp(50)
        elif item_type == "speed":
            self.player.speed += 1
        elif item_type == "weapon_swap":
            self.player.weapon_index = (self.player.weapon_index + 1) % len(self.player.weapons)
        elif item_type == "invincible":
            self.player.invincible = True
            self.player.invincible_timer = 300 # 5秒

    def draw_ui(self):
        # HUD
        pygame.draw.rect(self.screen, GRAY, (0, 0, SCREEN_WIDTH, 50))
        hp_text = self.font.render(f"HP: {self.player.health}/{self.player.max_health}", True, WHITE)
        shield_text = self.font.render(f"Shield: {self.player.shield}/{self.player.max_shield}", True, CYAN)
        exp_text = self.font.render(f"Lvl: {self.player.level} Exp: {self.player.exp}/{self.player.exp_to_next_level}", True, MAGENTA)
        money_text = self.font.render(f"Money: {self.player.money}", True, YELLOW)
        wave_text = self.font.render(f"Wave: {self.wave}", True, WHITE)
        score_text = self.font.render(f"Score: {self.player.score}", True, WHITE)
        
        self.screen.blit(hp_text, (10, 10))
        self.screen.blit(shield_text, (10, 40))
        self.screen.blit(exp_text, (10, 70))
        self.screen.blit(money_text, (10, 100))
        self.screen.blit(wave_text, (SCREEN_WIDTH - 100, 10))
        self.screen.blit(score_text, (SCREEN_WIDTH - 150, 40))

        # 武器指示
        weapon_name = self.player.weapons[self.player.weapon_index].name
        w_text = self.font.render(f"Weapon: {weapon_name}", True, WHITE)
        self.screen.blit(w_text, (SCREEN_WIDTH - 200, 70))

    def draw_menu(self):
        self.screen.fill(BLACK)
        title = self.big_font.render("SPACE SHOOTER PRO", True, WHITE)
        start_text = self.font.render("Press ENTER to Start", True, GREEN)
        load_text = self.font.render("Press L to Load Game", True, YELLOW)
        save_text = self.font.render("Press S to Save (if playing)", True, YELLOW)
        
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        self.screen.blit(start_text, (SCREEN_WIDTH//2 - start_text.get_width()//2, 300))
        self.screen.blit(load_text, (SCREEN_WIDTH//2 - load_text.get_width()//2, 400))
        
        # 检查存档
        if self.save_system.load():
            self.screen.blit(save_text, (SCREEN_WIDTH//2 - save_text.get_width()//2, 450))

    def draw_game_over(self):
        self.screen.fill(BLACK)
        go_text = self.big_font.render("GAME OVER", True, RED)
        score_text = self.font.render(f"Final Score: {self.player.score}", True, WHITE)
        restart_text = self.font.render("Press ENTER to Restart", True, GREEN)
        
        self.screen.blit(go_text, (SCREEN_WIDTH//2 - go_text.get_width()//2, 200))
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, 300))
        self.screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, 400))

    def draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        pause_text = self.big_font.render("PAUSED", True, WHITE)
        resume_text = self.font.render("Press P to Resume", True, GREEN)
        quit_text = self.font.render("Press Q to Quit to Menu", True, RED)
        
        self.screen.blit(pause_text, (SCREEN_WIDTH//2 - pause_text.get_width()//2, 300))
        self.screen.blit(resume_text, (SCREEN_WIDTH//2 - resume_text.get_width()//2, 400))
        self.screen.blit(quit_text, (SCREEN_WIDTH//2 - quit_text.get_width()//2, 450))

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            current_time = pygame.time.get_ticks()
            self.game_time += dt
            
            # 成就检查
            if self.state == GameState.PLAYING:
                new_achs = self.achievement_system.check_all(self)
                if new_achs:
                    print(f"Achievements Unlocked: {new_achs}")

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if self.state == GameState.MENU:
                        if event.key == pygame.K_RETURN:
                            self.state = GameState.PLAYING
                            self.start_wave()
                        elif event.key == pygame.K_l:
                            saved_data = self.save_system.load()
                            if saved_data:
                                self.player.score = saved_data['stats'].get('score', 0)
                                # 简化：只恢复分数，其他状态重置
                                self.state = GameState.PLAYING
                                self.start_wave()
                    elif self.state == GameState.PLAYING:
                        if event.key == pygame.K_p:
                            self.state = GameState.PAUSED
                    elif self.state == GameState.PAUSED:
                        if event.key == pygame.K_p:
                            self.state = GameState.PLAYING
                        elif event.key == pygame.K_q:
                            self.state = GameState.MENU
                    elif self.state == GameState.GAME_OVER:
                        if event.key == pygame.K_RETURN:
                            self.reset_game()
                            self.state = GameState.MENU

            keys = pygame.key.get_pressed()
            mouse_pos = pygame.mouse.get_pos()

            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.PLAYING:
                # 更新
                self.player.update(keys, mouse_pos, self.screen.get_rect())
                self.player.shoot(self.bullets, current_time)
                
                # 生成敌人
                if self.wave_active and self.enemies_to_spawn > 0:
                    self.spawn_timer += 1
                    if self.spawn_timer > 60: # 每秒生成一个
                        self.spawn_enemy()
                        self.spawn_timer = 0
                
                # 检查波次结束
                if self.wave_active and self.enemies_to_spawn == 0 and len(self.enemies) == 0:
                    self.wave_active = False
                    self.wave += 1
                    self.start_wave()

                # 更新实体
                self.bullets.update()
                self.enemies.update(self.player)
                self.items.update()
                self.enemy_bullets.update()
                self.particle_system.update()

                # 清理死亡实体
                self.bullets.kill()
                self.enemies.kill()
                self.items.kill()
                self.enemy_bullets.kill()

                # 碰撞检测
                self.check_collisions()

                # 玩家死亡
                if self.player.dead:
                    self.state = GameState.GAME_OVER
                    self.save_system.save(self.player.score, []) # 简化存档

                # 绘制
                self.screen.fill(BLACK)
                self.particle_system.draw(self.screen)
                self.player.draw(self.screen)
                self.bullets.draw(self.screen)
                self.enemies.draw(self.screen)
                self.items.draw(self.screen)
                self.enemy_bullets.draw(self.screen)
                self.draw_ui()

            elif self.state == GameState.PAUSED:
                self.draw_pause()
            elif self.state == GameState.GAME_OVER:
                self.draw_game_over()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    # 定义一些颜色常量如果之前没定义
    ORANGE = (255, 165, 0)
    BROWN = (139, 69, 19)
    PINK = (255, 192, 203)
    PURPLE = (128, 0, 128)
    
    game = Game()
    game.run()
