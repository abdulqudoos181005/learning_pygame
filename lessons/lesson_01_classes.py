# ============================================
# LESSON 1: Classes & Objects
# ============================================
# Think of a Class as a BLUEPRINT for creating things.
# Think of an Object as the ACTUAL THING made from that blueprint.


# --- STEP 1: Create a simple blueprint (class) ---

class Player:
    """This is a blueprint for a game player."""

    def __init__(self, name, health, speed):
        # These are the PROPERTIES of every player.
        # Every player that gets created will have these.
        self.name = name
        self.health = health
        self.speed = speed

    def introduce(self):
        """The player says hello."""
        print(f"Hi! I'm {self.name}.")
        print(f"  Health: {self.health}")
        print(f"  Speed:  {self.speed}")

    def take_damage(self, amount):
        """Reduce health by some amount."""
        self.health = self.health - amount
        print(f"{self.name} took {amount} damage! Health is now {self.health}.")

    def is_alive(self):
        """Check if the player is still alive."""
        if self.health > 0:
            return True
        else:
            return False

    def heal(self, amount):
        self.health = self.health + amount
        print(f"{self.name} healed for {amount}! Health is now {self.health}.")


# --- STEP 2: Create actual players (objects) from the blueprint ---

hero = Player("Hero", 100, 5)
villain = Player("Dark Knight", 80, 7)

# Notice: SAME blueprint, but DIFFERENT values.
# "hero" and "villain" are two separate objects.


# --- STEP 3: Use them! ---

print("=== Meet Our Characters ===")
print()

hero.introduce()
print()
villain.introduce()
print()

# --- STEP 4: Make things happen ---

print("=== Battle! ===")
print()

hero.take_damage(30)
villain.take_damage(50)

print()

hero.take_damage(60)

print()

# --- STEP 5: Check who's still standing ---

print("=== Healing! ===")
print()

hero.heal(20)

print("=== After Battle ===")
print()

print(f"Is {hero.name} alive? {hero.is_alive()}")       # Health: 10 → alive
print(f"Is {villain.name} alive? {villain.is_alive()}")  # Health: 30 → alive

print()

hero.take_damage(20)  # This will bring hero below 0!
print(f"Is {hero.name} alive? {hero.is_alive()}")        # Health: -10 → not alive


# ============================================
# KEY TAKEAWAYS:
# ============================================
#
# 1. "class Player:" → creates a BLUEPRINT
#
# 2. "__init__" → runs automatically when you create a new object.
#    It sets up the starting values (name, health, speed).
#
# 3. "self" → means "this particular object".
#    When hero calls take_damage(), self = hero.
#    When villain calls take_damage(), self = villain.
#
# 4. You create an object by calling the class like a function:
#    hero = Player("Hero", 100, 5)
#
# 5. You use the dot (.) to access properties and actions:
#    hero.name       → get the name
#    hero.introduce() → call an action
#
# ============================================
# TRY IT YOURSELF:
# ============================================
#
# 1. Create a third character (maybe a "Healer" with 60 health and speed 3)
# 2. Add a new action called "heal" that INCREASES health
# 3. Make the healer heal the hero after the battle
#
# When you're done (or stuck), tell me and we'll move on!
# ============================================
