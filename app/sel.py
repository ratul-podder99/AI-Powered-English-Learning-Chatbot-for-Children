"""Social-Emotional Learning (SEL) content for ages 3-6.

Five SEL goals covered:
  1. emotional awareness  - name the feeling ("You feel sad. That's okay.")
  2. self-regulation      - breathing ("smell the flower, blow the candle")
  3. confidence/growth    - "can't YET", praise effort not talent
  4. curiosity            - "I wonder..." prompts, welcome questions
  5. social skills        - hello, thank you, please, kindness

Copy is short and uses very simple words. Variants rotate by turn count so the
bot never repeats itself back-to-back, while staying deterministic for tests.
"""
from __future__ import annotations


def pick(options: list, n: int) -> str:
    return options[n % len(options)]


PRAISE = [
    "Great job, {n}! ⭐",
    "Yes! You did it, {n}! 🎉",
    "Wow, you are so smart, {n}! 🌟",
    "Super! I am proud of you, {n}! 💛",
    "Yay! You tried hard and it worked, {n}! 💪",
]

# growth-mindset praise for effort even when the answer was wrong
TRY_AGAIN = [
    "Good try! Trying is how our brain grows. 🌱",
    "Nice try, {n}! Mistakes help us learn. 💛",
    "Oops, that's okay! Let's try together. 🤝",
    "Almost! You are being brave to try. 🦁",
]

REVEAL = [
    "That's okay! The answer is \"{a}\". Let's say it together: {a}!",
    "No worries! It is \"{a}\". Say it with me: {a}!",
]

CURIOUS = [
    "I wonder what you will learn next! 🔍",
    "Ask me anything. Questions are great! ❓",
    "Curious kids learn the most! 🦉",
]

CHECKIN = [
    "You are working so hard! How do you feel right now? 😀 😐 😢",
    "Let's take a little break. How is your heart feeling? 💗",
]
CHECKIN_REPLIES = ["😀 Happy", "😐 OK", "😢 Sad", "😴 Tired"]

EMOTION_REPLY = {
    "sad": "I'm sorry you feel sad, {n}. It is okay to feel sad. 💙 Feelings are like clouds, they float away.",
    "angry": "You feel angry. That is okay, {n}. Angry is a big feeling. 🔥 We can calm down together.",
    "scared": "You feel scared. You are safe here, {n}. 🛡️ If you are scared, tell a grown-up you trust.",
    "shy": "It is okay to feel shy, {n}. Brave kids try even when they feel nervous. 🦁",
    "tired": "You look sleepy, {n}. 😴 Rest is important for a growing brain.",
    "hungry": "Your tummy is talking! 🍎 Maybe it is snack time, {n}. Ask a grown-up.",
    "happy": "I am happy you are happy, {n}! 😊 Happy feelings are the best.",
    "excited": "Wow, you are excited! 🎉 That energy is awesome, {n}!",
    "proud": "You should be proud, {n}! 🏆 You worked hard.",
}

SUPPORT_OFFER = "What would you like? We can take a deep breath, talk, or play a little game."
SUPPORT_REPLIES = ["🌸 Deep breath", "💬 Talk", "🎲 Play a game"]

BREATHING = (
    "Let's breathe together. Smell the flower 🌸 (breathe in slowly)... "
    "Blow the candle 🕯️ (breathe out slowly)... Let's do it 3 times. "
    "How do you feel now?"
)

LOW_CONFIDENCE = (
    "Hard things help our brain grow, {n}. 🌱 Let's say it together: "
    "\"I can't... YET!\" Now let's try something small. You can do it! 💪"
)

SAFETY = (
    "Thank you for telling me, {n}. 💛 You are important. "
    "Please tell a grown-up you trust right now, like mom, dad, or your teacher. "
    "They can help keep you safe."
)

SOCIAL = {
    "greet": ["Hello, {n}! 👋 I am Ollie the Owl. So happy to see you!", "Hi {n}! 🦉 Yay, you are here!"],
    "thanks": ["You're welcome, {n}! Saying thank you is so kind. 💛"],
    "bye": ["Bye bye, {n}! 👋 Great learning today. See you soon! 🦉"],
}

JOKES = [
    ("What do cats like to eat for breakfast? 🐱", "Mice Krispies! 😹"),
    ("What do you call a sleeping bull? 🐂", "A bulldozer! 😴"),
    ("Why did the banana go to the doctor? 🍌", "It was not peeling well! 🤒"),
]

# original rhymes (written for this project)
SONGS = [
    "🎵 Red, red, red, I see red, a red apple on my bed! Blue, blue, blue, I see blue, the sky is blue for me and you! 🎵",
    "🎵 One, two, one, two, clap your hands, that is what we do! Three, four, three, four, stomp your feet, then clap some more! 🎵",
]

STORIES = [
    "Once upon a time, a little 🐱 cat found a red 🍎 apple. 'Yum!' said the cat. 'Can I share?' The cat shared it with a 🐶 dog. They were friends. The end! 🌈",
]

ENGAGE_OPENERS = [
    "Okay, let's do something fun! 🎈",
    "No problem, {n}! Let's change it up. 🎨",
    "Let's play, not work! 🎲",
]

ENGAGE_BRIDGE = [
    "Ready for a fun word game? 🎮",
    "Want to try one tiny, easy game? 🧩",
]
