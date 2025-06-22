import discord
import os
import re
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
TOKEN = os.getenv("HAILBOT_TOKEN")
TARGET_CHANNEL_ID = os.getenv('db2id')
SOURCE_CHANNEL_ID = os.getenv('devid')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    try:
        first_channel = client.get_channel(TARGET_CHANNEL_ID)
        if not first_channel:
            print(f"Error: Channel with ID {TARGET_CHANNEL_ID} not found.")
            await client.close()
            return

        last_message = None
        async for message in first_channel.history(limit=1):
            last_message = message

        if not last_message:
            print(f"No messages found in channel {TARGET_CHANNEL_ID}.")
            await client.close()
            return

        content = last_message.content
        lines = content.strip().split("\n")
        latest_date = None
        for line in lines:
            try:
                date_str = re.search(
                    r"(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} (?:AM|PM))", line
                )
                if date_str:
                    try:
                        current_date = datetime.strptime(
                            date_str.group(1), "%d/%m/%Y %I:%M %p"
                        )
                        if latest_date is None or current_date > latest_date:
                            latest_date = current_date
                    except ValueError:
                        continue
            except (ValueError, IndexError):
                continue

        if latest_date is None:
            print("No valid date found in the last message.")
            await client.close()
            return

        second_channel = client.get_channel(SOURCE_CHANNEL_ID)
        if not second_channel:
            print(f"Error: Channel with ID {SOURCE_CHANNEL_ID} not found.")
            await client.close()
            return

        messages_after_date = []
        async for message in second_channel.history(
            limit=None, after=latest_date.replace(tzinfo=timezone.utc)
        ):
            if "nt" in message.content.lower():
                messages_after_date.append(message)
#
        filtered_messages = []
        for message in messages_after_date:
            if re.search(r"(\.|\b)nt\s+\d+\s+\d+", message.content, re.IGNORECASE):
                filtered_messages.append(message)

        filtered_messages.sort(key=lambda x: x.created_at)
#
        if not filtered_messages:
            print("No messages found matching the criteria.")
            await client.close()
            return
#
        final_message_parts = []
        for msg in filtered_messages:
            local_time = msg.created_at.astimezone(timezone.utc)

            formatted_date = local_time.strftime("%#d/%#m/%Y %#I:%M %p")

            match = re.search(r"(\.|\b)nt\s+(\d+\s+\d+)", msg.content, re.IGNORECASE)
            if match:
                message_part = match.group(2)
                final_message_parts.append(f"{formatted_date} {message_part}")

        final_message = "\n".join(final_message_parts)

        target_channel = client.get_channel(TARGET_CHANNEL_ID)
        if target_channel:
            await target_channel.send(final_message)
            print("Message sent successfully.")
        else:
            print(
                f"Error: Target channel with ID {TARGET_CHANNEL_ID} not found for sending the message."
            )

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()
        print("Bot has shut down.")


client.run(TOKEN)
