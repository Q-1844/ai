import pygame
import sys
import math
import random
import json
import os
from enum import Enum
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

# 颜色定义 (RGB)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GRAY = (128, 128, 128)

# 游戏状态枚举
class GameState(Enum):
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    SHOP = 5
    ACHIEVEMENTS = 6

# ==========================
# 2. 音效管理器 (Audio Manager)
# ==========================

class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.music_volume = 0.5
        self.sfx_volume = 0.7
        
    def load_sound(self, name, freq=44100, size=-16, channels=2):
        # 由于没有外部音频文件，我们创建合成音效
        # 在实际项目中，这里会加载 .wav 或 .ogg 文件
        pass 

    def play_explosion(self):
        # 模拟爆炸声
        pass

    def play_laser(self):
        # 模拟激光声
        pass
    
    def play_powerup(self):
        pass

    def play_boss_appear(self):
        pass

# ==========================
# 3. 粒子系统 (Particle System)
# ==========================

class Particle:
    def __init__(self, x, y, color, speed, life, size):
        self.x = x
        self.y = y
        self.color = color
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = speed * random.uniform(0.5, 1.5)
        self.vx = math.cos(self.angle) * self.speed
        self.vy = math.sin(self.angle) * self.speed
        self.life = life
        self.max_life = life
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size *= 0.95

    def draw(self, screen):
        alpha = int((self.life / self.max_life) * 255)
        # 简单的圆形粒子
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), max(1, int(self.size)))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, count, color, speed_range=(1, 5), life_range=(20, 50), size_range=(2, 5)):
        for _ in range(count):
            speed = random.uniform(*speed_range)
            life = random.randint(*life_range)
            size = random.uniform(*size_range)
            self.particles.append(Particle(x, y, color, speed, life, size))

    def update(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)

# ==========================
# 4. 武器系统 (Weapon System)
# ==========================

class WeaponType(Enum):
    BASIC = 1
    SPREAD = 2
    RAPID = 3
    LASER = 4
    MISSILE = 5
    PLASMA = 6

class Projectile:
    def __init__(self, x, y, angle, speed, damage, color, weapon_type, is_enemy=False):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = damage
        self.color = color
        self.weapon_type = weapon_type
        self.is_enemy = is_enemy
        self.radius = 4
        self.active = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        # 边界检查
        if self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.active = False

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

class Weapon:
    def __init__(self, weapon_type: WeaponType, damage=10, fire_rate=15, speed=10, color=WHITE):
        self.type = weapon_type
        self.damage = damage
        self.fire_rate = fire_rate  # Frames between shots
        self.cooldown = 0
        self.speed = speed
        self.color = color
        self.unlocked = True

    def can_fire(self):
        return self.cooldown <= 0

    def fire(self):
        self.cooldown = self.fire_rate

    def update_cooldown(self):
        if self.cooldown > 0:
            self.cooldown -= 1

# ==========================
# 5. 实体基类与玩家
# ==========================

class Entity:
    def __init__(self, x, y, width, height, health):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.health = health
        self.max_health = health
        self.dead = False
        self.rect = pygame.Rect(x, y, width, height)

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.dead = True

    def update_rect(self):
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 30, 30, 100)
        self.speed = 5
        self.weapons = {
            WeaponType.BASIC: Weapon(WeaponType.BASIC, 10, 15, 10, WHITE),
            WeaponType.SPREAD: Weapon(WeaponType.SPREAD, 8, 30, 12, CYAN),
            WeaponType.RAPID: Weapon(WeaponType.RAPID, 5, 5, 15, YELLOW),
            WeaponType.LASER: Weapon(WeaponType.LASER, 2, 2, 20, GREEN), # Continuous beam logic handled separately usually, simplified here
            WeaponType.MISSILE: Weapon(WeaponType.MISSILE, 30, 60, 8, RED),
            WeaponType.PLASMA: Weapon(WeaponType.PLASMA, 20, 40, 14, PURPLE)
        }
        self.current_weapon = WeaponType.BASIC
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = 100
        self.shield = 0
        self.invulnerable_time = 0
        
        # Skills (Simple stat boosts for this demo)
        self.skills = {
            "damage": 0,
            "speed": 0,
            "health": 0,
            "fire_rate": 0
        }

    def update(self, keys, mouse_pos, particles):
        self.update_rect()
        
        # Movement (WASD)
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            length = math.sqrt(dx*dx + dy*dy)
            dx /= length
            dy /= length

        # Apply Speed Skill
        current_speed = self.speed + (self.skills["speed"] * 0.5)
        
        self.x += dx * current_speed
        self.y += dy * current_speed

        # Boundary Check
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
        self.y = max(0, min(SCREEN_HEIGHT - self.height, self.y))
        
        self.update_rect()

        # Invulnerability Tick
        if self.invulnerable_time > 0:
            self.invulnerable_time -= 1

    def shoot(self, projectiles, particles):
        weapon = self.weapons[self.current_weapon]
        if not weapon.can_fire():
            return

        weapon.fire()
        
        # Aim towards mouse
        # Note: Mouse coordinates need to be relative to screen center or handled carefully
        # For simplicity, we assume mouse controls direction relative to player center
        # In a full game, you might want the ship to rotate to face mouse.
        
        # Calculate angle to mouse
        mouse_x, mouse_y = pygame.mouse.get_pos()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        angle = math.atan2(mouse_y - cy, mouse_x - cx)

        if self.current_weapon == WeaponType.SPREAD:
            for i in range(-1, 2):
                offset_angle = angle + (i * 0.2)
                projectiles.append(Projectile(cx, cy, offset_angle, weapon.speed, weapon.damage, weapon.color))
        elif self.current_weapon == WeaponType.MISSILE:
            proj = Projectile(cx, cy, angle, weapon.speed, weapon.damage, weapon.color)
            proj.is_homming = True # Custom flag for missile logic
            projectiles.append(proj)
        else:
            projectiles.append(Projectile(cx, cy, angle, weapon.speed, weapon.damage, weapon.color))

        # Engine trail particles
        particles.emit(cx, cy + 15, 1, GRAY, (0.5, 2), (10, 20), (2, 4))

    def gain_exp(self, amount):
        self.exp += amount
        if self.exp >= self.exp_to_next_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next_level
        self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
        # Heal on level up
        self.health = self.max_health + (self.skills["health"] * 10)
        return True

    def equip_skill(self, skill_name):
        if skill_name in self.skills:
            self.skills[skill_name] += 1

# ==========================
# 6. 敌人系统 (Enemy System)
# ==========================

class Enemy(Entity):
    def __init__(self, x, y, enemy_type, wave_number):
        super().__init__(x, y, 30, 30, 10)
        self.enemy_type = enemy_type
        self.wave_number = wave_number
        self.score_value = 10
        self.exp_value = 10
        
        # Type specific stats
        if enemy_type == "BASIC":
            self.color = RED
            self.speed = 2
            self.health = 10 + wave_number * 2
            self.max_health = self.health
        elif enemy_type == "FAST":
            self.color = ORANGE
            self.speed = 4
            self.health = 5 + wave_number
            self.max_health = self.health
            self.width = 20
            self.height = 20
        elif enemy_type == "TANK":
            self.color = GRAY
            self.speed = 1
            self.health = 30 + wave_number * 5
            self.max_health = self.health
            self.width = 40
            self.height = 40
        elif enemy_type == "SHOOTER":
            self.color = MAGENTA
            self.speed = 1.5
            self.health = 15 + wave_number * 2
            self.max_health = self.health
        elif enemy_type == "BOSS":
            self.color = PURPLE
            self.speed = 0.5
            self.health = 500 + wave_number * 50
            self.max_health = self.health
            self.width = 100
            self.height = 80
            self.score_value = 500
            self.exp_value = 500
            self.phase = 1
            self.boss_timer = 0

    def update(self, player, projectiles, particles):
        self.update_rect()
        
        # Basic AI
        if self.enemy_type == "BASIC" or self.enemy_type == "FAST":
            # Move down
            self.y += self.speed
            # Slight wobble
            self.x += math.sin(self.y * 0.05) * 0.5
            
        elif self.enemy_type == "TANK":
            self.y += self.speed
            
        elif self.enemy_type == "SHOOTER":
            self.y += self.speed
            # Shoot at player periodically
            if random.randint(0, 60) == 0:
                angle = math.atan2(player.y - self.y, player.x - self.x)
                # Create enemy projectile
                p = Projectile(self.x + self.width/2, self.y + self.height/2, angle, 5, 10, RED, WeaponType.BASIC, is_enemy=True)
                projectiles.append(p)

        elif self.enemy_type == "BOSS":
            self.handle_boss_ai(player, projectiles, particles)

        # Remove if off screen
        if self.y > SCREEN_HEIGHT + 50:
            self.dead = True

    def handle_boss_ai(self, player, projectiles, particles):
        self.boss_timer += 1
        
        # Phase 1: Move slowly down, shoot straight
        if self.phase == 1:
            self.y += 0.5
            if self.boss_timer % 30 == 0:
                angle = math.atan2(player.y - self.y, player.x - self.x)
                projectiles.append(Projectile(self.x + self.width/2, self.y + self.height/2, angle, 6, 15, RED, WeaponType.BASIC, is_enemy=True))
            
            if self.health < self.max_health * 0.6:
                self.phase = 2
                
        # Phase 2: Spiral attack
        elif self.phase == 2:
            self.y += 0.3
            if self.boss_timer % 5 == 0:
                spiral_angle = self.boss_timer * 0.1
                for i in range(4):
                    offset = i * math.pi / 2
                    angle = spiral_angle + offset
                    projectiles.append(Projectile(self.x + self.width/2, self.y + self.height/2, angle, 5, 10, ORANGE, WeaponType.BASIC, is_enemy=True))
            
            if self.health < self.max_health * 0.3:
                self.phase = 3

        # Phase 3: Chaotic movement and rapid fire
        elif self.phase == 3:
            # Erratic movement
            self.x += math.sin(self.boss_timer * 0.1) * 3
            if self.boss_timer % 10 == 0:
                angle = math.atan2(player.y - self.y, player.x - self.x)
                projectiles.append(Projectile(self.x + self.width/2, self.y + self.height/2, angle, 8, 20, RED, WeaponType.BASIC, is_enemy=True))

    def draw(self, screen):
        # Draw simple shape based on type
        if self.enemy_type == "BOSS":
            pygame.draw.rect(screen, self.color, self.rect)
            # Health bar for boss
            bar_width = 200
            health_pct = self.health / self.max_health
            pygame.draw.rect(screen, RED, (self.x + 50, self.y - 20, 200, 10))
            pygame.draw.rect(screen, GREEN, (self.x + 50, self.y - 20, 200 * health_pct, 10))
        else:
            pygame.draw.rect(screen, self.color, self.rect)
            # Simple health bar for non-bosses if damaged
            if self.health < self.max_health:
                bar_width = self.width
                health_pct = self.health / self.max_health
                pygame.draw.rect(screen, RED, (self.x, self.y - 5, bar_width, 3))
                pygame.draw.rect(screen, GREEN, (self.x, self.y - 5, bar_width * health_pct, 3))

# ==========================
# 7. 道具系统 (Power-ups)
# ==========================

class PowerUpType(Enum):
    SHIELD = 1
    SPEED = 2
    BOMB = 3
    HEALTH = 4
    WEAPON_UPGRADE = 5
    RAPID_FIRE = 6
    MULTI_SHOT = 7
    SCORE_BOOST = 8

class PowerUp(Entity):
    def __init__(self, x, y, p_type):
        super().__init__(x, y, 20, 20, 1)
        self.p_type = p_type
        self.vy = 2
        
        if p_type == PowerUpType.SHIELD:
            self.color = BLUE
            self.symbol = "S"
        elif p_type == PowerUpType.SPEED:
            self.color = YELLOW
            self.symbol = ">>"
        elif p_type == PowerUpType.BOMB:
            self.color = BLACK
            self.border = WHITE
            self.symbol = "B"
        elif p_type == PowerUpType.HEALTH:
            self.color = RED
            self.symbol = "+"
        elif p_type == PowerUpType.WEAPON_UPGRADE:
            self.color = CYAN
            self.symbol = "W"
        elif p_type == PowerUpType.RAPID_FIRE:
            self.color = GREEN
            self.symbol = "RF"
        elif p_type == PowerUpType.MULTI_SHOT:
            self.color = MAGENTA
            self.symbol = "MS"
        elif p_type == PowerUpType.SCORE_BOOST:
            self.color = ORANGE
            self.symbol = "$"

    def update(self):
        self.y += self.vy
        self.update_rect()
        if self.y > SCREEN_HEIGHT:
            self.dead = True

    def apply(self, player, projectiles, particles, sound_mgr):
        sound_mgr.play_powerup()
        if self.p_type == PowerUpType.SHIELD:
            player.shield += 50
        elif self.p_type == PowerUpType.SPEED:
            player.skills["speed"] += 1
        elif self.p_type == PowerUpType.BOMB:
            # Clear all enemies and projectiles
            for e in projectiles:
                if e.is_enemy:
                    e.active = False
                else:
                    e.damage = 0 # Disable damage temporarily or just remove
            # Visual effect
            particles.emit(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 100, WHITE, (5, 15), (50, 100), (5, 10))
        elif self.p_type == PowerUpType.HEALTH:
            player.health = min(player.health + 30, player.max_health + player.skills["health"]*10)
        elif self.p_type == PowerUpType.WEAPON_UPGRADE:
            # Switch to next weapon or upgrade current
            weapons_list = list(WeaponType)
            current_idx = weapons_list.index(player.current_weapon)
            next_idx = (current_idx + 1) % len(weapons_list)
            player.current_weapon = weapons_list[next_idx]
        elif self.p_type == PowerUpType.RAPID_FIRE:
            player.skills["fire_rate"] += 1 # Simplified implementation
        elif self.p_type == PowerUpType.MULTI_SHOT:
            player.skills["multi_shot"] = 1 # Placeholder logic
        elif self.p_type == PowerUpType.SCORE_BOOST:
            player.gain_exp(50)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # Draw symbol text could go here, simplified to rect for now

# ==========================
# 8. 成就系统 (Achievements)
# ==========================

class AchievementManager:
    def __init__(self):
        self.achieved = set()
        self.definitions = [
            {"id": "first_kill", "name": "First Blood", "desc": "Kill your first enemy"},
            {"id": "level_5", "name": "Rising Star", "desc": "Reach Level 5"},
            {"id": "boss_slayer", "name": "Dragon Slayer", "desc": "Defeat a Boss"},
            {"id": "no_damage", "name": "Pristine", "desc": "Complete a wave without taking damage"},
            {"id": "power_hungry", "name": "Power Hungry", "desc": "Collect 10 powerups"},
            {"id": "collector", "name": "Collector", "desc": "Unlock 3 different weapons"},
            {"id": "survivor", "name": "Survivor", "desc": "Survive for 5 minutes"},
            {"id": "combo_master", "name": "Combo Master", "desc": "Kill 50 enemies in one wave"},
            {"id": "rich", "name": "Rich", "desc": "Earn 1000 score"},
            {"id": "explorer", "name": "Explorer", "desc": "Visit all 3 levels"}
        ]

    def check(self, condition_key, data=None):
        if condition_key in self.achieved:
            return False
        # Logic to check conditions would go here
        # For demo, we simulate unlocking based on arbitrary events passed
        # In a real app, this would be triggered by specific game events
        return True

    def unlock(self, id_str):
        if id_str not in self.achieved:
            self.achieved.add(id_str)
            return True
        return False

    def save(self, filename="saves/achievements.json"):
        try:
            with open(filename, 'w') as f:
                json.dump(list(self.achieved), f)
        except:
            pass

    def load(self, filename="saves/achievements.json"):
        try:
            with open(filename, 'r') as f:
                self.achieved = set(json.load(f))
        except FileNotFoundError:
            pass

# ==========================
# 9. 存档系统 (Save System)
# ==========================

class SaveManager:
    @staticmethod
    def save_game(player, wave, score, filepath="saves/game_save.json"):
        data = {
            "player_level": player.level,
            "player_exp": player.exp,
            "player_health": player.health,
            "player_skills": player.skills,
            "current_weapon": player.current_weapon.value,
            "wave": wave,
            "score": score
        }
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f)

    @staticmethod
    def load_game(filepath="saves/game_save.json"):
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'r') as f:
            return json.load(f)

# ==========================
# 10. 主游戏类 (Game Engine)
# ==========================

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter Pro")
        self.clock = pygame.time.Clock()
        
        self.state = GameState.MENU
        self.font_large = pygame.font.SysFont("arial", 48)
        self.font_medium = pygame.font.SysFont("arial", 24)
        self.font_small = pygame.font.SysFont("arial", 16)
        
        self.sound_mgr = SoundManager()
        self.particles = ParticleSystem()
        self.achievement_mgr = AchievementManager()
        self.save_mgr = SaveManager()
        
        # Game Variables
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.projectiles = []
        self.enemies = []
        self.powerups = []
        
        self.wave = 1
        self.score = 0
        self.wave_enemies_left = 0
        self.wave_active = False
        self.wave_timer = 0
        self.level_index = 0 # 0, 1, 2 for scenes
        
        self.scenes = ["Deep Space", "Asteroid Field", "Nebula Core"]
        
        # Input handling
        self.keys = pygame.key.get_pressed()
        
        # Menu variables
        self.menu_selection = 0
        self.shop_selection = 0

    def reset_game(self):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.projectiles.clear()
        self.enemies.clear()
        self.powerups.clear()
        self.particles.particles.clear()
        self.wave = 1
        self.score = 0
        self.achievement_mgr = AchievementManager()
        self.start_wave()

    def start_wave(self):
        self.wave_active = True
        is_boss_wave = self.wave % 5 == 0
        
        if is_boss_wave:
            self.enemies.append(Enemy(SCREEN_WIDTH // 2 - 50, -100, "BOSS", self.wave))
            self.sound_mgr.play_boss_appear()
        else:
            # Spawn standard enemies
            count = 5 + self.wave * 2
            for _ in range(count):
                x = random.randint(0, SCREEN_WIDTH - 30)
                y = random.randint(-500, -50)
                r = random.random()
                if r < 0.5:
                    etype = "BASIC"
                elif r < 0.7:
                    etype = "FAST"
                elif r < 0.85:
                    etype = "TANK"
                else:
                    etype = "SHOOTER"
                self.enemies.append(Enemy(x, y, etype, self.wave))
                
        self.wave_enemies_left = len(self.enemies)

    def update(self):
        if self.state == GameState.PLAYING:
            self.handle_input()
            self.player.update(self.keys, pygame.mouse.get_pos(), self.particles)
            
            # Update Projectiles
            for p in self.projectiles[:]:
                p.update()
                if not p.active:
                    self.projectiles.remove(p)
            
            # Update Enemies
            for e in self.enemies[:]:
                e.update(self.player, self.projectiles, self.particles)
                if e.dead:
                    self.handle_enemy_death(e)
                    self.enemies.remove(e)
            
            # Update Powerups
            for pu in self.powerups[:]:
                pu.update()
                if pu.dead:
                    self.powerups.remove(pu)
                elif pu.rect.colliderect(self.player.rect):
                    pu.apply(self.player, self.projectiles, self.particles, self.sound_mgr)
                    self.powerups.remove(pu)

            # Collision Detection: Projectiles vs Entities
            self.check_collisions()

            # Update Particles
            self.particles.update()

            # Wave Management
            if not self.wave_active and len(self.enemies) == 0:
                self.wave += 1
                self.start_wave()

        elif self.state == GameState.PAUSED:
            pass # Stop updates

    def handle_input(self):
        self.keys = pygame.key.get_pressed()
        
        if self.keys[pygame.K_SPACE]:
            self.player.shoot(self.projectiles, self.particles)
            
        if self.keys[pygame.K_p]:
            self.state = GameState.PAUSED
            
        # Weapon switching with number keys
        if self.keys[pygame.K_1]: self.player.current_weapon = WeaponType.BASIC
        if self.keys[pygame.K_2]: self.player.current_weapon = WeaponType.SPREAD
        if self.keys[pygame.K_3]: self.player.current_weapon = WeaponType.RAPID
        if self.keys[pygame.K_4]: self.player.current_weapon = WeaponType.LASER
        if self.keys[pygame.K_5]: self.player.current_weapon = WeaponType.MISSILE
        if self.keys[pygame.K_6]: self.player.current_weapon = WeaponType.PLASMA

    def check_collisions(self):
        # Player Bullets vs Enemies
        for p in self.projectiles[:]:
            if p.is_enemy: continue
            
            for e in self.enemies[:]:
                if p.rect.colliderect(e.rect):
                    e.take_damage(p.damage)
                    p.active = False
                    # Hit effect
                    self.particles.emit(p.x, p.y, 5, WHITE, (1, 3), (10, 20), (2, 4))
                    
                    if e.dead:
                        self.score += e.score_value
                        self.player.gain_exp(e.exp_value)
                        self.particles.emit(e.x + e.width/2, e.y + e.height/2, 20, e.color, (2, 6), (30, 60), (3, 8))
                        self.sound_mgr.play_explosion()
                        
                        # Drop Powerup chance
                        if random.random() < 0.1:
                            p_type = random.choice(list(PowerUpType))
                            self.powerups.append(PowerUp(e.x, e.y, p_type))
                            
                    break # Bullet hits one enemy

        # Enemy Bullets/Enemies vs Player
        if self.player.invulnerable_time == 0:
            # Check Enemy Projectiles
            for p in self.projectiles[:]:
                if not p.is_enemy: continue
                if p.rect.colliderect(self.player.rect):
                    self.damage_player(p.damage)
                    p.active = False
                    
            # Check Enemy Body Collision
            for e in self.enemies[:]:
                if e.rect.colliderect(self.player.rect):
                    self.damage_player(20)
                    e.take_damage(50) # Ramming damages both
                    if e.dead:
                        self.score += e.score_value
                        self.enemies.remove(e)

    def damage_player(self, amount):
        if self.player.shield > 0:
            self.player.shield -= amount
            if self.player.shield < 0:
                self.player.health += self.player.shield # Absorb remainder
                self.player.shield = 0
        else:
            self.player.health -= amount
            
        self.player.invulnerable_time = 60 # 1 second invulnerability
        
        if self.player.health <= 0:
            self.state = GameState.GAME_OVER
            self.particles.emit(self.player.x, self.player.y, 50, RED, (2, 8), (50, 100), (4, 10))
            self.sound_mgr.play_explosion()

    def handle_enemy_death(self, enemy):
        pass # Logic handled in collision

    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw Background based on level
        if self.level_index == 0:
            bg_color = (10, 10, 30)
        elif self.level_index == 1:
            bg_color = (20, 10, 10)
        else:
            bg_color = (10, 20, 20)
        self.screen.fill(bg_color)

        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.PLAYING or self.state == GameState.PAUSED:
            self.draw_game()
            if self.state == GameState.PAUSED:
                self.draw_pause_menu()
        elif self.state == GameState.GAME_OVER:
            self.draw_game()
            self.draw_game_over()

        pygame.display.flip()

    def draw_game(self):
        # Draw Entities
        for p in self.projectiles:
            p.draw(self.screen)
            
        for e in self.enemies:
            e.draw(self.screen)
            
        for pu in self.powerups:
            pu.draw(self.screen)
            
        # Draw Player
        if self.player.invulnerable_time % 10 < 5: # Flicker effect
            pygame.draw.rect(self.screen, GREEN, self.player.rect)
            # Shield visualization
            if self.player.shield > 0:
                pygame.draw.circle(self.screen, BLUE, (self.player.x + 15, self.player.y + 15), 25, 2)

        self.particles.draw(self.screen)

        # Draw HUD
        self.draw_hud()

    def draw_hud(self):
        # Score
        text = self.font_medium.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(text, (10, 10))
        
        # Wave
        text = self.font_medium.render(f"Wave: {self.wave}", True, WHITE)
        self.screen.blit(text, (10, 40))
        
        # Level
        text = self.font_medium.render(f"Lvl: {self.player.level}", True, WHITE)
        self.screen.blit(text, (10, 70))
        
        # Health Bar
        health_pct = max(0, self.player.health / (self.player.max_health + self.player.skills["health"]*10))
        pygame.draw.rect(self.screen, RED, (SCREEN_WIDTH - 210, 10, 200, 20))
        pygame.draw.rect(self.screen, GREEN, (SCREEN_WIDTH - 210, 10, 200 * health_pct, 20))
        text = self.font_small.render(f"HP: {int(self.player.health)}", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH - 200, 15))
        
        # Shield Bar
        if self.player.shield > 0:
            shield_pct = self.player.shield / 100 # Assuming max shield ~100 for display
            pygame.draw.rect(self.screen, BLUE, (SCREEN_WIDTH - 210, 40, 200, 10))
            pygame.draw.rect(self.screen, CYAN, (SCREEN_WIDTH - 210, 40, 200 * min(shield_pct, 1), 10))
            
        # Current Weapon
        w_name = self.player.current_weapon.name
        text = self.font_small.render(f"Weapon: {w_name}", True, CYAN)
        self.screen.blit(text, (10, SCREEN_HEIGHT - 30))

    def draw_menu(self):
        title = self.font_large.render("SPACE SHOOTER PRO", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        menu_items = ["Start Game", "Load Game", "Achievements", "Quit"]
        for i, item in enumerate(menu_items):
            color = YELLOW if i == self.menu_selection else WHITE
            text = self.font_medium.render(item, True, color)
            self.screen.blit(text, (SCREEN_WIDTH//2 - 100, 300 + i * 50))

    def draw_pause_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        text = self.font_large.render("PAUSED", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 50))
        
        resume = self.font_medium.render("Press P to Resume", True, YELLOW)
        self.screen.blit(resume, (SCREEN_WIDTH//2 - resume.get_width()//2, SCREEN_HEIGHT//2 + 20))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        text = self.font_large.render("GAME OVER", True, RED)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 50))
        
        score_txt = self.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(score_txt, (SCREEN_WIDTH//2 - score_txt.get_width()//2, SCREEN_HEIGHT//2 + 20))
        
        restart = self.font_small.render("Press R to Restart, M for Menu", True, YELLOW)
        self.screen.blit(restart, (SCREEN_WIDTH//2 - restart.get_width()//2, SCREEN_HEIGHT//2 + 60))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.achievement_mgr.save()
                    
                if event.type == pygame.KEYDOWN:
                    if self.state == GameState.MENU:
                        if event.key == pygame.K_UP:
                            self.menu_selection = (self.menu_selection - 1) % 4
                        elif event.key == pygame.K_DOWN:
                            self.menu_selection = (self.menu_selection + 1) % 4
                        elif event.key == pygame.K_RETURN:
                            if self.menu_selection == 0: # Start
                                self.reset_game()
                                self.state = GameState.PLAYING
                            elif self.menu_selection == 1: # Load
                                data = self.save_mgr.load_game()
                                if data:
                                    self.player.level = data["player_level"]
                                    self.player.exp = data["player_exp"]
                                    self.player.health = data["player_health"]
                                    self.player.skills = data["player_skills"]
                                    self.player.current_weapon = WeaponType(data["current_weapon"])
                                    self.wave = data["wave"]
                                    self.score = data["score"]
                                    self.start_wave()
                                    self.state = GameState.PLAYING
                                else:
                                    print("No save file found.")
                            elif self.menu_selection == 2: # Achievements
                                self.state = GameState.ACHIEVEMENTS
                            elif self.menu_selection == 3: # Quit
                                running = False

                    elif self.state == GameState.PLAYING:
                        pass # Handled in update
                    elif self.state == GameState.PAUSED:
                        if event.key == pygame.K_p:
                            self.state = GameState.PLAYING
                    elif self.state == GameState.GAME_OVER:
                        if event.key == pygame.K_r:
                            self.reset_game()
                            self.state = GameState.PLAYING
                        elif event.key == pygame.K_m:
                            self.state = GameState.MENU
                    elif self.state == GameState.ACHIEVEMENTS:
                        if event.key == pygame.K_ESCAPE:
                            self.state = GameState.MENU

            self.update()
            self.draw()
            self.clock.tick(FPS)
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
