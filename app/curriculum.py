"""Static curriculum: three levels, ten items each.

L1 - single words (animals, colours, numbers, food)
L2 - phrases and simple questions ("I see a ...", counting, "What is this?")
L3 - short sentences, opposites, simple conversation, word order
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    level: int
    kind: str          # repeat | choose | fill | count | order | talk
    emoji: str
    teach: str         # short intro shown before the question (may be empty)
    prompt: str        # the question
    answers: tuple     # accepted answers (lowercase)
    hint: str
    options: tuple = ()  # shown as quick-reply buttons when present
    word: str = ""     # the target word/phrase (used for review + context)


L1 = [
    Item("l1_cat", 1, "repeat", "🐱", "This is a cat!", "Can you say: cat?", ("cat",), "It starts with C. C-C-cat!", ("cat",), "cat"),
    Item("l1_dog", 1, "repeat", "🐶", "This is a dog!", "Can you say: dog?", ("dog",), "D-D-dog! Woof woof!", ("dog",), "dog"),
    Item("l1_apple", 1, "choose", "🍎", "Apple is a yummy fruit.", "Which one is an apple? 🍎", ("apple",), "Look for the red fruit. A-A-apple!", ("apple", "ball"), "apple"),
    Item("l1_ball", 1, "choose", "⚽", "A ball is round.", "Which one is a ball? ⚽", ("ball",), "You can kick it! B-B-ball!", ("ball", "cat"), "ball"),
    Item("l1_red", 1, "choose", "🍓", "Strawberries are red!", "What color is a strawberry? 🍓", ("red",), "It is the same color as an apple.", ("red", "blue"), "red"),
    Item("l1_blue", 1, "choose", "🌤️", "The sky is blue!", "What color is the sky? 🌤️", ("blue",), "Look up! The sky is... b-b-blue!", ("blue", "red"), "blue"),
    Item("l1_one", 1, "repeat", "1️⃣", "This is the number one!", "Can you say: one?", ("one", "1"), "One finger up! ☝️ One!", ("one",), "one"),
    Item("l1_two", 1, "repeat", "2️⃣", "This is the number two!", "Can you say: two?", ("two", "2"), "Two fingers up! ✌️ Two!", ("two",), "two"),
    Item("l1_fish", 1, "repeat", "🐟", "A fish swims in water.", "Can you say: fish?", ("fish",), "F-F-fish! Splash!", ("fish",), "fish"),
    Item("l1_sun", 1, "choose", "☀️", "The sun is bright.", "Which one is the sun? ☀️", ("sun",), "It is up in the sky and it is warm.", ("sun", "fish"), "sun"),
]

L2 = [
    Item("l2_see_cat", 2, "fill", "🐱", "", "I see a ___ 🐱", ("cat",), "It says meow! It is a c-c-cat.", ("cat", "dog"), "I see a cat"),
    Item("l2_banana", 2, "choose", "🍌", "", "What color is a banana? 🍌", ("yellow",), "Think of the sun. It is y-y-yellow!", ("yellow", "green"), "yellow"),
    Item("l2_count3", 2, "count", "🍎🍎🍎", "", "How many apples? 🍎🍎🍎", ("three", "3"), "Count with me: one, two, ...", ("three", "two"), "three"),
    Item("l2_count5", 2, "count", "⭐⭐⭐⭐⭐", "", "How many stars? ⭐⭐⭐⭐⭐", ("five", "5"), "Count with your finger! One, two, three, four, ...", ("five", "four"), "five"),
    Item("l2_hello", 2, "repeat", "👋", "We say hello when we meet a friend.", "Can you say: Hello, friend!", ("hello",), "Wave and say: Hello!", ("Hello, friend!",), "hello"),
    Item("l2_big", 2, "choose", "🐘", "", "An elephant is ___ 🐘", ("big",), "Elephants are not tiny. They are b-b-big!", ("big", "small"), "big"),
    Item("l2_what_car", 2, "choose", "🚗", "", "What is this? 🚗", ("car",), "Beep beep! It has wheels.", ("car", "bus"), "car"),
    Item("l2_like", 2, "fill", "🍌", "", "I like ___ 🍌", ("banana", "bananas"), "It is yellow and you peel it.", ("banana", "ball"), "I like banana"),
    Item("l2_cow", 2, "choose", "🐮", "", "What does a cow say? 🐮", ("moo",), "M-M-moo!", ("moo", "meow"), "moo"),
    Item("l2_thanks", 2, "repeat", "🙏", "We say thank you when someone is kind.", "Can you say: Thank you!", ("thank", "thanks"), "Thank... you!", ("Thank you!",), "thank you"),
]

L3 = [
    Item("l3_kick", 3, "choose", "⚽", "", "I ___ a ball. ⚽ (kick / drink)", ("kick",), "What can you do with your foot and a ball?", ("kick", "drink"), "kick"),
    Item("l3_hot", 3, "choose", "☀️", "", "The sun is ___. (hot / cold)", ("hot",), "The sun makes us warm.", ("hot", "cold"), "hot"),
    Item("l3_opp_up", 3, "fill", "⬆️", "", "Up is the opposite of ___ ⬇️", ("down",), "It is the other way. Not up... d-d-down!", ("down", "high"), "down"),
    Item("l3_howare", 3, "talk", "😊", "", "How are you today? Say: I am ___", ("happy", "good", "fine", "great", "ok", "okay", "sad", "tired", "sleepy", "hungry", "angry", "scared", "excited"), "You can say: I am happy, or I am sad.", ("I am happy", "I am sad", "I am tired"), "I am happy"),
    Item("l3_shoes", 3, "choose", "👟", "", "What do we wear on our feet? 👟", ("shoes", "socks", "shoe", "sock"), "They go on your feet. S-S-shoes!", ("shoes", "hat"), "shoes"),
    Item("l3_milk", 3, "choose", "🥛", "", "She ___ milk. 🥛 (drinks / kicks)", ("drinks", "drink"), "What do we do with milk?", ("drinks", "kicks"), "drinks"),
    Item("l3_in_box", 3, "choose", "🐱📦", "", "The cat is ___ the box. 🐱📦 (in / on)", ("in",), "The cat is inside the box.", ("in", "on"), "in"),
    Item("l3_order", 3, "order", "🐶", "Put the words in order!", "is / This / a / dog  → write the sentence", ("this is a dog",), "Start with: This ...", ("This is a dog",), "this is a dog"),
    Item("l3_name", 3, "talk", "🙂", "", "What is your name? Say: My name is ___", ("name",), "You can say: My name is (your name).", (), "my name is"),
    Item("l3_night", 3, "choose", "🌙", "", "When do we see the moon? 🌙 (day / night)", ("night",), "It is dark when we see the moon.", ("day", "night"), "night"),
]

LEVELS = {1: L1, 2: L2, 3: L3}
LEVEL_NAMES = {1: "Words", 2: "Phrases", 3: "Sentences"}
ITEMS_BY_ID = {i.id: i for lv in LEVELS.values() for i in lv}

NUMBER_WORDS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five"}
