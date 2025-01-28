from flask import Flask, render_template, request, session
import requests
import json
import random

WORD_FETCH_LIMIT = 10
MIN_WORD_LENGTH = 4
MAX_WORD_LENGTH = 15
CHECK_PROFANITY = True
CHECK_NAMES = True

def contains_embedded_profanity(word):
    with open("censored_words.json", "r") as f:
        censored_words = json.load(f)

    for censored_word in censored_words:
        if censored_word in word.lower():
            print("\033[91m" + f"Profanity detected: {censored_word} \033[0m")
            return True


def contains_name(word):
    with open("names.json", "r") as f:
        names = json.load(f)
        if word in names or word.lower() in names or word.capitalize() in names:
            return True
        
        return False
    

def get_random_word():
    while True:
        try:
            word = requests.get("https://api.urbandictionary.com/v0/random")
        except requests.exceptions.RequestException:
            print("Error fetching word. Retrying...")
            return "404", "404"

        word_text = word.json()["list"][0]["word"]
        definition = word.json()["list"][0]["definition"]

        print(f"Word: {word_text}, Definition: {definition}")

        if not word_text.isalpha():
            print("\033[91m" + f"Word not alphabetic or contains space, skipping word: {word_text} \033[0m\n")
            continue

        if CHECK_PROFANITY:
            if contains_embedded_profanity(word_text) or contains_embedded_profanity(definition):
                print("\033[91m" + f"Profanity detected, skipping word: {word_text} \033[0m\n")
                continue

        if CHECK_NAMES:
            if contains_name(word_text):
                print("\033[91m" + f"Name detected, skipping word: {word_text} \033[0m\n")
                continue

        if word_text.lower() in definition.lower():
            print("\033[91m" + f"Word in definition, skipping word: {word_text} \033[0m\n")
            continue

        if len(word_text) < MIN_WORD_LENGTH or len(word_text) > MAX_WORD_LENGTH:
            print("\033[91m" + f"Word length not in range, skipping word: {word_text} \033[0m\n")
            continue

        break

    print("\033[92m" + f"Word fetched: {word_text} \033[0m")
    definition = definition.replace("[", "").replace("]", "")

    word_text = word_text[0].capitalize() + word_text[1:]
    definition = definition[0].capitalize() + definition[1:]

    return word_text, definition


def generate_word_list():
    word_list = []
    for i in range(WORD_FETCH_LIMIT):
        word, definition = get_random_word()
        if word == "404":
            return False
        word_list.append((word, definition))
        print("\033[94m" + f"Word {i+1}: {word} \033[0m")
    
    try:
        with open("word_list.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    data.extend(word_list)
    with open("word_list.json", "w") as f:
        json.dump(data, f)

    return True


def get_word_list(n):
    try:
        with open("word_list.json", "r") as f:
            data = json.load(f)
            if len(data) < n:
                if not data:
                    return None
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        with open("word_list.json", "w") as f:
            json.dump([], f)
        return None

    return data[-n:]


app = Flask(__name__)
app.secret_key = 'supersecreturbancrosswordkey'

@app.route('/')
def index():
    if 'first_load' not in session:
        session['first_load'] = True

    word_list = get_word_list(10)
    if word_list is None:
        if session['first_load']:
            error_message = None
            session['first_load'] = False
        else:
            error_message = (
                "Not enough words available to generate the list. "
                "Please try generating new words using the button below."
            )
        
        return render_template("index.html", word_list=[], error_message=error_message)

    return render_template("index.html", word_list=word_list, error_message=None)

@app.route('/generate_new_crossword', methods=["POST"])
def generate_new_crossword():
    fetched = generate_word_list()
    if not fetched:
        return {"success": False, "message": "Error fetching words. Please try again later."}
    return {"success": True}

if __name__ == "__main__":
    app.run(debug=True)