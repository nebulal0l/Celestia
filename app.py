import discord
from discord.ext import commands
import os
import asyncio
import json
import requests
from datetime import datetime
import psutil
import base64
import sys
import random
import traceback
import time
import platform
import pytz
import subprocess


def read_config():
    with open('config.json') as config_file:
        return json.load(config_file)

# Function to check if the config file has changed and update the variables
def check_config():
    global config, last_modified_time, client

    current_modified_time = os.path.getmtime('config.json')

    if current_modified_time != last_modified_time:
        print("Config file has changed, reloading...")
        last_modified_time = current_modified_time
        config = read_config()

        # Update variables from the config.json file
        global TOKEN, TITLE, FOOTER, DEFAULT_STATUS, WEBHOOK_URL, PREFIX, DEFAULT_EMOJI
        TOKEN = config.get("TOKEN")
        TITLE = config.get("TITLE", "Celestia")
        FOOTER = config.get("FOOTER", "Celestia Selfbot")
        WEBHOOK_URL = config.get("WEBHOOK_URL")
        DEFAULT_STATUS = config.get("DEFAULT_STATUS", "Celestia Selfbot | !cmds")
        DEFAULT_EMOJI = config.get("DEFAULT_EMOJI", "💻")
        new_prefix = config.get("PREFIX", "!")

        # If the prefix has changed, update it and reload commands
        if new_prefix != client.command_prefix:
            print(f"Prefix changed to: {new_prefix}")
            client.command_prefix = new_prefix
            client.remove_command("help")  # Remove default help command
            print("Reinitializing commands with new prefix...")

# Initialize variables from config.json
config = read_config()  # Read the config file at the start
TOKEN = config.get("TOKEN")
TITLE = config.get("TITLE", "Celestia")
FOOTER = config.get("FOOTER", "Celestia Selfbot")
WEBHOOK_URL = config.get("WEBHOOK_URL")
DEFAULT_STATUS = config.get("DEFAULT_STATUS", "Celestia Selfbot | !cmds")
DEFAULT_EMOJI = config.get("DEFAULT_EMOJI", "💻")
PREFIX = config.get("PREFIX", "!")

last_modified_time = os.path.getmtime('config.json')  # Store the initial modification time

# Start checking every 1 second in the background
async def config_checker():
    while True:
        check_config()
        await set_presence()
        await asyncio.sleep(0)  # Wait for 1 second before checking again

# Initialize the client with the prefix from the config
client = commands.Bot(command_prefix=PREFIX, self_bot=True)
async def set_presence():
    try:
        # Get values from the config
        title = config.get("TITLE", "Celestia Selfbot")
        description = config.get("DEFAULT_STATUS", "Celestia Selfbot | !cmds")
        emoji = config.get("DEFAULT_EMOJI", "💻")

        if not description:
            print("No status found in config file!")
            return

        # Debug: Check the values of title, description, and emoji
        print(f"Attempting to set presence with Title: {emoji} | Status: {description}")

        # Define the streaming activity with emoji as title and description as status message
        activity = discord.Streaming(
            name=f"{emoji} {description}",  # The status message with emoji as the title
            url="https://www.twitch.tv/your_stream_url"  # Placeholder URL (replace with your URL)
        )

        # Set the bot's presence as streaming
        await client.change_presence(activity=activity)
        print(f"Presence set as streaming: {emoji} | {description}")

    except discord.errors.HTTPException as e:
        print(f"HTTPException encountered while setting presence: {e}")
        print(f"Error Details: {e.response.text}")  # This will print the full error response
    except discord.errors.Forbidden as e:
        print(f"Forbidden: Bot may not have permission to change presence: {e}")
    except Exception as e:
        print(f"Failed to set presence: {e}")
        traceback.print_exc()

# Call this function in on_ready or wherever appropriate
@client.event
async def on_ready():
    """Triggered when the selfbot is ready."""
    try:
        print(f"\nLogged in as {client.user}")
        print(f"--- Selfbot is online ---\n")

        # Start the config checker task after bot is ready
        client.loop.create_task(config_checker())

        print(f"Attempting to set presence...")

        # Change the current working directory to the 'core' folder (if needed)
        os.chdir(os.path.join(os.getcwd(), 'core'))

        # Debugging: Check if we're in the right directory
        print(f"Current directory: {os.getcwd()}")

        # Run the presence.py script
        result = subprocess.run(['python', 'presence.py'], capture_output=True, text=True)

        # Debugging: Check the output of the subprocess
        if result.returncode == 0:
            print("Successfully ran presence.py")
            print(result.stdout)  # Output of the presence.py script
        else:
            print(f"Error running presence.py: {result.stderr}")
            print(f"Exit code: {result.returncode}")

    except Exception as e:
        print(f"Error in on_ready: {e}")
        traceback.print_exc()
        
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    # Auto reply if certain phrases are detected
    if "hello" in message.content.lower():
        await send_styled(message.channel, "Hey there!")
    elif "how are you" in message.content.lower():
        await send_styled(message.channel, "I'm doing great, thanks for asking!")
    elif "whats your selfbot" in message.content.lower():
        await send_styled(message.channel, "My selfbot is Celestia! (socials.lat)")



# Function for sending styled messages
async def send_styled(ctx, message, delete_after=10):
    """Send a styled message with customizable title and footer"""
    styled_message = f"""```ini
[{TITLE}]
{message}
[{FOOTER}]
```"""
    sent_message = await ctx.send(styled_message, delete_after=delete_after)
    return sent_message

def send_log_to_webhook(content, title="Selfbot Log", color=0x7f03fc):
    payload = {
        "embeds": [
            {
                "title": title,
                "description": content,
                "color": color,
                "footer": {
                    "text": config["FOOTER"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    # Send POST request to webhook URL
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print("Failed to send log to webhook")

# When the bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    send_log_to_webhook(f'You have logged in successfully as {client.user}.', "Selfbot Logged In", color=0x7f03fc)

# Log command usage
@client.event
async def on_command(ctx):
    log_message = f"You ran the '{ctx.command}' command in {ctx.guild.name if ctx.guild else 'DM'}"
    send_log_to_webhook(log_message, title="Command Ran")

# Log when the selfbot is pinged
@client.event
async def on_message(message):
    if client.user.mentioned_in(message):
        content = f'{message.author} pinged you in {message.guild.name if message.guild else "DM"}'
        send_log_to_webhook(content, title="Selfbot Pinged", color=0x7f03fc)

    # Process the command after logging
    await client.process_commands(message)

@client.command()
async def search(ctx, keyword: str, limit: int = 100):
    """Search messages for a keyword"""
    messages = []
    async for message in ctx.channel.history(limit=limit):
        if keyword.lower() in message.content.lower():
            messages.append(f"{message.author}: {message.content}")

    if messages:
        await send_styled(ctx, f"Found {len(messages)} messages with the keyword '{keyword}':\n{chr(10).join(messages[:10])}")
    else:
        await send_styled(ctx, f"No messages found with the keyword '{keyword}'.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def countmessages(ctx, user: discord.User):
    """Count messages from a specific user"""
    message_count = 0
    async for message in ctx.channel.history(limit=100):
        if message.author == user:
            message_count += 1
    await send_styled(ctx, f"{user.name} has sent {message_count} messages in this channel.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def randomrole(ctx):
    """Give a random role to the user who invoked the command"""
    roles = ctx.guild.roles
    random_role = random.choice(roles[1:])  # Avoid the @everyone role
    await ctx.author.add_roles(random_role)
    await send_styled(ctx, f"{ctx.author}, you have been assigned the '{random_role.name}' role randomly!")
    await ctx.message.delete()  # Delete ONLY the command message
MORSE_CODE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.',
    'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.',
    'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-',
    'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--', 'Z': '--..', '1': '.----',
    '2': '..---', '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.', '0': '-----', ' ': '/'
}

@client.command()
async def length(ctx, *, text: str):
    """Get the length of a message"""
    await send_styled(ctx, f"The length of the provided text is {len(text)} characters.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def uppercase(ctx, *, text: str):
    """Convert text to uppercase"""
    upper_text = text.upper()
    await send_styled(ctx, f"Uppercased: {upper_text}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def wordcount(ctx, *, text: str):
    """Count the number of words in a message"""
    word_count = len(text.split())
    await send_styled(ctx, f"The message contains {word_count} words.")
    await ctx.message.delete()  # Delete ONLY the command message
afk_status = False
afk_message = "I'm currently AFK, please leave a message."

@client.command()
async def afk(ctx, status: str):
    """Enable or disable AFK status."""
    global afk_status
    if status.lower() == "enable":
        afk_status = True
        await send_styled(ctx, "AFK mode enabled. I'll reply with your custom message when pinged.")
    elif status.lower() == "disable":
        afk_status = False
        await send_styled(ctx, "AFK mode disabled. I'm back online.")
    else:
        await send_styled(ctx, "Invalid status. Use 'enable' or 'disable'.")
@client.command()
async def afkmessage(ctx, *, message: str):
    """Set the AFK message."""
    global afk_message
    afk_message = message
    await send_styled(ctx, f"AFK message set to: {afk_message}")
@client.event
async def on_message(message):
    """Reply with custom AFK message when the user is pinged."""
    if afk_status and message.mentions and client.user in message.mentions:
        await message.channel.send(f"{message.author.mention} {afk_message}")
    await client.process_commands(message)
@client.command()
async def emojify(ctx, *, text: str):
    """Convert a message into emoji characters."""
    emoji_text = " ".join([f":{char.lower()}:" for char in text if char.isalpha()])
    await send_styled(ctx, emoji_text)
@client.command()
async def morse(ctx, *, text: str):
    """Convert text to Morse code"""
    morse_code = ' '.join(MORSE_CODE_DICT.get(char.upper(), '?') for char in text)
    await send_styled(ctx, f"Morse Code: {morse_code}")
    await ctx.message.delete()  # Delete ONLY the command message

@client.command()
async def membercount(ctx):
    """Get the current member count of the server"""
    member_count = len(ctx.guild.members)
    await send_styled(ctx, f"There are currently {member_count} members in this server.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def base64_encode(ctx, *, message: str):
    """Encode a message to Base64"""
    try:
        encoded = base64.b64encode(message.encode()).decode()
        await send_styled(ctx, f"Base64 Encoded Message: `{encoded}`")
    except Exception:
        await send_styled(ctx, "Error encoding the message!")
    await ctx.message.delete()

REGION_MAP = {
    "eu-central": "DE-1",  # Germany
    "us-west": "US-W-1",    # United States West
    "us-east": "US-E-1",    # United States East
    "br": "BR-1",           # Brazil
    "au": "AU-1",           # Australia
    "jp": "JP-1",           # Japan
    "kr": "KR-1",           # South Korea
    "in": "IN-1",           # India
    "singapore": "SG-1",    # Singapore
    "southafrica": "ZA-1",  # South Africa
    "eu-west": "IE-1",      # Ireland
    "us-south": "US-S-1",    # United States South (for specific servers like Dallas)
    # Add more regions as needed...
}

@client.command()
async def botinfo(ctx):
    """Display bot information including location (guild region or timezone), connected user, ping, and more."""

    # Get bot's connected user (the bot itself)
    bot_user = ctx.bot.user
    bot_username = bot_user.name
    bot_user_id = bot_user.id

    # Get bot's ping
    ping = round(ctx.bot.latency * 1000)  # Latency is in seconds, so we multiply by 1000 to get milliseconds

    # Get memory and system information (optional, feel free to remove or modify)
    memory_info = psutil.virtual_memory()
    memory_usage = f"{memory_info.percent}%"
    cpu_usage = f"{psutil.cpu_percent()}%"

    # Uptime calculation (time the bot has been running)
    now = datetime.now()
    created_at_naive = bot_user.created_at.replace(tzinfo=None)  # Make it naive for calculation
    uptime = str(now - created_at_naive).split('.')[0]  # Getting the uptime as a string

    # Timezone detection from created_at (using pytz)
    timezone = pytz.timezone('UTC')  # Default timezone if detection fails
    bot_time = created_at_naive.replace(tzinfo=pytz.utc).astimezone(timezone)
    time_zone_str = bot_time.strftime('%Z')  # Get timezone abbreviation like 'UTC', 'PST', etc.
    
    # Optionally, use region codes or other information for location
    location_code = "Unknown"  # You can replace with a custom logic if needed

    # Prepare the information to send
    bot_info = (
        f"Bot Information\n"
        f"Connected User: {bot_username} (ID: {bot_user_id})\n"
        f"Connected Server: US-S-1\n"
        f"Ping: {ping} ms\n"
        f"Memory Usage: {memory_usage}\n"
        f"CPU Usage: {cpu_usage}\n"
        f"Uptime: {uptime}\n"
        f"Timezone: {time_zone_str}\n"
    )

    # Send the bot information as a code block (since you mentioned using codeblocks)
    await send_styled(ctx, bot_info)

    # Optionally delete the command message
    await ctx.message.delete()

import base64

@client.command()
async def halftoken(ctx, user_id: int):
    """Encode a user ID to Base64"""
    try:
        # Convert the user ID to a string, then encode it to bytes
        user_id_str = str(user_id)
        encoded = base64.b64encode(user_id_str.encode()).decode()
        await send_styled(ctx, f"Users Half Token. {encoded}")
    except Exception:
        await send_styled(ctx, "Error getting half of the token.")
    await ctx.message.delete()


@client.command()
async def base64_decode(ctx, *, encoded_message: str):
    """Decode a Base64 message"""

    try:
        decoded = base64.b64decode(encoded_message).decode()
        await send_styled(ctx, f"Base64 Decoded Message: `{decoded}`")
    except Exception:
        await send_styled(ctx, "Invalid Base64 string!")
    await ctx.message.delete()

@client.command()
async def cipher_encode(ctx, shift: int, *, text: str):
    """Encode a message using Caesar cipher (shift)"""
    encoded_message = ''.join(
        [chr((ord(char) + shift - 65) % 26 + 65) if char.isupper() else 
         chr((ord(char) + shift - 97) % 26 + 97) if char.islower() else char
         for char in text]
    )
    await send_styled(ctx, f"Encoded Message: `{encoded_message}`")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def cipher_decode(ctx, shift: int, *, text: str):
    """Decode a message using Caesar cipher (shift)"""
    decoded_message = ''.join(
        [chr((ord(char) - shift - 65) % 26 + 65) if char.isupper() else 
         chr((ord(char) - shift - 97) % 26 + 97) if char.islower() else char
         for char in text]
    )
    await send_styled(ctx, f"Decoded Message: `{decoded_message}`")
    await ctx.message.delete()  # Delete ONLY the command message@client.command()
    async def base64_encode(ctx, *, message: str):
        """Encode a message to Base64"""
        try:
            encoded = base64.b64encode(message.encode()).decode()
            await send_styled(ctx, f"Base64 Encoded Message: `{encoded}`")
        except Exception:
            await send_styled(ctx, "Error encoding the message!")
        await ctx.message.delete()

import random

@client.command()
async def pet(ctx, user: discord.User):
    """Give a virtual pet to a user"""
    pets = [
        "You gave {user.mention} a soft pat on the head. 🐾", 
        "You petted {user.mention} gently. 🐱", 
        "Aww, {user.mention} looks happy now! 🐶", 
        "You gave {user.mention} a belly rub! 🐕"
    ]
    pet_message = random.choice(pets).format(user=user)
    await send_styled(ctx, pet_message)
    await ctx.message.delete()


@client.command()
async def countdown(ctx, seconds: int):
    """Create a countdown in seconds"""
    if seconds <= 0:
        await send_styled(ctx, "Please provide a positive number of seconds.")
        return

    await ctx.message.delete()
    for i in range(seconds, 0, -1):
        await send_styled(ctx, f"Countdown: {i} seconds remaining...")
        await asyncio.sleep(1)

    await send_styled(ctx, "⏰ Time's up!")
    await ctx.message.delete()  # Delete ONLY the command message

@client.command()
async def scrape(ctx):
    """Scrape the last 10 messages in the channel and send them with style."""
    messages = []
    async for msg in ctx.channel.history(limit=10):
        messages.append(msg.content)
    
    if messages:
        # Join the messages into a single string
        scraped_content = f"Scraped messages:\n{chr(10).join(messages)}"
        
        # Split the content into chunks of 2000 characters or less
        for i in range(0, len(scraped_content), 2000):
            chunk = scraped_content[i:i+2000]
            await send_styled(ctx, chunk)
    else:
        await send_styled(ctx, "No messages found to scrape.")
    
    await ctx.message.delete()  # Delete ONLY the command message

@client.command()
async def deletebyid(ctx, message_id: int):
    """Delete a message by its ID."""
    try:
        message = await ctx.channel.fetch_message(message_id)  # Fetch the message by ID
        await message.delete()  # Delete the message
        await send_styled(ctx, f"Message with ID {message_id} has been deleted.")
    except discord.NotFound:
        await send_styled(ctx, f"Message with ID {message_id} not found.")
    except discord.Forbidden:
        await send_styled(ctx, "I don't have permission to delete messages in this channel.")
    except discord.HTTPException:
        await send_styled(ctx, "An error occurred while trying to delete the message.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def deletebyuser(ctx, user_id: int):
    """Delete all messages from a user in the current channel."""
    try:
        async for message in ctx.channel.history(limit=100):  # You can change the limit if needed
            if message.author.id == user_id:
                await message.delete()
        await send_styled(ctx, f"Deleted all messages from user with ID {user_id}.")
    except discord.Forbidden:
        await send_styled(ctx, "I don't have permission to delete messages in this channel.")
    except discord.HTTPException:
        await send_styled(ctx, "An error occurred while trying to delete messages.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def deletebyword(ctx, word: str):
    """Delete all messages that contain the given word/phrase."""
    try:
        async for message in ctx.channel.history(limit=100):  # Adjust the limit as necessary
            if word.lower() in message.content.lower():  # Case insensitive search
                await message.delete()
        await send_styled(ctx, f"Deleted all messages containing the word '{word}'.")
    except discord.Forbidden:
        await send_styled(ctx, "I don't have permission to delete messages in this channel.")
    except discord.HTTPException:
        await send_styled(ctx, "An error occurred while trying to delete messages.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def percentage(ctx, part: float, whole: float):
    """Calculate the percentage of a part from the whole"""
    if whole == 0:
        await send_styled(ctx, "The whole cannot be zero.")
    else:
        percent = (part / whole) * 100
        await send_styled(ctx, f"{part} is {percent:.2f}% of {whole}.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def ascii(ctx, *, text: str):
    """Convert text into ASCII art (basic block style)"""
    art = '\n'.join(f"{' '.join([char.upper() for char in line])}" for line in text.split())
    await send_styled(ctx, f"ASCII Art:\n```\n{art}\n```")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def randomnum(ctx, min_num: int, max_num: int):
    """Generate a random number between two integers"""
    if min_num > max_num:
        await send_styled(ctx, "Make sure the minimum is less than the maximum!")
    else:
        rand_num = random.randint(min_num, max_num)
        await send_styled(ctx, f"Random Number: {rand_num}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def countletters(ctx, *, text: str):
    """Count vowels and consonants in the text"""
    vowels = "aeiou"
    consonants = "bcdfghjklmnpqrstvwxyz"
    vowel_count = sum(1 for char in text.lower() if char in vowels)
    consonant_count = sum(1 for char in text.lower() if char in consonants)
    await send_styled(ctx, f"Vowels: {vowel_count}, Consonants: {consonant_count}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def rps(ctx, choice: str):
    """Play Rock, Paper, Scissors"""
    options = ["rock", "paper", "scissors"]
    bot_choice = random.choice(options)

    if choice not in options:
        await send_styled(ctx, "Invalid choice! Choose rock, paper, or scissors.")
        return

    if choice == bot_choice:
        result = "It's a tie!"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "scissors" and bot_choice == "paper") or \
         (choice == "paper" and bot_choice == "rock"):
        result = "You win!"
    else:
        result = "You lose!"
    
    await send_styled(ctx, f"Your choice: {choice}\nBot's choice: {bot_choice}\nResult: {result}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def encrypt(ctx, shift: int, *, text: str):
    """Encrypt text using a Caesar cipher"""
    encrypted = ''.join(
        chr(((ord(char) - 65 + shift) % 26) + 65) if char.isupper() else
        chr(((ord(char) - 97 + shift) % 26) + 97) if char.islower() else char
        for char in text
    )
    await send_styled(ctx, f"Encrypted Text: {encrypted}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def decrypt(ctx, shift: int, *, text: str):
    """Decrypt text using a Caesar cipher"""
    decrypted = ''.join(
        chr(((ord(char) - 65 - shift) % 26) + 65) if char.isupper() else
        chr(((ord(char) - 97 - shift) % 26) + 97) if char.islower() else char
        for char in text
    )
    await send_styled(ctx, f"Decrypted Text: {decrypted}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def isprime(ctx, number: int):
    """Check if a number is prime"""
    if number <= 1:
        await send_styled(ctx, f"{number} is not a prime number.")
        return

    for i in range(2, int(number**0.5) + 1):
        if number % i == 0:
            await send_styled(ctx, f"{number} is not a prime number.")
            return

    await send_styled(ctx, f"{number} is a prime number.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def palindrome(ctx, *, text: str):
    """Check if a text is a palindrome"""
    clean_text = ''.join(char.lower() for char in text if char.isalnum())
    is_palindrome = clean_text == clean_text[::-1]
    await send_styled(ctx, f"'{text}' is {'a palindrome' if is_palindrome else 'not a palindrome'}.")
    await ctx.message.delete()  # Delete ONLY the command message

@client.command()
async def pinbyid(ctx, message_id: int):
    """Pin a message by its ID."""
    try:
        message = await ctx.channel.fetch_message(message_id)  # Fetch the message
        await message.pin()  # Pin the message
        await send_styled(ctx, f"Message with ID {message_id} has been pinned.")
    except discord.NotFound:
        await send_styled(ctx, f"Message with ID {message_id} not found.")
    except discord.Forbidden:
        await send_styled(ctx, "I don't have permission to pin messages in this channel.")
    except discord.HTTPException:
        await send_styled(ctx, "An error occurred while trying to pin the message.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def randomcolor(ctx):
    """Generate a random color"""
    hex_color = "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    await send_styled(ctx, f"Random Color: {hex_color}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def numfact(ctx, number: int):
    """Get a random fact about a number"""
    response = requests.get(f'http://numbersapi.com/{number}?json')
    data = response.json()
    
    fact = data.get("text", f"No fact found for {number}.")
    await send_styled(ctx, f"**Number Fact:**\n{fact}")
    await ctx.message.delete()  # Delete ONLY the command message

@client.command()
async def geoip(ctx, ip: str):
    """Get geolocation information for an IP address"""
    response = requests.get(f'https://ipapi.co/{ip}/json/')
    data = response.json()
    await ctx.message.delete()  # Delete ONLY the command message
    if 'error' not in data:
        location = data.get('city', 'Unknown city')
        country = data.get('country_name', 'Unknown country')
        timezone = data.get('timezone', 'Unknown timezone')
        
        await send_styled(ctx, f"IP: {ip}\nLocation: {location}, {country}\nTimezone: {timezone}")
    else:
        await send_styled(ctx, f"Could not find information for IP {ip}. Please check the IP address and try again.")
    await ctx.message.delete()  # Delete ONLY the command message

@client.command()
async def time(ctx, timezone: str):
    """Get the current time in a specified timezone"""
    response = requests.get(f'http://worldtimeapi.org/api/timezone/{timezone}')
    data = response.json()
    await ctx.message.delete()  # Delete ONLY the command message
    if 'datetime' in data:
        current_time = data['datetime']
        await send_styled(ctx, f"Current time in {timezone}: {current_time}")
    else:
        await send_styled(ctx, f"Invalid timezone: {timezone}. Please check the name and try again.")
    await ctx.message.delete()  # Delete ONLY the command message
from datetime import datetime
@client.command()
async def whattimeisit(ctx):
    """Displays the current time."""
    current_time = datetime.now().strftime("%H:%M:%S")
    await send_styled(ctx, f"The current time is: {current_time}")
@client.command()
async def dog(ctx):
    """Get a random dog image"""
    response = requests.get('https://dog.ceo/api/breeds/image/random')
    data = response.json()
    
    await send_styled(ctx, f"Here's a dog for you!\n{data['message']}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def cmdamount(ctx):
    """Show the total number of commands"""
    total_commands = len(client.commands)  # Get the number of commands from the bot
    await send_styled(ctx, f"Total available commands: {total_commands}")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def sqrt(ctx, number: float):
    if number < 0:
        await send_styled(ctx, "Cannot calculate the square root of a negative number.")
        return
    result = math.sqrt(number)
    await send_styled(ctx, f"The square root of {number} is {result}.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def factmath(ctx, number: int):
    if number < 0:
        await send_styled(ctx, "Factorial is undefined for negative numbers.")
        return
    result = math.factorial(number)
    await send_styled(ctx, f"The factorial of {number} is {result}.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def power(ctx, base: float, exponent: float):
    result = base ** exponent
    await send_styled(ctx, f"{base} raised to the power of {exponent} is {result}.")
    await ctx.message.delete()  # Delete ONLY the command message
import time
start_time = time.time()
@client.command()
async def uptime(ctx):
    uptime_seconds = int(time.time() - start_time)
    minutes, seconds = divmod(uptime_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    await send_styled(ctx, f"Bot has been online for {hours} hours, {minutes} minutes, and {seconds} seconds.")
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def shutdown(ctx):
    await send_styled(ctx, "Shutting down the bot...")
    await client.close()
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def botstatus(ctx):
    await send_styled(ctx, "The bot is currently online and functioning normally.")    
    await ctx.message.delete()  # Delete ONLY the command message
@client.command()
async def advice(ctx):
    response = requests.get("https://api.adviceslip.com/advice")
    advice_data = response.json()
    await send_styled(ctx, f"Here's a piece of advice: {advice_data['slip']['advice']}")

word_list = ["apple", "table", "grape", "stone", "flash"]

@client.command()
async def wordle(ctx):
    target_word = random.choice(word_list)
    await send_styled(ctx, "Welcome to Wordle! Try to guess the 5-letter word.")
    
    def check(msg):
        return msg.author == ctx.author and len(msg.content) == 5

    attempts = 0
    while attempts < 6:
        try:
            guess = await client.wait_for('message', timeout=30.0, check=check)
            guess_word = guess.content.lower()
            if guess_word == target_word:
                await send_styled(ctx, f"Correct! The word was {target_word}.")
                return
            else:
                await send_styled(ctx, f"Incorrect! You have {5 - attempts} attempts left.")
                attempts += 1
        except asyncio.TimeoutError:
            await send_styled(ctx, "You took too long to respond!")
            return

    await send_styled(ctx, f"Sorry, you didn't guess the word. The correct word was {target_word}.")
    await ctx.message.delete()  # Delete ONLY the command message


@client.command()
async def restart(ctx):
    await send_styled(ctx, "Restarting bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)
    await ctx.message.delete()  # Delete ONLY the command message

import random

@client.command()
async def compliment(ctx, user: discord.User):
    """Give a random compliment to a user"""
    compliments = [
        "You have an amazing smile!", "You're a true superstar!", 
        "Your positivity is contagious!", "You're a genius!", "You light up the room!"
    ]
    compliment = random.choice(compliments)
    await send_styled(ctx, f"🌟 **Compliment for {user.mention}**: {compliment}")
    await ctx.message.delete()


@client.command()
async def cmds(ctx, page: int = 1):
    """Paginated command list"""
    commands_pages = [
"""
Page 1 - Basic Commands:
- !hello: Say hello
- !info: Get bot info
- !ping: Check bot latency
- !cmdamount: Check how many commands Celestia has.
- !serverinfo: Get server info
- !userinfo @user: Get user info
- !avatar @user: Get user's avatar
- !roll: Roll a dice (1-6)
- !flip: Flip a coin (Heads or Tails)
- !shout <message>: Send a message in uppercase
- !repeat <message>: Repeat the message
- !purge <amount>: Delete messages
""",
"""
Page 2 - Intermediate Commands:
- !randomnum <min> <max>: Generate a random number
- !percentage <part> <whole>: Calculate percentage
- !ascii <text>: Generate ASCII art
- !countletters <text>: Count vowels and consonants
- !rps <choice>: Play Rock, Paper, Scissors
- !isprime <number>: Check if a number is prime
- !palindrome <text>: Check if text is a palindrome
- !fortune: Get a random fortune message
- !coinflip: Flip a coin (Heads or Tails)
- !roll_dice <sides>: Roll a custom-sided die
""",
"""
Page 3 - External API Commands:
- !joke: Get a random joke
- !catfact: Get a random cat fact
- !dog: Get a random dog image
- !chucknorris: Get a random Chuck Norris joke
- !quote: Get a random motivational quote
- !numfact <number>: Get a fact about a number
- !meme: Get a random meme
- !randomcolor: Generate a random color
- !geoip <ip>: Get geolocation info for an IP address
- !time <timezone>: Get the current time in a specified timezone
""",
"""
Page 4 - Encoding & Decoding Commands:
- !base64_encode <text>: Encode text in Base64
- !base64_decode <encoded_text>: Decode a Base64 encoded text
- !cipher_encode <shift> <text>: Encrypt text using Caesar cipher
- !cipher_decode <shift> <text>: Decrypt text using Caesar cipher
- !reverse <text>: Reverse a given text string
- !uppercase <text>: Convert text to uppercase
- !lowercase <text>: Convert text to lowercase
- !leetspeak <text>: Converts text to leet speak.
""",
"""
Page 5 - Math & Utility Commands:
- !sqrt <number>: Calculate the square root of a number
- !fact <nusmber>: Get the factorial of a number
- !power <base> <exponent>: Raise a number to a power
- !uptime: Display how long the bot has been online
- !clearcache: Clear bot’s temporary data/cache
- !restart: Restart the bot
- !shutdown: Shut down the bot
- !status <status_message>: Set a custom status message
- !roles <user>:  Displays the roles of a user.
- !emojiinfo <emoji>: Displays information about an emoji.
- !halftoken <user_id>: Gets a halftoken of a user.
""",
"""
Page 6 - Fun & Misc Commands:
- !advice: Get random advice
- !wordle: Get a random wordle challenge
- !lenny: Send a random Lenny face
- !pet @user: Give a virtual pet to a user
- !compliment @user: Give a random compliment to a user
"""
    ]

    # Ensure valid page range
    if page < 1 or page > len(commands_pages):
        await send_styled(ctx, f"Invalid page number! Choose a page between 1 and {len(commands_pages)}.")
        return

    # Send selected page
    await send_styled(ctx, commands_pages[page - 1])
    await ctx.message.delete()  # Delete ONLY the command message


# Command 1: Hello Command
@client.command()
async def emojiinfo(ctx, emoji: discord.PartialEmoji):
    """Displays information about an emoji."""
    if isinstance(emoji, discord.Emoji):  # Only handle custom emoji
        emoji_info = (
            f"**Emoji Info for {emoji.name}:**\n"
            f"**ID:** {emoji.id}\n"
            f"**Created At:** {emoji.created_at.strftime('%b %d, %Y')}\n"
            f"**URL:** https://cdn.discordapp.com/emojis/{emoji.id}.png\n"
            f"**Image URL:** {emoji.url}"
        )
        await send_styled(ctx, emoji_info)
    else:
        await send_styled(ctx, f"Please provide a valid custom emoji.")
    await ctx.message.delete()



@client.command()
async def fact(ctx):
    """Send a random fact."""
    response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en")
    if response.status_code == 200:
        fact = response.json().get("text")
        await send_styled(ctx, f"Here's a fact: {fact}")
    else:
        await send_styled(ctx, "Failed to fetch fact!")
# Command to update avatar


@client.command()
async def avatarset(ctx, url: str = None):
    """Set the bot's avatar"""
    try:
        # Default avatar URL if no URL is provided
        if url is None:
            url = "https://cdn.discordapp.com/attachments/1307114192796651552/1307117804398448763/CelestiaNoText_1.png?ex=673923d1&is=6737d251&hm=6c2227c6c0ca81e3a71287f30ee1db3a98a6bb1c3b1493a9116495c7de43c370&"

        # Ensure the URL is a valid image URL
        if not url.startswith("http"):
            raise ValueError("Provided URL is not valid.")

        # Attempt to fetch the image from the URL
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError("Unable to fetch image from URL. Status code: " + str(response.status_code))

        # Update the bot's avatar
        await client.user.edit(avatar=response.content)
        await send_styled(ctx, f"Avatar updated successfully!")
    except Exception as e:
        # Send the error message with styling
        await send_styled(ctx, f"Error updating avatar: {e}")
        print(f"Error updating avatar: {e}")  # Optional: print the error to the console




# Command 2: Info Command
@client.command()
async def info(ctx):
    """Get bot info with some style"""
    message = f"Selfbot Info:\nName: {client.user.name}\nID: {client.user.id}"
    await send_styled(ctx, message)
    await ctx.message.delete()  # Delete ONLY the command message

# Command 3: Ping Command
@client.command()
async def ping(ctx):
    """Check bot latency"""
    latency = round(client.latency * 1000)
    await send_styled(ctx, f"Pong! Latency is {latency}ms")
    await ctx.message.delete()  # Delete ONLY the command message

# Command 4: Server Info Command (No member scraping)
@client.command()
async def serverinfo(ctx):
    """Get information about the server"""
    server = ctx.guild
    message = f"Server Info:\nName: {server.name}\nID: {server.id}\nRegion: {server.region}"
    await send_styled(ctx, message)
    await ctx.message.delete()  # Delete ONLY the command message

# Command 5: User Info Command
@client.command()
async def userinfo(ctx, user: discord.User):
    """Get user info (without scraping member list)"""
    message = f"User Info:\nName: {user.name}\nID: {user.id}\nDiscriminator: {user.discriminator}"
    await send_styled(ctx, message)
    await ctx.message.delete()  # Delete ONLY the command message

# Command 6: Purge Command (Delete Messages)
@client.command()
async def purge(ctx, amount: int):
    """Purge a certain number of messages"""
    await ctx.channel.purge(limit=amount+1)  # +1 to delete the command message too
    await send_styled(ctx, f"Purged {amount} messages.")
    await ctx.message.delete()  # Delete ONLY the command message



# Command 8: Kick Command (Kick a user)
@client.command()
async def kick(ctx, user: discord.User):
    """Kick a user from the server"""
    await ctx.guild.kick(user)
    await send_styled(ctx, f"{user.name} has been kicked from the server.")
    await ctx.message.delete()  # Delete ONLY the command message

# Command 9: Ban Command (Ban a user)
@client.command()
async def ban(ctx, user: discord.User):
    """Ban a user from the server"""
    await ctx.guild.ban(user)
    await send_styled(ctx, f"{user.name} has been banned from the server.")
    await ctx.message.delete()  # Delete ONLY the command message

# Command 10: Unban Command (Unban a user)
@client.command()
async def unban(ctx, user: discord.User):
    """Unban a user from the server"""
    await ctx.guild.unban(user)
    await send_styled(ctx, f"{user.name} has been unbanned from the server.")
    await ctx.message.delete()  # Delete ONLY the command message

# Command 11: Change Status Command
@client.command()
async def switchstatus(ctx, status: str):
    """Switch the bot's status to either 'online', 'idle', 'dnd', or 'invisible'."""
    status = status.lower()

    if status == "online":
        await client.user.set_status(discord.Status.online)
        await send_styled(ctx, "Status set to Online.")
    elif status == "idle":
        await client.user.set_status(discord.Status.idle)
        await send_styled(ctx, "Status set to Idle.")
    elif status == "dnd":
        await client.user.set_status(discord.Status.dnd)
        await send_styled(ctx, "Status set to Do Not Disturb.")
    elif status == "invisible":
        await client.user.set_status(discord.Status.invisible)
        await send_styled(ctx, "Status set to*Invisible.")
    else:
        await send_styled(ctx, "Invalid status. Use online, idle, dnd, or invisible.")
    await ctx.message.delete()

# Command 12: Send an Embed
@client.command()
async def embed(ctx, *, message: str):
    """Send a styled embed"""
    embed = discord.Embed(title="Celestia Selfbot", description=message, color=discord.Color.blue())
    embed.set_footer(text="Celestia Selfbot")
    await ctx.send(embed=embed)
    await ctx.message.delete()  # Delete ONLY the command message

# Command 13: Shout Command (Send a message in uppercase)
@client.command()
async def shout(ctx, *, message: str):
    """Send a message in uppercase"""
    await send_styled(ctx, message.upper())
    await ctx.message.delete()  # Delete ONLY the command message

# Command 14: Repeat Command (Repeat the message)
@client.command()
async def repeat(ctx, *, message: str):
    """Repeat the message"""
    await send_styled(ctx, message)
    await ctx.message.delete()  # Delete ONLY the command message

# Command 15: Roll a Dice Command
@client.command()
async def roll(ctx):
    """Roll a dice (1-6)"""
    roll = random.randint(1, 6)
    await send_styled(ctx, f"You rolled a {roll}!")
    await ctx.message.delete()  # Delete ONLY the command message

# Command 16: Flip a Coin Command
@client.command()
async def flip(ctx):
    """Flip a coin (Heads or Tails)"""
    flip = random.choice(["Heads", "Tails"])
    await send_styled(ctx, f"The coin landed on {flip}!")
    await ctx.message.delete()  # Delete ONLY the command message

# Command 17: Server Emoji Command
@client.command()
async def emojis(ctx):
    """List all emojis in the server"""
    emojis = ", ".join([str(emoji) for emoji in ctx.guild.emojis])
    await send_styled(ctx, f"Emojis in this server:\n{emojis}")
    await ctx.message.delete()  # Delete ONLY the command message

@client.command()
async def dm(ctx, user: discord.User, *, message: str):
    """Send a direct message to a user"""
    try:
        await user.send(message)
        await send_styled(ctx, f"Message sent to {user.name}!")
    except Exception as e:
        await send_styled(ctx, f"Failed to send message: {e}")
    await ctx.message.delete()
    
@client.command()
async def poll(ctx, *, question: str):
    """Create a simple poll"""
    poll_message = await ctx.send(f"**Poll:** {question}")
    await poll_message.add_reaction("👍")  # Thumbs up
    await poll_message.add_reaction("👎")  # Thumbs down
    await ctx.message.delete()

@client.command()
async def math(ctx, *, expression: str):
    """Calculate a mathematical expression"""
    try:
        result = eval(expression)
        await send_styled(ctx, f"Result: {result}")
    except Exception as e:
        await send_styled(ctx, f"Error in calculation: {e}")
    await ctx.message.delete()

@client.command()
async def invite(ctx):
    """Generate an invite link for the server."""
    try:
        invite = await ctx.channel.create_invite(max_age=600, unique=True, validate=True)  # Added 'validate=True'
        await send_styled(ctx, f"**Server Invite**\nClick the link below to join the server:\n{invite.url}")
    except Exception as e:
        await send_styled(ctx, f"An error occurred while generating the invite: {e}")


@client.command()
async def avatar(ctx, member: discord.Member = None):
    """Display the avatar of a user or the bot."""
    member = member or ctx.author  # Default to the author if no user is mentioned
    avatar_url = member.avatar.url

    # Send just the avatar URL (styled message)
    await send_styled(ctx, f"Here is the avatar URL of {member.name}:\n{avatar_url}")

    # Wait for 1 second
    await asyncio.sleep(1)

    # Send the avatar image without any additional text
    await ctx.send(avatar_url)


@client.command()
async def roles(ctx, user: discord.User):
    """Get the roles of a user."""
    if isinstance(user, discord.Member):
        roles = [role.name for role in user.roles if role.name != "@everyone"]
        await send_styled(ctx, f"{user.name}'s roles: {', '.join(roles)}")
    else:
        await send_styled(ctx, f"{user.name} is not in this server or does not have roles.")


@client.command()
async def leetspeak(ctx, *, text: str):
    """Converts text to leet speak."""
    leet_dict = {
        'a': '4', 'b': '8', 'c': '<', 'e': '3', 'f': '|=', 'g': '6', 'h': '#', 'i': '1', 'j': ']', 
        'k': '|<', 'l': '1', 'm': '/\/\\', 'n': '/\/', 'o': '0', 'p': '|*', 'q': '9', 'r': '|2', 
        's': '$', 't': '7', 'u': '|_|', 'v': '\/', 'w': '\/\/', 'x': '><', 'y': 'j', 'z': '2'
    }
    leet_text = ''.join([leet_dict.get(char.lower(), char) for char in text])
    await send_styled(ctx, f"Leet Speak: {leet_text}")
    await ctx.message.delete()


@client.command()
async def meme(ctx):
    """Send a random meme"""
    try:
        response = requests.get("https://meme-api.com/gimme")
        data = response.json()
        meme_url = data['url']
        await send_styled(ctx, f"🤣 **Meme**: {meme_url}")
        await asyncio.sleep(2)
        await ctx.send(meme_url)  # Sends the meme URL as plain text
    except Exception as e:
        await send_styled(ctx, "Oops! Couldn't fetch a meme at the moment.")
    await ctx.message.delete()

@client.command()
async def lenny(ctx):
    """Send a random Lenny face"""
    lenny_faces = [
        "( ͡° ͜ʖ ͡°)", "(¬‿¬)", "(° ͜ʖ°)", "(¬_¬)", "( ͡ᵔ ͜ʖ ͡ᵔ )"
    ]
    lenny = random.choice(lenny_faces)
    await send_styled(ctx, lenny)
    await ctx.message.delete()


@client.command()
async def reverse(ctx, *, message: str):
    """Reverse the given message"""
    reversed_message = message[::-1]
    await send_styled(ctx, reversed_message)
    await ctx.message.delete()

@client.command()
async def remind(ctx, time: int, *, message: str):
    """Set a reminder"""
    await send_styled(ctx, f"Reminder set for {time} seconds!")
    await ctx.message.delete()
    await asyncio.sleep(time)
    await send_styled(ctx, f"⏰ Reminder: {message}")


# Command 18: Self Destruct Command (Delete bot's own messages)
@client.command()
async def selfdestruct(ctx):
    """Delete the bot's message"""
    await ctx.message.delete()  # Delete the bot's own message

# Run the bot with the token from the .env file
client.run(TOKEN)
