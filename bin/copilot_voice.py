from pynput.keyboard import Controller, Key
import json
import os
import threading # For non-blocking speech

# Initialize components
engine = pyttsx3.init()
keyboard = Controller()
r = sr.Recognizer()

# Global state for checklist management
current_checklist = None
current_checklist_name = None
current_checklist_index = -1
CHECKLISTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs', 'checklists')

def talk(text):
    """Speaks the given text and prints it to console."""
    print(f"Copilot: {text}")
    # Use a thread for speech to avoid blocking the main loop
    # This is a simple approach; for more complex scenarios, a dedicated speech queue might be better
    def _speak():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=_speak).start()

def load_checklist(checklist_name):
    """Loads a checklist from a JSON file."""
    global current_checklist, current_checklist_index, current_checklist_name
    filepath = os.path.join(CHECKLISTS_DIR, f"{checklist_name}.json")
    if not os.path.exists(filepath):
        talk(f"Error: Checklist '{checklist_name}' not found.")
        return False
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Assuming the checklist is under a key like "pre_flight_checklist"
            # We need to find the correct key, or enforce a standard key name.
            # For now, let's assume the key is the checklist_name with underscores.
            key = checklist_name.replace('-', '_') + "_checklist"
            if key not in data:
                talk(f"Error: Invalid format for checklist '{checklist_name}'. Expected key '{key}'.")
                return False
            current_checklist = data[key]
            current_checklist_index = -1 # Start before the first item
            current_checklist_name = checklist_name
            talk(f"Checklist '{checklist_name}' loaded. Ready to begin.")
            return True
    except json.JSONDecodeError:
        talk(f"Error: Could not parse JSON for checklist '{checklist_name}'.")
        return False
    except Exception as e:
        talk(f"An unexpected error occurred loading checklist: {e}")
        return False

def start_checklist(checklist_name):
    """Initiates a checklist."""
    if load_checklist(checklist_name):
        talk(f"Starting {checklist_name} checklist.")
        next_checklist_item() # Immediately present the first item

def next_checklist_item():
    """Advances to the next item in the current checklist."""
    global current_checklist_index
    if current_checklist is None:
        talk("No checklist is currently active.")
        return

    current_checklist_index += 1
    if current_checklist_index < len(current_checklist):
        item = current_checklist[current_checklist_index]
        talk(f"{item.get('instruction', 'No instruction provided.')}")
        # Here you could add logic to perform keyboard actions based on item.get('action')
        # For now, we just speak the instruction.
    else:
        talk(f"Checklist '{current_checklist_name}' complete.")
        reset_checklist()

def repeat_checklist_item():
    """Repeats the current item in the current checklist."""
    if current_checklist is None or current_checklist_index == -1:
        talk("No checklist is currently active or no item to repeat.")
        return
    if current_checklist_index < len(current_checklist):
        item = current_checklist[current_checklist_index]
        talk(f"Repeating: {item.get('instruction', 'No instruction provided.')}")

def reset_checklist():
    """Resets the current checklist state."""
    global current_checklist, current_checklist_index, current_checklist_name
    current_checklist = None
    current_checklist_index = -1
    current_checklist_name = None
    talk("Checklist cancelled.")

# Define core commands
CORE_COMMANDS = {
    "gear down": lambda: (keyboard.press('g'), talk("Gear down.")),
    "flaps up": lambda: (keyboard.press(Key.f5), talk("Flaps up.")),
    "check fuel": lambda: talk("Fuel pumps are active, tanks balanced."),
    "start preflight checklist": lambda: start_checklist("preflight"),
    "start landing checklist": lambda: start_checklist("landing"), # Assuming landing.json exists
    "next item": next_checklist_item,
    "check": next_checklist_item, # Alias for next item
    "repeat item": repeat_checklist_item,
    "cancel checklist": reset_checklist,
    "what is the current item": repeat_checklist_item, # Alias
}

def listen_and_act():
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source) # Adjust for noise once per listen cycle
        print("Copilot is listening...")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5) # Add timeout for robustness
            command = r.recognize_google(audio).lower()
            print(f"User: {command}")
            
            if command in CORE_COMMANDS:
                CORE_COMMANDS[command]()
            else:
                talk("Say again?")
        except sr.UnknownValueError:
            # print("Could not understand audio") # Optional: for debugging
            pass # Silently ignore if nothing understood
        except sr.RequestError as e:
            talk(f"Could not request results from Google Speech Recognition service; {e}")
        except sr.WaitTimeoutError:
            # print("No speech detected within timeout.") # Optional: for debugging
            pass # Silently ignore if no speech within timeout

if __name__ == "__main__":
    talk("SkyDeck Copilot standing by. Initializing systems.")
    # Ensure the checklists directory exists
    os.makedirs(CHECKLISTS_DIR, exist_ok=True)
    talk("Say 'start preflight checklist' to begin.")
    while True:
        listen_and_act()
