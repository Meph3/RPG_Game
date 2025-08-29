import random
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


# Таблица оружия
WEAPONS = {
    "Меч":              {"damage": 3, "type": "slashing"},
    "Дубина":           {"damage": 3, "type": "blunt"},
    "Кинжал":           {"damage": 2, "type": "piercing"},
    "Топор":            {"damage": 4, "type": "slashing"},
    "Копьё":            {"damage": 3, "type": "piercing"},
    "Легендарный Меч":  {"damage": 10, "type": "slashing"},
}

# Классы персонажей
CLASS_INFO = {
    "Разбойник": {"hp_per_level": 4, "start_weapon": "Кинжал"},
    "Воин":      {"hp_per_level": 5, "start_weapon": "Меч"},
    "Варвар":    {"hp_per_level": 6, "start_weapon": "Дубина"},
}

# Враги
ENEMIES = [
    {"name": "Гоблин",  "hp": 5,  "weapon": "Кинжал", "strength": 1, "dexterity": 2, "endurance": 1, "special": None, "reward": "Кинжал"},
    {"name": "Скелет",  "hp": 10, "weapon": "Дубина", "strength": 2, "dexterity": 2, "endurance": 1, "special": "double_damage_from_blunt", "reward": "Дубина"},
    {"name": "Слайм",   "hp": 8,  "weapon": "Копьё",  "strength": 1, "dexterity": 1, "endurance": 2, "special": "immune_slashing_but_strength_and_skills_work", "reward": "Копьё"},
    {"name": "Призрак", "hp": 6,  "weapon": "Меч",    "strength": 1, "dexterity": 3, "endurance": 1, "special": "sneak_attack_like_rogue", "reward": "Меч"},
    {"name": "Голем",   "hp": 10, "weapon": "Топор",  "strength": 3, "dexterity": 1, "endurance": 3, "special": "stone_skin_like_barbarian", "reward": "Топор"},
    {"name": "Дракон",  "hp": 20, "weapon": "Легендарный Меч", "strength": 3, "dexterity": 3, "endurance": 3, "special": "fire_breath_every_3_turns", "reward": "Легендарный Меч"},
]

# Сущности
@dataclass
class Entity:
    name: str
    strength: int
    dexterity: int
    endurance: int
    weapon: str
    max_hp: int
    hp: int

@dataclass
class Player(Entity):
    classes: Dict[str, int] = field(default_factory=lambda: {"Разбойник": 0, "Воин": 0, "Варвар": 0})
    total_level: int = 0
    per_battle_turn_counter: int = 0
    _got_bonus: Dict[Tuple[str, int], bool] = field(default_factory=dict)

    def calculate_max_hp(self) -> int:
        hp_from_classes = sum(CLASS_INFO[c]["hp_per_level"] * lvl for c, lvl in self.classes.items())
        hp_from_endurance = self.endurance * max(1, self.total_level)
        return hp_from_classes + hp_from_endurance

    def recalc_max_hp_after_level(self, old_max_hp: int) -> int:
        new_max = self.calculate_max_hp()
        self.max_hp = new_max
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        return new_max - old_max_hp

    def reset_battle_counters(self):
        self.per_battle_turn_counter = 0

@dataclass
class Enemy(Entity):
    special: Optional[str] = None
    reward: Optional[str] = None
    per_battle_turn_counter: int = 0


def roll_attributes() -> Tuple[int, int, int]:
    """Случайные атрибуты 1, 2 или 3"""
    return (random.randint(1, 3), random.randint(1, 3), random.randint(1, 3))

def choose_class(prompt: str = "Выберите класс:") -> str:
    options = ["Разбойник", "Воин", "Варвар"]
    print(prompt)
    for i, c in enumerate(options, 1):
        print(f"{i}. {c}")
    while True:
        pick = input("Ваш выбор (1-3): ").strip()
        if pick in ("1", "2", "3"):
            return options[int(pick) - 1]
        print("Неверный ввод, попробуйте снова.")

def print_player(p: Player):
    cls_line = ", ".join([f"{k} {v}" for k, v in p.classes.items() if v > 0])
    print(f"{p.name}: Сила={p.strength}, Ловкость={p.dexterity}, Выносливость={p.endurance} | HP {p.hp}/{p.max_hp} | Оружие: {p.weapon}")
    print(f"Классы: {cls_line} | Общий уровень: {p.total_level}")

# Механика попадания и урона
def hit_success(attacker: Entity, defender: Entity) -> bool:
    """ Шанс попадания"""
    roll = random.randint(1, attacker.dexterity + defender.dexterity)
    return not (roll <= defender.dexterity)

def base_weapon_damage(entity: Entity) -> int:
    return WEAPONS[entity.weapon]["damage"]

def weapon_type(entity: Entity) -> str:
    return WEAPONS[entity.weapon]["type"]

# Эффекты атакующего (игрок)
def apply_attacker_class_effects(attacker: Player, defender: Entity, damage: int) -> int:

    attacker.per_battle_turn_counter += 1
    tn = attacker.per_battle_turn_counter
    total_bonus = 0

    # Разбойник
    r_lvl = attacker.classes.get("Разбойник", 0)
    if r_lvl >= 1 and attacker.dexterity > getattr(defender, "dexterity", 0):
        total_bonus += 1
    if r_lvl >= 3:
        poison = max(0, tn - 1)
        if poison > 0:
            total_bonus += poison

    # Воин
    w_lvl = attacker.classes.get("Воин", 0)
    if w_lvl >= 1 and tn == 1:
        total_bonus += base_weapon_damage(attacker)

    # Варвар
    b_lvl = attacker.classes.get("Варвар", 0)
    if b_lvl >= 1:
        if tn <= 3:
            total_bonus += 2
        else:
            total_bonus -= 1

    return max(0, damage + total_bonus)

# Эффекты игрока
def apply_defender_class_effects(attacker: Entity, defender: Player, damage: int) -> int:
    # Воин — щит
    if defender.classes.get("Воин", 0) >= 2 and defender.strength > attacker.strength:
        damage -= 3
        print("🛡 Щит воина: -3 урона.")
    # Варвар — каменная кожа
    if defender.classes.get("Варвар", 0) >= 2 and damage > 0:
        before = damage
        damage = max(0, damage - defender.endurance)
        if before != damage:
            print(f"🪨 Каменная кожа варвара: -{defender.endurance} урона.")
    return max(0, damage)

# Особенности врага
def apply_enemy_specials_on_attack(attacker: Enemy, defender: Entity, damage: int) -> int:

    attacker.per_battle_turn_counter += 1
    tn = attacker.per_battle_turn_counter

    if attacker.special == "sneak_attack_like_rogue":
        if attacker.dexterity > getattr(defender, "dexterity", 0):
            damage += 1
            print("👻 Призрак: скрытая атака (+1).")
    if attacker.special == "fire_breath_every_3_turns":
        if tn % 3 == 0:
            damage += 3
            print("🔥 Дракон использует дыхание: +3 урона.")
    return max(0, damage)

# Особенности врага при защите
def apply_enemy_specials_on_defense(attacker: Entity, defender: Enemy, damage: int) -> int:

    # Слайм
    if defender.special == "immune_slashing_but_strength_and_skills_work" and weapon_type(attacker) == "slashing":
        weapon_part = base_weapon_damage(attacker)
        if weapon_part > 0:
            damage = max(0, damage - weapon_part)
            print("🧪 Слайм: рубящий урон оружия не прошёл (сила и умения работают).")

    # Скелет
    if defender.special == "double_damage_from_blunt" and weapon_type(attacker) == "blunt":
        damage *= 2
        print("💀 Скелет уязвим к дробящему: x2 урона.")

    # Голем
    if defender.special == "stone_skin_like_barbarian" and damage > 0:
        before = damage
        damage = max(0, damage - defender.endurance)
        if before != damage:
            print(f"🗿 Голем: -{defender.endurance} урона (каменная кожа).")

    return max(0, damage)

# Выполнение атаки
def perform_attack(attacker: Entity, defender: Entity, is_player_attacking: bool) -> bool:

    # 1) попадание
    if not hit_success(attacker, defender):
        print(f"{attacker.name} промахнулся по {defender.name}.")
        return False

    # 2) базовый урон
    damage = base_weapon_damage(attacker) + attacker.strength

    # 3) эффекты атакующего
    if is_player_attacking and isinstance(attacker, Player):
        damage = apply_attacker_class_effects(attacker, defender, damage)
    elif (not is_player_attacking) and isinstance(attacker, Enemy):
        damage = apply_enemy_specials_on_attack(attacker, defender, damage)

    # 4) эффекты цели
    if is_player_attacking and isinstance(defender, Enemy):
        damage = apply_enemy_specials_on_defense(attacker, defender, damage)
    elif (not is_player_attacking) and isinstance(defender, Player):
        damage = apply_defender_class_effects(attacker, defender, damage)

    # 5) применение урона
    if damage <= 0:
        print(f"{attacker.name} ударил {defender.name}, но урон не прошёл.")
        return False

    defender.hp -= damage
    print(f"{attacker.name} наносит {damage} урона по {defender.name}. (HP цели: {max(0, defender.hp)}/{defender.max_hp})")
    if defender.hp <= 0:
        print(f"☠️ {defender.name} пал.")
        return True
    return False

# Бой
def determine_first_actor(player: Player, enemy: Enemy) -> str:
    return "player" if player.dexterity >= enemy.dexterity else "enemy"

def battle(player: Player, enemy_proto: Dict) -> bool:

    enemy = Enemy(
        name=enemy_proto["name"],
        strength=enemy_proto["strength"],
        dexterity=enemy_proto["dexterity"],
        endurance=enemy_proto["endurance"],
        weapon=enemy_proto["weapon"],
        max_hp=enemy_proto["hp"],
        hp=enemy_proto["hp"],
        special=enemy_proto.get("special"),
        reward=enemy_proto.get("reward"),
    )

    player.per_battle_turn_counter = 0
    enemy.per_battle_turn_counter = 0

    print("\n==============================")
    print(f"⚔️ На вас напал {enemy.name} (HP {enemy.hp}/{enemy.max_hp}), вооружён: {enemy.weapon}")
    print("==============================")

    turn_owner = determine_first_actor(player, enemy)
    print(f"Первым ходит: {'Игрок' if turn_owner == 'player' else enemy.name}")

    while player.hp > 0 and enemy.hp > 0:
        if turn_owner == "player":
            if perform_attack(player, enemy, is_player_attacking=True):
                return True
            turn_owner = "enemy"
        else:
            if perform_attack(enemy, player, is_player_attacking=False):
                return False
            turn_owner = "player"

    return player.hp > 0


# Ап уровня
def choose_class_for_levelup() -> str:
    options = ["Разбойник", "Воин", "Варвар"]
    print("\nВыберите класс для повышения уровня:")
    for i, c in enumerate(options, 1):
        print(f"{i}. {c}")
    while True:
        pick = input("Ваш выбор (1-3): ").strip()
        if pick in ("1", "2", "3"):
            return options[int(pick) - 1]
        print("Попробуйте снова.")
# Бонусы от классов
def apply_threshold_passives(player: Player):

    for class_name, lvl in player.classes.items():
        if class_name == "Разбойник" and lvl >= 2 and not player._got_bonus.get(("Разбойник", 2), False):
            player.dexterity += 1
            player._got_bonus[("Разбойник", 2)] = True
            print("🎯 Разбойник(2): Ловкость +1.")
        if class_name == "Воин" and lvl >= 3 and not player._got_bonus.get(("Воин", 3), False):
            player.strength += 1
            player._got_bonus[("Воин", 3)] = True
            print("💪 Воин(3): Сила +1.")
        if class_name == "Варвар" and lvl >= 3 and not player._got_bonus.get(("Варвар", 3), False):
            player.endurance += 1
            player._got_bonus[("Варвар", 3)] = True
            print("🪓 Варвар(3): Выносливость +1.")

def level_up(player: Player):
    chosen = choose_class_for_levelup()
    player.classes[chosen] += 1
    player.total_level += 1

    apply_threshold_passives(player)

    old_max = player.max_hp
    gain = player.recalc_max_hp_after_level(old_max)
    print(f"\n🎉 Повышен уровень в {chosen}. Теперь {chosen} {player.classes[chosen]}.")
    if gain != 0:
        print(f"➕ Максимальное здоровье изменилось на {gain}. Текущее HP: {player.hp}/{player.max_hp}")
    else:
        print(f"Максимальное здоровье: {player.max_hp}. Текущее HP: {player.hp}/{player.max_hp}")


def main():
    print("=== Зачистка подземелья ===")
    while True:
        s, d, e = roll_attributes()
        print("\nСоздание персонажа")
        name = input("Введите имя персонажа: ").strip() or "Герой"
        print(f"Выпали начальные статы: Сила={s}, Ловкость={d}, Выносливость={e}")
        chosen = choose_class("Выберите стартовый класс:")
        player = Player(
            name=name,
            strength=s,
            dexterity=d,
            endurance=e,
            weapon=CLASS_INFO[chosen]["start_weapon"],
            max_hp=0,
            hp=0,
        )
        player.classes = {"Разбойник": 0, "Воин": 0, "Варвар": 0}
        player.classes[chosen] = 1
        player.total_level = 1
        player.max_hp = player.calculate_max_hp()
        player.hp = player.max_hp

        print("\nВаш персонаж:")
        print_player(player)

        win_streak = 0

        while True:
            enemy_proto = random.choice(ENEMIES)
            victory = battle(player, enemy_proto)

            if victory:
                win_streak += 1
                print(f"\n🏆 Победа! Побед подряд: {win_streak}")

                player.hp = player.max_hp
                print(f"🩹 Здоровье восстановлено: {player.hp}/{player.max_hp}")

                level_up(player)

                reward = enemy_proto.get("reward")
                if reward and reward in WEAPONS:
                    w = WEAPONS[reward]
                    print(f"\nС поверженного врага можно подобрать: {reward} ({w['damage']} урона, тип {w['type']})")
                    ans = input("Заменить текущее оружие? (y/n): ").strip().lower()
                    if ans == "y":
                        player.weapon = reward
                        print(f"🔁 Экипировано: {player.weapon}")

                player.reset_battle_counters()

                if win_streak >= 3:
                    print("\n🎉 Вы победили 3 монстра подряд — игра пройдена! Поздравляю!")
                    break
            else:
                print("\n💀 Вы погибли. Игра окончена для этого персонажа.")
                break

        again = input("\nСоздать нового персонажа? (y/n): ").strip().lower()
        if again != "y":
            print("Спасибо за игру!")
            break

if __name__ == "__main__":
    main()
