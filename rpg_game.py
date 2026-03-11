import json
import math
import os
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# =========================
# Utility
# =========================

def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def roll(chance_percent: float) -> bool:
    return random.random() < (chance_percent / 100.0)


# =========================
# Core Data Models
# =========================

@dataclass
class Stats:
    strength: int = 5
    agility: int = 5
    endurance: int = 5
    intelligence: int = 5
    wisdom: int = 5
    luck: int = 5

    def to_dict(self) -> Dict[str, int]:
        return {
            "strength": self.strength,
            "agility": self.agility,
            "endurance": self.endurance,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "luck": self.luck,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Stats":
        return cls(**data)

    def add(self, other: "Stats") -> "Stats":
        return Stats(
            strength=self.strength + other.strength,
            agility=self.agility + other.agility,
            endurance=self.endurance + other.endurance,
            intelligence=self.intelligence + other.intelligence,
            wisdom=self.wisdom + other.wisdom,
            luck=self.luck + other.luck,
        )


@dataclass
class Item:
    name: str
    item_type: str  # weapon, armor, consumable, trinket
    value: int = 0
    stat_bonus: Dict[str, int] = field(default_factory=dict)
    heal_amount: int = 0
    mana_restore: int = 0
    stamina_restore: int = 0
    slot: Optional[str] = None  # weapon, armor, accessory

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Item":
        return cls(**data)


@dataclass
class Skill:
    name: str
    skill_type: str  # physical, magical, utility
    mana_cost: int = 0
    stamina_cost: int = 0
    power: float = 1.0
    cooldown: int = 0
    description: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Skill":
        return cls(**data)


# =========================
# Class Templates
# =========================

CLASS_TEMPLATES = {
    "Warrior": {
        "base_stats": Stats(strength=9, agility=6, endurance=9, intelligence=3, wisdom=4, luck=5),
        "skills": [
            Skill("Power Strike", "physical", stamina_cost=12, power=1.8, cooldown=2,
                  description="A heavy strike boosted by Strength."),
            Skill("Second Wind", "utility", power=0.0, cooldown=4,
                  description="Recover stamina mid-battle."),
        ],
    },
    "Rogue": {
        "base_stats": Stats(strength=6, agility=10, endurance=6, intelligence=4, wisdom=5, luck=8),
        "skills": [
            Skill("Quick Stab", "physical", stamina_cost=8, power=1.4, cooldown=1,
                  description="Fast attack with high crit synergy."),
            Skill("Shadowstep", "utility", stamina_cost=10, power=0.0, cooldown=3,
                  description="Increase dodge chance temporarily."),
        ],
    },
    "Mage": {
        "base_stats": Stats(strength=3, agility=5, endurance=5, intelligence=10, wisdom=9, luck=5),
        "skills": [
            Skill("Firebolt", "magical", mana_cost=12, power=1.8, cooldown=1,
                  description="A basic offensive spell."),
            Skill("Meditate", "utility", power=0.0, cooldown=3,
                  description="Restore mana in combat."),
        ],
    },
    "Cleric": {
        "base_stats": Stats(strength=4, agility=4, endurance=7, intelligence=7, wisdom=10, luck=5),
        "skills": [
            Skill("Smite", "magical", mana_cost=10, power=1.5, cooldown=1,
                  description="Holy damage scaling with Intelligence."),
            Skill("Heal", "utility", mana_cost=14, power=1.6, cooldown=2,
                  description="Restore health based on Wisdom and Intelligence."),
        ],
    },
}


# =========================
# Base Character
# =========================

class Character:
    def __init__(self, name: str, stats: Stats, level: int = 1):
        self.name = name
        self.base_stats = stats
        self.level = level
        self.max_hp = self.calculate_max_hp()
        self.hp = self.max_hp
        self.max_mana = self.calculate_max_mana()
        self.mana = self.max_mana
        self.max_stamina = self.calculate_max_stamina()
        self.stamina = self.max_stamina
        self.cooldowns: Dict[str, int] = {}
        self.temp_effects: Dict[str, int] = {}

    def calculate_max_hp(self) -> int:
        return 50 + (self.base_stats.endurance * 12) + (self.level * 8)

    def calculate_max_mana(self) -> int:
        return 20 + (self.base_stats.intelligence * 10) + (self.level * 4)

    def calculate_max_stamina(self) -> int:
        return 30 + (self.base_stats.endurance * 8) + (self.level * 5)

    def physical_attack_power(self) -> int:
        return int(self.base_stats.strength * 2.5 + self.level * 2)

    def magic_attack_power(self) -> int:
        return int(self.base_stats.intelligence * 2.7 + self.level * 2)

    def defense(self) -> int:
        return int(self.base_stats.endurance * 1.8 + self.level)

    def crit_chance(self) -> float:
        return min(40.0, 5.0 + self.base_stats.luck * 1.5)

    def dodge_chance(self) -> float:
        base = 3.0 + self.base_stats.agility * 1.2
        if self.temp_effects.get("shadowstep", 0) > 0:
            base += 20.0
        return min(50.0, base)

    def mana_regen(self) -> int:
        return max(1, int(self.base_stats.wisdom * 0.8))

    def cooldown_reduction_percent(self) -> float:
        return min(50.0, self.base_stats.wisdom * 1.2)

    def is_alive(self) -> bool:
        return self.hp > 0

    def end_turn(self) -> None:
        self.mana = min(self.max_mana, self.mana + self.mana_regen())
        self.stamina = min(self.max_stamina, self.stamina + 5 + self.base_stats.endurance // 2)

        expired_effects = []
        for effect, turns in self.temp_effects.items():
            self.temp_effects[effect] = turns - 1
            if self.temp_effects[effect] <= 0:
                expired_effects.append(effect)
        for effect in expired_effects:
            del self.temp_effects[effect]

        ready_skills = []
        for skill_name, cd in self.cooldowns.items():
            self.cooldowns[skill_name] = cd - 1
            if self.cooldowns[skill_name] <= 0:
                ready_skills.append(skill_name)
        for skill_name in ready_skills:
            del self.cooldowns[skill_name]

    def take_damage(self, amount: int) -> int:
        final_damage = max(1, amount - self.defense())
        self.hp = max(0, self.hp - final_damage)
        return final_damage


# =========================
# Player
# =========================

class Player(Character):
    def __init__(self, name: str, class_name: str):
        if class_name not in CLASS_TEMPLATES:
            raise ValueError(f"Invalid class: {class_name}")

        self.class_name = class_name
        template = CLASS_TEMPLATES[class_name]

        super().__init__(name, template["base_stats"], level=1)

        self.xp = 0
        self.gold = 50
        self.skill_points = 0
        self.skills: List[Skill] = [Skill.from_dict(s.to_dict()) for s in template["skills"]]
        self.inventory: List[Item] = []
        self.equipment: Dict[str, Optional[Item]] = {
            "weapon": None,
            "armor": None,
            "accessory": None,
        }

        self.true_base_stats = Stats.from_dict(template["base_stats"].to_dict())
        self.inventory.extend(self.starting_items())
        self.auto_equip_starters()
        self.refresh_resources(full_restore=True)

    def starting_items(self) -> List[Item]:
        items = [Item(name="Small Potion", item_type="consumable", heal_amount=30, value=10)]

        if self.class_name == "Warrior":
            items.append(Item("Iron Sword", "weapon", value=20, stat_bonus={"strength": 2}, slot="weapon"))
            items.append(Item("Leather Armor", "armor", value=15, stat_bonus={"endurance": 2}, slot="armor"))
        elif self.class_name == "Rogue":
            items.append(Item("Dagger", "weapon", value=20, stat_bonus={"agility": 2, "luck": 1}, slot="weapon"))
            items.append(Item("Light Vest", "armor", value=15, stat_bonus={"agility": 1, "endurance": 1}, slot="armor"))
        elif self.class_name == "Mage":
            items.append(Item("Apprentice Staff", "weapon", value=20, stat_bonus={"intelligence": 2}, slot="weapon"))
            items.append(Item("Cloth Robe", "armor", value=15, stat_bonus={"wisdom": 2}, slot="armor"))
        elif self.class_name == "Cleric":
            items.append(Item("Blessed Mace", "weapon", value=20, stat_bonus={"strength": 1, "wisdom": 1}, slot="weapon"))
            items.append(Item("Initiate Robe", "armor", value=15, stat_bonus={"endurance": 1, "wisdom": 1}, slot="armor"))

        return items

    def auto_equip_starters(self) -> None:
        remaining = []
        for item in self.inventory:
            if item.slot in self.equipment and self.equipment[item.slot] is None:
                self.equipment[item.slot] = item
            else:
                remaining.append(item)
        self.inventory = remaining

    def get_total_stats(self) -> Stats:
        total = Stats.from_dict(self.true_base_stats.to_dict())
        for item in self.equipment.values():
            if item:
                total = total.add(Stats(
                    strength=item.stat_bonus.get("strength", 0),
                    agility=item.stat_bonus.get("agility", 0),
                    endurance=item.stat_bonus.get("endurance", 0),
                    intelligence=item.stat_bonus.get("intelligence", 0),
                    wisdom=item.stat_bonus.get("wisdom", 0),
                    luck=item.stat_bonus.get("luck", 0),
                ))
        return total

    def refresh_resources(self, full_restore: bool = False) -> None:
        old_hp = getattr(self, "hp", 0)
        old_mana = getattr(self, "mana", 0)
        old_stamina = getattr(self, "stamina", 0)

        self.base_stats = self.get_total_stats()
        self.max_hp = self.calculate_max_hp()
        self.max_mana = self.calculate_max_mana()
        self.max_stamina = self.calculate_max_stamina()

        if full_restore:
            self.hp = self.max_hp
            self.mana = self.max_mana
            self.stamina = self.max_stamina
        else:
            self.hp = clamp(old_hp, 0, self.max_hp)
            self.mana = clamp(old_mana, 0, self.max_mana)
            self.stamina = clamp(old_stamina, 0, self.max_stamina)

    def attack_power(self) -> int:
        stats = self.get_total_stats()
        return int(stats.strength * 2.5 + self.level * 2)

    def magic_power(self) -> int:
        stats = self.get_total_stats()
        return int(stats.intelligence * 2.7 + self.level * 2)

    def defense(self) -> int:
        stats = self.get_total_stats()
        return int(stats.endurance * 1.8 + self.level)

    def crit_chance(self) -> float:
        stats = self.get_total_stats()
        return min(40.0, 5.0 + stats.luck * 1.5)

    def dodge_chance(self) -> float:
        stats = self.get_total_stats()
        base = 3.0 + stats.agility * 1.2
        if self.temp_effects.get("shadowstep", 0) > 0:
            base += 20.0
        return min(50.0, base)

    def mana_regen(self) -> int:
        stats = self.get_total_stats()
        return max(1, int(stats.wisdom * 0.8))

    def gain_xp(self, amount: int) -> None:
        self.xp += amount
        print(f"\nYou gained {amount} XP.")
        while self.xp >= self.xp_to_next_level():
            self.level_up()

    def xp_to_next_level(self) -> int:
        return 100 + ((self.level - 1) * 75)

    def level_up(self) -> None:
        required = self.xp_to_next_level()
        self.xp -= required
        self.level += 1
        self.skill_points += 3

        growths = {
            "Warrior": {"strength": 2, "endurance": 2, "agility": 1},
            "Rogue": {"agility": 2, "luck": 1, "strength": 1, "endurance": 1},
            "Mage": {"intelligence": 2, "wisdom": 2},
            "Cleric": {"wisdom": 2, "intelligence": 1, "endurance": 1},
        }

        for stat_name, amount in growths.get(self.class_name, {}).items():
            setattr(self.true_base_stats, stat_name, getattr(self.true_base_stats, stat_name) + amount)

        self.refresh_resources(full_restore=True)
        print(f"\n*** LEVEL UP! You are now level {self.level}. ***")
        print("You gained 3 stat points.")
        self.allocate_stat_points()

    def allocate_stat_points(self) -> None:
        while self.skill_points > 0:
            print(f"\nYou have {self.skill_points} stat points.")
            print("1. Strength")
            print("2. Agility")
            print("3. Endurance")
            print("4. Intelligence")
            print("5. Wisdom")
            print("6. Luck")
            print("0. Done")

            choice = input("> ").strip()
            mapping = {
                "1": "strength",
                "2": "agility",
                "3": "endurance",
                "4": "intelligence",
                "5": "wisdom",
                "6": "luck",
            }

            if choice == "0":
                break
            if choice not in mapping:
                print("Invalid choice.")
                continue

            stat_name = mapping[choice]
            setattr(self.true_base_stats, stat_name, getattr(self.true_base_stats, stat_name) + 1)
            self.skill_points -= 1
            self.refresh_resources(full_restore=True)
            print(f"{stat_name.capitalize()} increased by 1.")

    def basic_attack(self, target: Character) -> None:
        base_damage = self.attack_power()
        crit = roll(self.crit_chance())
        if crit:
            base_damage = int(base_damage * 1.75)

        if roll(target.dodge_chance()):
            print(f"{target.name} dodged your attack!")
            return

        damage = target.take_damage(base_damage)
        print(f"You attack {target.name} for {damage} damage{' (CRIT)' if crit else ''}.")

    def use_skill(self, skill_index: int, target: Character) -> None:
        if skill_index < 0 or skill_index >= len(self.skills):
            print("Invalid skill.")
            return

        skill = self.skills[skill_index]

        if skill.name in self.cooldowns:
            print(f"{skill.name} is on cooldown for {self.cooldowns[skill.name]} more turn(s).")
            return

        if self.mana < skill.mana_cost:
            print("Not enough mana.")
            return

        if self.stamina < skill.stamina_cost:
            print("Not enough stamina.")
            return

        self.mana -= skill.mana_cost
        self.stamina -= skill.stamina_cost

        if skill.cooldown > 0:
            actual_cd = max(1, math.ceil(skill.cooldown * (1 - self.cooldown_reduction_percent() / 100)))
            self.cooldowns[skill.name] = actual_cd

        if skill.skill_type == "physical":
            if roll(target.dodge_chance()):
                print(f"{target.name} dodged your skill!")
                return

            damage = int(self.attack_power() * skill.power)
            crit = roll(self.crit_chance())
            if crit:
                damage = int(damage * 1.5)

            final_damage = target.take_damage(damage)
            print(f"You used {skill.name} on {target.name} for {final_damage} damage{' (CRIT)' if crit else ''}.")

        elif skill.skill_type == "magical":
            if roll(target.dodge_chance() / 2):
                print(f"{target.name} partially evaded the spell!")
                return

            damage = int(self.magic_power() * skill.power)
            crit = roll(self.crit_chance() / 2)
            if crit:
                damage = int(damage * 1.5)

            final_damage = target.take_damage(damage)
            print(f"You cast {skill.name} on {target.name} for {final_damage} damage{' (CRIT)' if crit else ''}.")

        elif skill.skill_type == "utility":
            self.resolve_utility_skill(skill)

    def resolve_utility_skill(self, skill: Skill) -> None:
        if skill.name == "Second Wind":
            restore = 25 + self.level * 3
            self.stamina = min(self.max_stamina, self.stamina + restore)
            print(f"You used {skill.name} and restored {restore} stamina.")
        elif skill.name == "Shadowstep":
            self.temp_effects["shadowstep"] = 2
            print("You used Shadowstep. Your dodge chance is greatly increased for 2 turns.")
        elif skill.name == "Meditate":
            restore = 20 + self.get_total_stats().wisdom * 2
            self.mana = min(self.max_mana, self.mana + restore)
            print(f"You used Meditate and restored {restore} mana.")
        elif skill.name == "Heal":
            total = self.get_total_stats()
            restore = int((total.wisdom + total.intelligence) * 1.6 + self.level * 4)
            self.hp = min(self.max_hp, self.hp + restore)
            print(f"You used Heal and restored {restore} HP.")
        else:
            print(f"{skill.name} had no effect.")

    def add_item(self, item: Item) -> None:
        self.inventory.append(item)
        print(f"You received: {item.name}")

    def equip_item(self, inventory_index: int) -> None:
        if inventory_index < 0 or inventory_index >= len(self.inventory):
            print("Invalid inventory slot.")
            return

        item = self.inventory[inventory_index]
        if item.slot not in self.equipment:
            print("That item cannot be equipped.")
            return

        old_item = self.equipment[item.slot]
        self.equipment[item.slot] = item
        self.inventory.pop(inventory_index)

        if old_item:
            self.inventory.append(old_item)
            print(f"Unequipped {old_item.name}.")

        print(f"Equipped {item.name} to {item.slot}.")
        self.refresh_resources(full_restore=False)

    def use_consumable(self, inventory_index: int) -> None:
        if inventory_index < 0 or inventory_index >= len(self.inventory):
            print("Invalid inventory slot.")
            return

        item = self.inventory[inventory_index]
        if item.item_type != "consumable":
            print("That item is not consumable.")
            return

        if item.heal_amount > 0:
            self.hp = min(self.max_hp, self.hp + item.heal_amount)
            print(f"You restored {item.heal_amount} HP.")
        if item.mana_restore > 0:
            self.mana = min(self.max_mana, self.mana + item.mana_restore)
            print(f"You restored {item.mana_restore} mana.")
        if item.stamina_restore > 0:
            self.stamina = min(self.max_stamina, self.stamina + item.stamina_restore)
            print(f"You restored {item.stamina_restore} stamina.")

        self.inventory.pop(inventory_index)

    def show_character_sheet(self) -> None:
        stats = self.get_total_stats()
        print("\n===== CHARACTER SHEET =====")
        print(f"Name: {self.name}")
        print(f"Class: {self.class_name}")
        print(f"Level: {self.level}")
        print(f"XP: {self.xp}/{self.xp_to_next_level()}")
        print(f"Gold: {self.gold}")
        print(f"HP: {self.hp}/{self.max_hp}")
        print(f"Mana: {self.mana}/{self.max_mana}")
        print(f"Stamina: {self.stamina}/{self.max_stamina}")
        print("\nStats:")
        print(f"  Strength:     {stats.strength}")
        print(f"  Agility:      {stats.agility}")
        print(f"  Endurance:    {stats.endurance}")
        print(f"  Intelligence: {stats.intelligence}")
        print(f"  Wisdom:       {stats.wisdom}")
        print(f"  Luck:         {stats.luck}")
        print("\nDerived:")
        print(f"  Physical Power: {self.attack_power()}")
        print(f"  Magic Power:    {self.magic_power()}")
        print(f"  Defense:        {self.defense()}")
        print(f"  Crit Chance:    {self.crit_chance():.1f}%")
        print(f"  Dodge Chance:   {self.dodge_chance():.1f}%")
        print(f"  Mana Regen:     {self.mana_regen()}/turn")
        print("===========================\n")

    def show_inventory(self) -> None:
        print("\n===== INVENTORY =====")
        if not self.inventory:
            print("Inventory is empty.")
        else:
            for i, item in enumerate(self.inventory):
                details = []
                if item.stat_bonus:
                    details.append(f"Bonuses: {item.stat_bonus}")
                if item.heal_amount:
                    details.append(f"Heal: {item.heal_amount}")
                if item.mana_restore:
                    details.append(f"Mana: {item.mana_restore}")
                if item.stamina_restore:
                    details.append(f"Stamina: {item.stamina_restore}")
                extra = f" | {' | '.join(details)}" if details else ""
                print(f"{i + 1}. {item.name} [{item.item_type}]{extra}")

        print("\nEquipped:")
        for slot, item in self.equipment.items():
            print(f"  {slot.capitalize()}: {item.name if item else 'None'}")
        print("=====================\n")

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "class_name": self.class_name,
            "level": self.level,
            "xp": self.xp,
            "gold": self.gold,
            "skill_points": self.skill_points,
            "true_base_stats": self.true_base_stats.to_dict(),
            "hp": self.hp,
            "mana": self.mana,
            "stamina": self.stamina,
            "skills": [skill.to_dict() for skill in self.skills],
            "inventory": [item.to_dict() for item in self.inventory],
            "equipment": {
                slot: item.to_dict() if item else None
                for slot, item in self.equipment.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Player":
        player = cls(data["name"], data["class_name"])
        player.level = data["level"]
        player.xp = data["xp"]
        player.gold = data["gold"]
        player.skill_points = data["skill_points"]
        player.true_base_stats = Stats.from_dict(data["true_base_stats"])
        player.skills = [Skill.from_dict(s) for s in data["skills"]]
        player.inventory = [Item.from_dict(i) for i in data["inventory"]]
        player.equipment = {
            slot: Item.from_dict(item) if item else None
            for slot, item in data["equipment"].items()
        }
        player.refresh_resources(full_restore=False)
        player.hp = clamp(data["hp"], 0, player.max_hp)
        player.mana = clamp(data["mana"], 0, player.max_mana)
        player.stamina = clamp(data["stamina"], 0, player.max_stamina)
        return player


# =========================
# Enemy
# =========================

class Enemy(Character):
    def __init__(self, name: str, stats: Stats, level: int, xp_reward: int, gold_reward: int, loot_table: List[Item]):
        super().__init__(name, stats, level)
        self.xp_reward = xp_reward
        self.gold_reward = gold_reward
        self.loot_table = loot_table

    def attack(self, target: Character) -> None:
        if roll(target.dodge_chance()):
            print(f"{target.name} dodged the attack from {self.name}!")
            return

        damage = self.physical_attack_power()
        crit = roll(self.crit_chance() / 2)
        if crit:
            damage = int(damage * 1.5)

        final_damage = target.take_damage(damage)
        print(f"{self.name} attacks {target.name} for {final_damage} damage{' (CRIT)' if crit else ''}.")


# =========================
# Loot
# =========================

COMMON_LOOT = [
    Item("Small Potion", "consumable", value=10, heal_amount=30),
    Item("Mana Potion", "consumable", value=12, mana_restore=25),
    Item("Stamina Tonic", "consumable", value=12, stamina_restore=25),
]

UNCOMMON_LOOT = [
    Item("Steel Sword", "weapon", value=40, stat_bonus={"strength": 3}, slot="weapon"),
    Item("Swift Dagger", "weapon", value=40, stat_bonus={"agility": 3, "luck": 1}, slot="weapon"),
    Item("Mage Wand", "weapon", value=40, stat_bonus={"intelligence": 3}, slot="weapon"),
    Item("Sage Charm", "trinket", value=45, stat_bonus={"wisdom": 3}, slot="accessory"),
    Item("Chain Vest", "armor", value=50, stat_bonus={"endurance": 3}, slot="armor"),
]

RARE_LOOT = [
    Item("Lucky Ring", "trinket", value=80, stat_bonus={"luck": 4}, slot="accessory"),
    Item("Knight Blade", "weapon", value=90, stat_bonus={"strength": 5, "endurance": 2}, slot="weapon"),
    Item("Mystic Staff", "weapon", value=90, stat_bonus={"intelligence": 5, "wisdom": 2}, slot="weapon"),
]


# =========================
# Enemy Generation
# =========================

def generate_enemy(player_level: int) -> Enemy:
    enemy_types = [
        ("Goblin", Stats(5, 7, 5, 2, 2, 4)),
        ("Wolf", Stats(6, 8, 5, 1, 2, 4)),
        ("Skeleton", Stats(7, 5, 6, 2, 2, 3)),
        ("Bandit", Stats(7, 7, 6, 3, 3, 5)),
        ("Slime", Stats(5, 3, 8, 1, 1, 2)),
        ("Dark Acolyte", Stats(3, 4, 5, 8, 6, 4)),
    ]

    name, base_stats = random.choice(enemy_types)
    level = max(1, random.randint(max(1, player_level - 1), player_level + 1))

    scaled = Stats(
        strength=base_stats.strength + level,
        agility=base_stats.agility + level,
        endurance=base_stats.endurance + level,
        intelligence=base_stats.intelligence + level,
        wisdom=base_stats.wisdom + level,
        luck=base_stats.luck + level // 2,
    )

    xp_reward = 40 + level * 20
    gold_reward = 10 + level * 8
    loot_table = COMMON_LOOT[:]
    if level >= 3:
        loot_table += UNCOMMON_LOOT[:]
    if level >= 6:
        loot_table += RARE_LOOT[:]

    return Enemy(name, scaled, level, xp_reward, gold_reward, loot_table)


def drop_loot(player: Player, enemy: Enemy) -> Optional[Item]:
    quality_roll = random.randint(1, 100) + int(player.get_total_stats().luck * 1.5)

    if quality_roll >= 105 and enemy.level >= 6:
        return random.choice(RARE_LOOT)
    if quality_roll >= 75 and enemy.level >= 3:
        return random.choice(UNCOMMON_LOOT)
    if quality_roll >= 30:
        return random.choice(COMMON_LOOT)
    return None


def check_special_event(player: Player) -> None:
    chance = 2.0 + player.get_total_stats().luck * 0.8
    if roll(chance):
        bonus_gold = random.randint(15, 40)
        player.gold += bonus_gold
        print(f"\n*** Lucky Event! You found a hidden stash and gained {bonus_gold} gold. ***")


# =========================
# Save / Load
# =========================

SAVE_FILE = "savegame.json"


def save_game(player: Player) -> None:
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(player.to_dict(), f, indent=2)
    print("Game saved.")


def load_game() -> Optional[Player]:
    if not os.path.exists(SAVE_FILE):
        print("No save file found.")
        return None

    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    player = Player.from_dict(data)
    print("Game loaded.")
    return player


# =========================
# Combat
# =========================

def print_battle_status(player: Player, enemy: Enemy) -> None:
    print("\n----------------------------")
    print(f"{player.name} - HP: {player.hp}/{player.max_hp} | Mana: {player.mana}/{player.max_mana} | Stamina: {player.stamina}/{player.max_stamina}")
    print(f"{enemy.name} (Lv {enemy.level}) - HP: {enemy.hp}/{enemy.max_hp}")
    print("----------------------------")


def player_turn(player: Player, enemy: Enemy) -> bool:
    while True:
        print_battle_status(player, enemy)
        print("Choose an action:")
        print("1. Basic Attack")
        print("2. Use Skill")
        print("3. Use Item")
        print("4. View Character")
        print("5. Attempt Escape")

        choice = input("> ").strip()

        if choice == "1":
            player.basic_attack(enemy)
            return True

        elif choice == "2":
            print("\nSkills:")
            for i, skill in enumerate(player.skills):
                cd_text = f" [CD: {player.cooldowns.get(skill.name, 0)}]" if skill.name in player.cooldowns else ""
                print(f"{i + 1}. {skill.name} - {skill.description} (Mana {skill.mana_cost}, Stamina {skill.stamina_cost}, Cooldown {skill.cooldown}){cd_text}")
            try:
                idx = int(input("> ").strip()) - 1
                player.use_skill(idx, enemy)
                return True
            except ValueError:
                print("Invalid choice.")

        elif choice == "3":
            player.show_inventory()
            try:
                idx = int(input("Choose item number to use (0 to cancel): ").strip()) - 1
                if idx == -1:
                    continue
                player.use_consumable(idx)
                return True
            except ValueError:
                print("Invalid choice.")

        elif choice == "4":
            player.show_character_sheet()

        elif choice == "5":
            escape_chance = min(75, 25 + player.get_total_stats().agility * 3 - enemy.base_stats.agility)
            if roll(max(10, escape_chance)):
                print("You escaped successfully!")
                return False
            print("Escape failed!")
            return True

        else:
            print("Invalid choice.")


def enemy_turn(enemy: Enemy, player: Player) -> None:
    if enemy.is_alive():
        enemy.attack(player)


def battle(player: Player, enemy: Enemy) -> bool:
    print(f"\nA wild {enemy.name} (Level {enemy.level}) appears!")

    while player.is_alive() and enemy.is_alive():
        acted = player_turn(player, enemy)

        if not acted:
            return False

        if enemy.is_alive():
            enemy_turn(enemy, player)

        player.end_turn()
        enemy.end_turn()

    if player.is_alive():
        print(f"\nYou defeated the {enemy.name}!")
        player.gain_xp(enemy.xp_reward)
        player.gold += enemy.gold_reward
        print(f"You gained {enemy.gold_reward} gold.")

        loot = drop_loot(player, enemy)
        if loot:
            player.add_item(loot)
        else:
            print("No loot dropped this time.")

        check_special_event(player)
        return True

    print("\nYou were defeated...")
    return False


# =========================
# Town / Menus
# =========================

def rest_at_inn(player: Player) -> None:
    cost = 15
    if player.gold < cost:
        print("Not enough gold to rest.")
        return

    player.gold -= cost
    player.refresh_resources(full_restore=True)
    print("You rest at the inn and fully recover.")


def shop_menu(player: Player) -> None:
    shop_items = [
        Item("Small Potion", "consumable", value=10, heal_amount=30),
        Item("Mana Potion", "consumable", value=12, mana_restore=25),
        Item("Stamina Tonic", "consumable", value=12, stamina_restore=25),
        Item("Bronze Sword", "weapon", value=35, stat_bonus={"strength": 2}, slot="weapon"),
        Item("Leather Coat", "armor", value=35, stat_bonus={"endurance": 2}, slot="armor"),
        Item("Lucky Charm", "trinket", value=50, stat_bonus={"luck": 2}, slot="accessory"),
    ]

    while True:
        print("\n===== SHOP =====")
        print(f"Gold: {player.gold}")
        for i, item in enumerate(shop_items):
            print(f"{i + 1}. {item.name} - {item.value} gold")
        print("0. Leave shop")

        choice = input("> ").strip()
        if choice == "0":
            break

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(shop_items):
                print("Invalid choice.")
                continue

            item = shop_items[idx]
            if player.gold < item.value:
                print("Not enough gold.")
                continue

            player.gold -= item.value
            player.add_item(item)
            print(f"You bought {item.name}.")
        except ValueError:
            print("Invalid choice.")


def inventory_menu(player: Player) -> None:
    while True:
        player.show_inventory()
        print("1. Equip item")
        print("2. Use consumable")
        print("0. Back")

        choice = input("> ").strip()

        if choice == "0":
            break
        elif choice == "1":
            try:
                idx = int(input("Choose inventory item number to equip: ").strip()) - 1
                player.equip_item(idx)
            except ValueError:
                print("Invalid choice.")
        elif choice == "2":
            try:
                idx = int(input("Choose inventory item number to use: ").strip()) - 1
                player.use_consumable(idx)
            except ValueError:
                print("Invalid choice.")
        else:
            print("Invalid choice.")


def town_menu(player: Player) -> None:
    while True:
        print("\n===== TOWN =====")
        print("1. Go Adventuring")
        print("2. View Character")
        print("3. Inventory")
        print("4. Rest at Inn (15 gold)")
        print("5. Shop")
        print("6. Save Game")
        print("0. Quit to Main Menu")

        choice = input("> ").strip()

        if choice == "1":
            enemy = generate_enemy(player.level)
            won_or_escaped = battle(player, enemy)
            if not player.is_alive():
                print("You wake up in town after being rescued.")
                player.hp = max(1, player.max_hp // 2)
                player.mana = player.max_mana // 2
                player.stamina = player.max_stamina // 2
        elif choice == "2":
            player.show_character_sheet()
        elif choice == "3":
            inventory_menu(player)
        elif choice == "4":
            rest_at_inn(player)
        elif choice == "5":
            shop_menu(player)
        elif choice == "6":
            save_game(player)
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


# =========================
# Game Setup
# =========================

def create_character() -> Player:
    print("\nEnter your character name:")
    name = input("> ").strip()
    if not name:
        name = "Hero"

    print("\nChoose your class:")
    class_names = list(CLASS_TEMPLATES.keys())
    for i, class_name in enumerate(class_names, start=1):
        print(f"{i}. {class_name}")

    while True:
        choice = input("> ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(class_names):
                selected_class = class_names[idx]
                player = Player(name, selected_class)
                print(f"\nWelcome, {player.name} the {player.class_name}!")
                return player
        except ValueError:
            pass
        print("Invalid class choice.")


def main_menu() -> None:
    while True:
        print("\n===== TEXT RPG =====")
        print("1. New Game")
        print("2. Load Game")
        print("0. Exit")

        choice = input("> ").strip()

        if choice == "1":
            player = create_character()
            town_menu(player)
        elif choice == "2":
            player = load_game()
            if player:
                town_menu(player)
        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main_menu()
