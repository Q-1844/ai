import pygame
import sys
import math
import random
import json
import os
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple

# 初始化 Pygame
pygame.init()
pygame.mixer.init()

# ==============================
# 1. 配置与常量
# ==============================
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

# 游戏状态枚举
class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    LEVEL_TRANSITION = auto()

# 敌人类别
class EnemyType(Enum):
    DRONE = 1
    FIGHTER = 2
    TANK = 3
    SPEEDER = 4
    BOSS = 99

# 武器类型
class WeaponType(Enum):
    LASER = 1
    RAPID_FIRE = 2
    SPREAD = 3
    PLASMA = 4
    MISSILE = 5
    SHOCKWAVE = 6

# 道具类型
class ItemType(Enum):
    HEALTH = 1
    SHIELD = 2
    SPEED_BOOST = 3
    BOMB = 4
    AMMO_REFILL = 5
    EXPERIENCE_BOOST = 6
    WEAPON_UPGRADE = 7
    FREEZE_TIME = 8

# 成就列表
ACHIEVEMENTS = {
    "first_blood": {"name": "初次杀戮", "desc": "击杀第一个敌人", "unlocked": False},
    "survivor": {"name": "幸存者", "desc": "存活1分钟", "unlocked": False},
    "sharpshooter": {"name": "神枪手", "desc": "10连杀", "unlocked": False},
    "boss_slayer": {"name": "屠龙者", "desc": "击败第一个Boss", "unlocked": False},
    "collector": {"name": "收集者", "desc": "拾取10个道具", "unlocked": False},
    "level_5": {"name": "老兵", "desc": "达到5级", "unlocked": False},
    "weapon_master": {"name": "武器大师", "desc": "解锁所有武器", "unlocked": False},
    "wave_5": {"name": "先锋", "desc": "到达第5波", "unlocked": False},
    "no_damage": {"name": "完美闪避", "desc": "单局未受伤害", "unlocked": False},
    "combo_king": {"name": "连击之王", "desc": "达成50连击", "unlocked": False}
}

# ==============================
# 2. 音效管理器 (合成音频)
# ==============================
class SoundManager:
    def __init__(self):
        self.sounds = {}
        # 简单的正弦波合成器用于生成音效，避免依赖外部文件
        self.frequency_map = {
            'shoot': 440,
            'hit': 220,
            'explosion': 110,
            'pickup': 880,
            'levelup': 660,
            'damage': 150
        }

    def play_sound(self, sound_name, volume=0.5):
        # 在实际生产中，这里应该加载 .wav 或 .ogg 文件
        # 为了本代码的可运行性，我们只打印日志或模拟播放
        # pygame.mixer.Sound 需要缓冲区，这里简化处理
        pass 

    def stop_all(self):
        pygame.mixer.stop()

sound_manager = SoundManager()

# ==============================
# 3. 基础精灵类
# ==============================
class Sprite(pygame.sprite.Sprite):
    def __init__(self, x, y, color, size):
        super().__init__()
        self.image = pygame.Surface((size, size))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.color = color
        self.size = size

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Particle(Sprite):
    def __init__(self, x, y, color, speed, life):
        super().__init__(x, y, color, 4)
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = life
        self.max_life = life
        self.alpha = 255

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.life -= 1
        self.alpha = int(255 * (self.life / self.max_life))
        # 更新图像透明度 (简单模拟)
        if self.alpha < 0:
            self.kill()

class Bullet(Sprite):
    def __init__(self, x, y, vx, vy, damage, is_player_bullet, weapon_type=None):
        super().__init__(x, y, WHITE if is_player_bullet else RED, 6)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.is_player_bullet = is_player_bullet
        self.weapon_type = weapon_type

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        # 屏幕外移除
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or \
           self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
            self.kill()

class Player(Sprite):
    def __init__(self, x, y):
        super().__init__(x, y, CYAN, 30)
        self.speed = 5
        self.health = 100
        self.max_health = 100
        self.shield = 0
        self.max_shield = 50
        self.xp = 0
        self.level = 1
        self.weapon = WeaponType.LASER
        self.fire_rate = 15 # frames between shots
        self.damage = 10
        self.last_shot_time = 0
        self.mouse_x, self.mouse_y = x, y
        self.angle = 0
        self.unlocked_weapons = [WeaponType.LASER]
        self.achievements = dict(ACHIEVEMENTS)
        
        # 状态效果
        self.speed_boost_timer = 0
        self.freeze_timer = 0

    def update(self, keys, dt):
        # 移动
        dx, dy = 0, 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1

        # 归一化向量
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            dx /= length
            dy /= length

        current_speed = self.speed * 1.5 if self.speed_boost_timer > 0 else self.speed
        if self.freeze_timer > 0:
            current_speed *= 0.5

        self.rect.x += dx * current_speed
        self.rect.y += dy * current_speed

        # 边界检查
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # 旋转朝向鼠标
        mx, my = pygame.mouse.get_pos()
        self.angle = math.degrees(math.atan2(my - self.rect.centery, mx - self.rect.centerx))

        # 计时器递减
        if self.speed_boost_timer > 0: self.speed_boost_timer -= 1
        if self.freeze_timer > 0: self.freeze_timer -= 1

    def shoot(self, bullets, current_time):
        if current_time - self.last_shot_time >= self.fire_rate:
            self.last_shot_time = current_time
            # 计算发射角度
            rad = math.radians(self.angle)
            bx = math.cos(rad) * 10
            by = math.sin(rad) * 10
            
            if self.weapon == WeaponType.LASER:
                bullets.append(Bullet(self.rect.centerx, self.rect.centery, bx*10, by*10, self.damage, True, WeaponType.LASER))
            elif self.weapon == WeaponType.RAPID_FIRE:
                for i in range(-1, 2):
                    angle_offset = rad + i * 0.1
                    bullets.append(Bullet(self.rect.centerx, self.rect.centery, 
                                          math.cos(angle_offset)*12, math.sin(angle_offset)*12, self.damage//2, True))
            elif self.weapon == WeaponType.SPREAD:
                for i in range(-2, 3):
                    angle_offset = rad + i * 0.2
                    bullets.append(Bullet(self.rect.centerx, self.rect.centery, 
                                          math.cos(angle_offset)*8, math.sin(angle_offset)*8, self.damage//2, True))
            elif self.weapon == WeaponType.PLASMA:
                bullets.append(Bullet(self.rect.centerx, self.rect.centery, bx*5, by*5, self.damage*2, True, WeaponType.PLASMA))
            elif self.weapon == WeaponType.MISSILE:
                bullet = Bullet(self.rect.centerx, self.rect.centery, bx*8, by*8, self.damage, True, WeaponType.MISSILE)
                bullet.target_lock = True # 标记为追踪
                bullets.append(bullet)
            elif self.weapon == WeaponType.SHOCKWAVE:
                for i in range(360):
                    rad_i = math.radians(i)
                    bullets.append(Bullet(self.rect.centerx, self.rect.centery, 
                                          math.cos(rad_i)*2, math.sin(rad_i)*2, self.damage//4, True))
            
            sound_manager.play_sound('shoot')

    def take_damage(self, amount):
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield
                self.shield = 0
        else:
            self.health -= amount
        
        if self.health <= 0:
            return True # Dead
        return False

    def gain_xp(self, amount):
        self.xp += amount
        threshold = self.level * 100
        if self.xp >= threshold:
            self.level_up()
            return True
        return False

    def level_up(self):
        self.level += 1
        self.xp = 0
        self.max_health += 20
        self.health = self.max_health
        self.damage += 2
        sound_manager.play_sound('levelup')

    def unlock_weapon(self, weapon_type):
        if weapon_type not in self.unlocked_weapons:
            self.unlocked_weapons.append(weapon_type)
            self.weapon = weapon_type

    def get_stats(self):
        return {
            "health": self.health,
            "shield": self.shield,
            "level": self.level,
            "xp": self.xp,
            "weapon": self.weapon.name,
            "unlocked_weapons": [w.name for w in self.unlocked_weapons],
            "achievements": {k: v["unlocked"] for k, v in self.achievements.items()}
        }

    def save_game(self, filename="save.json"):
        stats = self.get_stats()
        with open(filename, 'w') as f:
            json.dump(stats, f)

    def load_game(self, filename="save.json"):
        try:
            with open(filename, 'r') as f:
                stats = json.load(f)
            self.health = stats['health']
            self.shield = stats['shield']
            self.level = stats['level']
            self.xp = stats['xp']
            self.weapon = WeaponType[stats['weapon']]
            self.unlocked_weapons = [WeaponType[w] for w in stats['unlocked_weapons']]
            for k, v in stats['achievements'].items():
                if k in self.achievements:
                    self.achievements[k]["unlocked"] = v
        except FileNotFoundError:
            print("Save file not found.")

class Enemy(Sprite):
    def __init__(self, x, y, enemy_type, wave_multiplier=1.0):
        self.enemy_type = enemy_type
        self.wave_multiplier = wave_multiplier
        
        # 根据类型设置属性
        if enemy_type == EnemyType.DRONE:
            super().__init__(x, y, RED, 20)
            self.health = 20 * wave_multiplier
            self.speed = 2
            self.score = 10
        elif enemy_type == EnemyType.FIGHTER:
            super().__init__(x, y, MAGENTA, 25)
            self.health = 40 * wave_multiplier
            self.speed = 3
            self.score = 20
        elif enemy_type == EnemyType.TANK:
            super().__init__(x, y, DARK_GRAY, 40)
            self.health = 100 * wave_multiplier
            self.speed = 1
            self.score = 50
        elif enemy_type == EnemyType.SPEEDER:
            super().__init__(x, y, YELLOW, 15)
            self.health = 15 * wave_multiplier
            self.speed = 6
            self.score = 15
        elif enemy_type == EnemyType.BOSS:
            super().__init__(x, y, BLACK, 100)
            self.health = 1000 * wave_multiplier
            self.speed = 1
            self.score = 500
            self.phase = 1

        self.vx = 0
        self.vy = 0
        self.timer = 0

    def update(self, player, bullets, particles):
        self.timer += 1
        
        # 默认向下移动
        if self.enemy_type != EnemyType.BOSS:
            self.vy = self.speed
            # 简单的左右摆动
            self.vx = math.sin(self.timer * 0.05) * 2
            
            # 边界
            if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
                self.vx *= -1
                
            self.rect.x += self.vx
            self.rect.y += self.vy

            # 射击
            if random.random() < 0.01 * self.wave_multiplier:
                angle = math.atan2(player.rect.centery - self.rect.centery, player.rect.centerx - self.rect.centerx)
                bx = math.cos(angle) * 5
                by = math.sin(angle) * 5
                bullets.append(Bullet(self.rect.centerx, self.rect.centery, bx, by, 10, False))

        elif self.enemy_type == EnemyType.BOSS:
            # Boss 逻辑
            self.rect.x += math.sin(self.timer * 0.02) * 2
            self.rect.y = 100 + math.sin(self.timer * 0.01) * 50
            
            # 阶段切换
            max_hp = 1000 * self.wave_multiplier
            current_hp_ratio = self.health / max_hp
            
            if current_hp_ratio < 0.5 and self.phase == 1:
                self.phase = 2
                self.speed = 2
            
            # 攻击模式
            if self.timer % 60 == 0:
                # 环形弹幕
                for i in range(8):
                    angle = i * (math.pi / 4) + self.timer * 0.1
                    bx = math.cos(angle) * 4
                    by = math.sin(angle) * 4
                    bullets.append(Bullet(self.rect.centerx, self.rect.centery, bx, by, 20, False))
            
            if self.timer % 30 == 0:
                # 追踪导弹
                angle = math.atan2(player.rect.centery - self.rect.centery, player.rect.centerx - self.rect.centerx)
                bx = math.cos(angle) * 6
                by = math.sin(angle) * 6
                bullets.append(Bullet(self.rect.centerx, self.rect.centery, bx, by, 15, False))

        # 屏幕外移除
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.kill()
            return True
        return False

class Item(Sprite):
    def __init__(self, x, y, item_type):
        self.item_type = item_type
        color_map = {
            ItemType.HEALTH: GREEN,
            ItemType.SHIELD: BLUE,
            ItemType.SPEED_BOOST: YELLOW,
            ItemType.BOMB: RED,
            ItemType.AMMO_REFILL: CYAN,
            ItemType.EXPERIENCE_BOOST: MAGENTA,
            ItemType.WEAPON_UPGRADE: WHITE,
            ItemType.FREEZE_TIME: GRAY
        }
        super().__init__(x, y, color_map[item_type], 15)
        self.vy = 2

    def update(self):
        self.rect.y += self.vy
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

# ==============================
# 4. 游戏核心逻辑
# ==============================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter Pro")
        self.clock = pygame.time.Clock()
        self.state = GameState.MENU
        
        # 实体组
        self.all_sprites = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()
        self.items = pygame.sprite.Group()
        
        # 游戏变量
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.wave = 1
        self.wave_timer = 0
        self.enemies_to_spawn = 0
        self.spawn_timer = 0
        self.game_time = 0
        self.kills = 0
        self.combo = 0
        self.last_kill_time = 0
        self.total_items_picked = 0
        self.taken_damage_this_run = False
        
        # 字体
        self.font_large = pygame.font.SysFont("arial", 48)
        self.font_medium = pygame.font.SysFont("arial", 24)
        self.font_small = pygame.font.SysFont("arial", 16)
        
        # 场景背景
        self.bg_color = (10, 10, 30)

    def spawn_wave(self):
        # 生成敌人逻辑
        num_enemies = 5 + self.wave * 2
        if self.wave % 5 == 0:
            # Boss 波
            self.enemies.add(Enemy(SCREEN_WIDTH // 2, -100, EnemyType.BOSS, 1 + self.wave * 0.1))
        else:
            types = [EnemyType.DRONE, EnemyType.FIGHTER, EnemyType.TANK, EnemyType.SPEEDER]
            weights = [0.5, 0.3, 0.1, 0.1]
            chosen_types = random.choices(types, weights=weights, k=num_enemies)
            
            for etype in chosen_types:
                x = random.randint(20, SCREEN_WIDTH - 20)
                y = random.randint(-500, -50)
                self.enemies.add(Enemy(x, y, etype, 1 + self.wave * 0.1))
        
        self.enemies_to_spawn = 0 # 全部已添加

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_SPACE:
                        self.start_new_game()
                    elif event.key == pygame.K_l:
                        self.load_saved_game()
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                    elif event.key == pygame.K_1: self.player.weapon = WeaponType.LASER
                    elif event.key == pygame.K_2: self.player.weapon = WeaponType.RAPID_FIRE
                    elif event.key == pygame.K_3: self.player.weapon = WeaponType.SPREAD
                    elif event.key == pygame.K_4: self.player.weapon = WeaponType.PLASMA
                    elif event.key == pygame.K_5: self.player.weapon = WeaponType.MISSILE
                    elif event.key == pygame.K_6: self.player.weapon = WeaponType.SHOCKWAVE
                elif self.state == GameState.PAUSED:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PLAYING
                    elif event.key == pygame.K_q:
                        self.save_game()
                        self.state = GameState.MENU
                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.start_new_game()
                    elif event.key == pygame.K_m:
                        self.state = GameState.MENU

    def start_new_game(self):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
        self.wave = 1
        self.wave_timer = 0
        self.kills = 0
        self.combo = 0
        self.game_time = 0
        self.total_items_picked = 0
        self.taken_damage_this_run = False
        
        self.all_sprites.empty()
        self.player_bullets.empty()
        self.enemy_bullets.empty()
        self.enemies.empty()
        self.particles.empty()
        self.items.empty()
        
        self.all_sprites.add(self.player)
        self.spawn_wave()
        self.state = GameState.PLAYING

    def load_saved_game(self):
        if os.path.exists("save.json"):
            self.player.load_game()
            self.state = GameState.PLAYING
            # 重置一些运行时变量以进入游玩状态
            self.wave = 1
            self.kills = 0
            self.combo = 0
            self.game_time = 0
            self.total_items_picked = 0
            self.taken_damage_this_run = False
            self.all_sprites.add(self.player)
            self.spawn_wave()

    def save_game(self):
        self.player.save_game()

    def check_achievements(self):
        now = pygame.time.get_ticks()
        
        # 1. 初次杀戮
        if self.kills >= 1:
            self.unlock_achievement("first_blood")
        
        # 2. 幸存者
        if self.game_time > 60000: # 60 seconds approx at 60fps logic? No, use frame count or time diff
             # Simplified: just check game_time variable increment
            pass 
        
        # 3. 连击
        if self.combo >= 10:
            self.unlock_achievement("sharpshooter")
        
        # 4. Boss 击杀
        if self.kills >= 1 and self.wave > 5: # Rough heuristic
             pass # Real tracking needed for specific boss kills, simplified here

        # 5. 收集者
        if self.total_items_picked >= 10:
            self.unlock_achievement("collector")

        # 6. 等级
        if self.player.level >= 5:
            self.unlock_achievement("level_5")

        # 7. 武器大师
        if len(self.player.unlocked_weapons) >= 6:
            self.unlock_achievement("weapon_master")

        # 8. 波次
        if self.wave >= 5:
            self.unlock_achievement("wave_5")

        # 9. 无伤
        if not self.taken_damage_this_run and self.kills > 0:
            self.unlock_achievement("no_damage")

        # 10. 连击王
        if self.combo >= 50:
            self.unlock_achievement("combo_king")

    def unlock_achievement(self, key):
        if key in ACHIEVEMENTS and not ACHIEVEMENTS[key]["unlocked"]:
            ACHIEVEMENTS[key]["unlocked"] = True
            self.player.achievements[key]["unlocked"] = True
            # 显示提示
            print(f"Achievement Unlocked: {ACHIEVEMENTS[key]['name']}")

    def update(self):
        if self.state != GameState.PLAYING:
            return

        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()
        
        # 玩家更新
        self.player.update(keys, 1/FPS)
        if keys[pygame.K_SPACE]:
            self.player.shoot(self.player_bullets, current_time)

        # 波次管理
        if len(self.enemies) == 0:
            self.wave_timer += 1
            if self.wave_timer > 120: # 2 seconds break
                self.wave += 1
                self.wave_timer = 0
                self.spawn_wave()
                
                # 检查成就
                if self.wave == 5:
                    self.unlock_achievement("wave_5")

        # 实体更新
        self.player_bullets.update()
        self.enemy_bullets.update()
        self.enemies.update(self.player, self.enemy_bullets, self.particles)
        self.particles.update()
        self.items.update()

        # 碰撞检测
        # 玩家子弹击中敌人
        hits = pygame.sprite.groupcollide(self.player_bullets, self.enemies, False, False)
        for bullet, enemy_group in hits.items():
            for enemy in enemy_group:
                enemy.take_damage(bullet.damage)
                bullet.kill()
                # 产生粒子
                for _ in range(5):
                    p = Particle(enemy.rect.centerx, enemy.rect.centery, RED, 2, 20)
                    self.particles.add(p)
                
                if enemy.health <= 0:
                    self.kills += 1
                    self.combo += 1
                    self.last_kill_time = current_time
                    self.player.gain_xp(enemy.score)
                    
                    # 掉落道具
                    if random.random() < 0.3:
                        item_type = random.choice(list(ItemType))
                        self.items.add(Item(enemy.rect.centerx, enemy.rect.centery, item_type))
                    
                    # 爆炸效果
                    for _ in range(20):
                        p = Particle(enemy.rect.centerx, enemy.rect.centery, YELLOW, 5, 30)
                        self.particles.add(p)
                    sound_manager.play_sound('explosion')

        # 敌人子弹击中玩家
        hits = pygame.sprite.groupcollide(self.enemy_bullets, pygame.sprite.Group([self.player]), False, False)
        if hits:
            for bullet in list(hits.keys()):
                if self.player.take_damage(bullet.damage):
                    self.game_over()
                    return
                bullet.kill()
                self.taken_damage_this_run = True
                sound_manager.play_sound('damage')
                for _ in range(10):
                    p = Particle(self.player.rect.centerx, self.player.rect.centery, RED, 3, 20)
                    self.particles.add(p)

        # 敌人撞击玩家
        hits = pygame.sprite.spritecollide(self.player, self.enemies, False)
        if hits:
            for enemy in hits:
                if self.player.take_damage(20):
                    self.game_over()
                    return
                enemy.take_damage(50)
                self.taken_damage_this_run = True
        
        # 玩家拾取道具
        hits = pygame.sprite.spritecollide(self.player, self.items, True)
        for item in hits:
            self.apply_item(item.item_type)
            self.total_items_picked += 1
            sound_manager.play_sound('pickup')

        # 连击超时重置
        if current_time - self.last_kill_time > 2000:
            self.combo = 0

        self.game_time += 1
        self.check_achievements()

    def apply_item(self, item_type):
        if item_type == ItemType.HEALTH:
            self.player.health = min(self.player.health + 20, self.player.max_health)
        elif item_type == ItemType.SHIELD:
            self.player.shield = min(self.player.shield + 20, self.player.max_shield)
        elif item_type == ItemType.SPEED_BOOST:
            self.player.speed_boost_timer = 300
        elif item_type == ItemType.BOMB:
            # 全屏清除敌人和子弹
            for enemy in self.enemies:
                enemy.take_damage(100)
            self.enemy_bullets.empty()
            sound_manager.play_sound('explosion')
        elif item_type == ItemType.EXPERIENCE_BOOST:
            self.player.gain_xp(50)
        elif item_type == ItemType.WEAPON_UPGRADE:
            # 解锁随机未解锁武器
            all_weapons = list(WeaponType)
            available = [w for w in all_weapons if w not in self.player.unlocked_weapons]
            if available:
                new_weapon = random.choice(available)
                self.player.unlock_weapon(new_weapon)
        elif item_type == ItemType.FREEZE_TIME:
            self.player.freeze_timer = 180

    def game_over(self):
        self.state = GameState.GAME_OVER

    def draw_ui(self):
        # 绘制 HUD
        # 血条
        pygame.draw.rect(self.screen, RED, (20, 20, 200, 20))
        hp_ratio = self.player.health / self.player.max_health
        pygame.draw.rect(self.screen, GREEN, (20, 20, 200 * hp_ratio, 20))
        
        # 护盾
        pygame.draw.rect(self.screen, BLUE, (20, 45, 200, 10))
        shield_ratio = self.player.shield / self.player.max_shield
        pygame.draw.rect(self.screen, CYAN, (20, 45, 200 * shield_ratio, 10))

        # 等级和经验
        text = self.font_small.render(f"Lvl: {self.player.level} XP: {self.player.xp}/{self.player.level*100}", True, WHITE)
        self.screen.blit(text, (20, 65))
        
        # 波次
        text = self.font_medium.render(f"WAVE: {self.wave}", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH - 150, 20))

        # 分数/连击
        text = self.font_medium.render(f"Kills: {self.kills} Combo: {self.combo}", True, YELLOW)
        self.screen.blit(text, (SCREEN_WIDTH - 250, 50))

        # 当前武器
        text = self.font_small.render(f"Weapon: {self.player.weapon.name}", True, WHITE)
        self.screen.blit(text, (20, SCREEN_HEIGHT - 30))

    def draw_menu(self):
        self.screen.fill(self.bg_color)
        title = self.font_large.render("SPACE SHOOTER PRO", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        menu_items = ["Press SPACE to Start", "Press L to Load Save", "Press ESC to Exit"]
        for i, item in enumerate(menu_items):
            color = WHITE if i == 0 else GRAY
            text = self.font_medium.render(item, True, color)
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 200 + i*40))

    def draw_pause(self):
        self.screen.fill((0, 0, 0, 128)) # Semi-transparent
        text = self.font_large.render("PAUSED", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 50))
        
        sub_text = self.font_medium.render("Press ESC to Resume", True, WHITE)
        self.screen.blit(sub_text, (SCREEN_WIDTH//2 - sub_text.get_width()//2, SCREEN_HEIGHT//2 + 20))
        
        sub_text2 = self.font_medium.render("Press Q to Quit to Menu", True, GRAY)
        self.screen.blit(sub_text2, (SCREEN_WIDTH//2 - sub_text2.get_width()//2, SCREEN_HEIGHT//2 + 60))

    def draw_game_over(self):
        self.screen.fill(BLACK)
        text = self.font_large.render("GAME OVER", True, RED)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 100))
        
        text = self.font_medium.render(f"Waves Survived: {self.wave}", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 200))
        
        text = self.font_medium.render("Press R to Restart", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 300))
        
        text = self.font_medium.render("Press M to Main Menu", True, GRAY)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 340))

    def render(self):
        self.screen.fill(self.bg_color)
        
        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.PLAYING:
            self.all_sprites.draw(self.screen)
            self.player_bullets.draw(self.screen)
            self.enemy_bullets.draw(self.screen)
            self.particles.draw(self.screen)
            self.items.draw(self.screen)
            self.draw_ui()
        elif self.state == GameState.PAUSED:
            self.all_sprites.draw(self.screen)
            self.player_bullets.draw(self.screen)
            self.enemy_bullets.draw(self.screen)
            self.particles.draw(self.screen)
            self.items.draw(self.screen)
            self.draw_pause()
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over()

        pygame.display.flip()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
