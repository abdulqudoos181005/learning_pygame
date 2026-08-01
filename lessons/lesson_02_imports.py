# ============================================
# LESSON 2: Importing Modules
# ============================================
# A module is just a file (or collection of files) that has
# useful code someone already wrote for you.
#
# Python comes with many modules built-in. Pygame is one you
# install separately. Let's start with built-in ones.


# ============================================
# WAY 1: Import the whole module
# ============================================

import random

# Now you can use anything from "random" by writing: random.something

dice_roll = random.randint(1, 6)
print(f"You rolled a {dice_roll}!")

# random.randint(1, 6) gives you a random whole number from 1 to 6.
# This is SUPER useful in games — random enemy positions, random loot, etc.

print()


# ============================================
# WAY 2: Import only what you need
# ============================================

from math import sqrt

# "sqrt" means square root. Now you can use it directly (no "math." needed).

result = sqrt(25)
print(f"The square root of 25 is {result}")

# Why use this? Less typing. Instead of "math.sqrt(25)", just "sqrt(25)".

print()


# ============================================
# WAY 3: Import multiple things at once
# ============================================

from random import choice, shuffle

# "choice" picks one random item from a list
# "shuffle" mixes up a list randomly

fruits = ["apple", "banana", "cherry", "mango"]
picked = choice(fruits)
print(f"Random fruit: {picked}")

shuffle(fruits)
print(f"Shuffled list: {fruits}")

print()


# ============================================
# WAY 4: Give a module a nickname
# ============================================

import random as r

# Now instead of typing "random", you just type "r"
coin = r.choice(["Heads", "Tails"])
print(f"Coin flip: {coin}")

print()


# ============================================
# REAL EXAMPLE: Using "time" module
# ============================================

import time

print("Starting a 1-second timer...")
time.sleep(1)  # Pauses the program for 1 second
print("ABDUL QUDOOS")
print("Done! 15 second has passed.")

print()


# ============================================
# WHY THIS MATTERS FOR PYGAME:
# ============================================
# When we start Pygame, the very first line will be:
#
#     import pygame
#
# This brings in EVERYTHING pygame offers:
#   - pygame.display  → creating the game window
#   - pygame.draw     → drawing shapes
#   - pygame.event    → keyboard/mouse input
#   - pygame.mixer    → sound and music
#   - pygame.image    → loading pictures
#
# Sometimes we'll also do:
#
#     from pygame.locals import *
#
# This brings in handy shortcuts like key names (K_UP, K_DOWN, etc.)


# ============================================
# QUICK REFERENCE TABLE:
# ============================================
#
# | Style                      | Example                    | When to use it          |
# |----------------------------|----------------------------|-------------------------|
# | import module              | import random              | Want everything         |
# | from module import thing   | from math import sqrt      | Want just one thing     |
# | import module as nickname  | import random as r         | Module name is too long |
#


# ============================================
# TRY IT YOURSELF:
# ============================================
#
# 1. Import the "datetime" module
# 2. Use datetime.datetime.now() to print today's date and time
# 3. Try: from datetime import datetime
#    Then just use: datetime.now()
#
# When you're ready, tell me and we'll move to Lesson 3!
# ============================================



from datetime import datetime as dt
print(dt.now())
