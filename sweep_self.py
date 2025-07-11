import os
import re
import discord
from dotenv import load_dotenv
from datetime import datetime, timezone


load_dotenv()


TOKEN = os.getenv("HAIL_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID") or os.getenv("db2id"))
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID") or os.getenv("devid"))

client = discord.Client()

def parse_latest_date(message_content: str) -> datetime | None:
    latest: datetime | None = None
    for line in message_content.splitlines():
        match = re.search(r"(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} (?:AM|PM))", line)
        if match:
            try:
                dt = datetime.strptime(match.group(1), "%d/%m/%Y %I:%M %p").replace(
                    tzinfo=timezone.utc
                )
                if latest is None or dt > latest:
                    latest = dt
            except ValueError:
                continue
    return latest


def fmt_date(dt: datetime) -> str:
    out = dt.strftime("%d/%m/%Y %I:%M %p")

    out = re.sub(r"\b0(\d)", r"\1", out)
    return out


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    try:
        target_channel = client.get_channel(TARGET_CHANNEL_ID)
        source_channel = client.get_channel(SOURCE_CHANNEL_ID)
        if not target_channel or not source_channel:
            print("❌ One or both channels could not be found. Check the channel IDs.")
            await client.close()
            return

        latest_date: datetime | None = None
        async for last_msg in target_channel.history(limit=1):
            latest_date = parse_latest_date(last_msg.content)

        if latest_date is None:
            latest_date = datetime.min.replace(tzinfo=timezone.utc)

        pattern_full = re.compile(r"(\.|\b)nt\s+(\d+\s+\d+)", re.IGNORECASE)
        matching_messages: list[discord.Message] = []
        async for msg in source_channel.history(limit=None, after=latest_date):
            if pattern_full.search(msg.content):
                matching_messages.append(msg)

        if not matching_messages:
            print("ℹ️ No new matching messages found. Nothing to send.")
            await client.close()
            return

        matching_messages.sort(key=lambda m: m.created_at)
        lines: list[str] = []
        for m in matching_messages:
            utc_time = m.created_at.astimezone(timezone.utc)
            formatted_time = fmt_date(utc_time)
            data = pattern_full.search(m.content).group(2)
            lines.append(f"{formatted_time} {data}")

        final_message = "\n".join(lines[1:])
        if final_message:
            await target_channel.send(final_message)
            print("✅ Message sent successfully.")
        else:
            print("ℹ️ No valid data to send in the message.")

    except Exception as e:
        print(f"⚠️ An error occurred: {e}")

    finally:
        await client.close()
        print("🔒 Bot session closed.")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("TOKEN (or HAILBOT_TOKEN) environment variable not set.")

    client.run(TOKEN)
