import requests
import time
import random
import string
import threading
from colorama import Fore, Style, init
from plyer import notification
from concurrent.futures import ThreadPoolExecutor

init()

# ====== SETTINGS =====
INCLUDE_NUMBERS = True
INCLUDE_UNDERSCORE = True
USERNAME_LENGTH = 4
REQUIRED_CHARACTERS = "4"
START_CHAR = ""
END_CHAR = ""
NUMBER_OF_USERNAMES = 10000
ENABLE_NOTIFICATIONS = True
MAX_THREADS = 5
DELAY_BETWEEN_REQUESTS = 0.5
MAX_SHUFFLE_RETRIES = 10
# ======================

lock = threading.Lock()
cooldown_event = threading.Event()
cooldown_lock = threading.Lock()

def generate_usernames():
    usernames = set()

    characters = string.ascii_lowercase
    if INCLUDE_NUMBERS:
        characters += string.digits
    if INCLUDE_UNDERSCORE:
        characters += "_"

    base_length = USERNAME_LENGTH - len(START_CHAR) - len(END_CHAR) - len(REQUIRED_CHARACTERS)
    if base_length < 0:
        raise ValueError("Username length too short for required constraints.")

    max_attempts = NUMBER_OF_USERNAMES * 20
    attempts = 0

    while len(usernames) < NUMBER_OF_USERNAMES and attempts < max_attempts:
        attempts += 1
        retries = 0

        while retries < MAX_SHUFFLE_RETRIES:
            mid_part = ''.join(random.choice(characters) for _ in range(base_length))
            all_middle = list(mid_part + REQUIRED_CHARACTERS)
            random.shuffle(all_middle)

            if not all_middle or (all_middle[0] != '_' and all_middle[-1] != '_'):
                break
            retries += 1

        if retries >= MAX_SHUFFLE_RETRIES:
            continue

        username = START_CHAR + ''.join(all_middle) + END_CHAR

        if username not in usernames:
            usernames.add(username)

    if len(usernames) < NUMBER_OF_USERNAMES:
        print(Fore.YELLOW + f"⚠️ Only generated {len(usernames)} unique usernames. Try increasing USERNAME_LENGTH or reducing REQUIRED_CHARACTERS." + Style.RESET_ALL)

    return list(usernames)

def send_notification(username):
    notification.notify(
        title="✅ Valid Roblox Username",
        message=f"{username} is available!",
        timeout=5
    )

def trigger_global_cooldown(seconds):
    with cooldown_lock:
        if not cooldown_event.is_set():
            print(Fore.MAGENTA + f"\n⚠️  Rate limit hit. Cooling down for {seconds} seconds...\n" + Style.RESET_ALL)
            cooldown_event.set()
            threading.Thread(target=lambda: cooldown_wait(seconds)).start()

def cooldown_wait(seconds):
    time.sleep(seconds)
    cooldown_event.clear()

def check_username(username):
    url = f"https://auth.roblox.com/v1/usernames/validate?Username={username}&Birthday=2000-01-01"
    retries = 3

    for attempt in range(retries):
        try:
            if cooldown_event.is_set():
                time.sleep(DELAY_BETWEEN_REQUESTS)

            response = requests.get(url, timeout=5)

            if response.status_code == 429:
                trigger_global_cooldown(16)
                time.sleep(DELAY_BETWEEN_REQUESTS)
                continue

            data = response.json()
            code = data.get("code")

            with lock:
                if code == 0:
                    print(Fore.GREEN + f"VALID: {username}" + Style.RESET_ALL)
                    if ENABLE_NOTIFICATIONS:
                        send_notification(username)
                elif code == 1:
                    print(Fore.LIGHTBLACK_EX + f"TAKEN: {username}" + Style.RESET_ALL)
                elif code == 2:
                    print(Fore.RED + f"CENSORED: {username}" + Style.RESET_ALL)
                else:
                    print(Fore.YELLOW + f"Unknown code ({code}): {username}" + Style.RESET_ALL)
            break

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                with lock:
                    print(Fore.YELLOW + f"Failed {username}: {e}" + Style.RESET_ALL)

        time.sleep(DELAY_BETWEEN_REQUESTS)

def main():
    usernames = generate_usernames()
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        executor.map(check_username, usernames)

if __name__ == "__main__":
    main()
