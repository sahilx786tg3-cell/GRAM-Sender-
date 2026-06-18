import telebot
import requests
import time
import asyncio
import base64
from pytoniq import LiteBalancer, WalletV4R2

BOT_TOKEN = "8532448307:AAHnURBUFaBTPxvPT8W6h8rLw_kKGjgRTe4"
MNEMONIC = "endless woman interest senior inner arrive educate stage talk throw useful sphere ranch urban list above plate join glare peace borrow buyer armed shift".split()
ADMIN_ID = 6520878121
WALLET_ADDRESS = "EQBs2e9qbnIwREgnRtjg1zLiMv9tlCQGzYZ7Eq66ChGMz3M-"

bot = telebot.TeleBot(BOT_TOKEN)

async def send_ton_async(to_address, amount_ton):
    provider = LiteBalancer.from_mainnet_config(trust_level=1)
    await provider.start_up()
    wallet = await WalletV4R2.from_mnemonic(provider, MNEMONIC)
    result = await wallet.transfer(
        to_address,
        amount=int(amount_ton * 1e9),
        body=""
    )
    await provider.close_all()
    return result

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

def get_tx_hash():
    try:
        r = requests.get(
            "https://toncenter.com/api/v2/getTransactions",
            params={"address": WALLET_ADDRESS, "limit": 5},
            timeout=10
        ).json()
        for tx in r.get("result", []):
            if tx.get("out_msgs") and len(tx["out_msgs"]) > 0:
                raw_hash = tx["transaction_id"]["hash"]
                decoded = base64.b64decode(raw_hash)
                hex_hash = decoded.hex().upper()
                return hex_hash
    except Exception as e:
        print(f"[HASH ERROR] {e}")
    return None

def do_send(message, amount, to_address):
    status_msg = bot.reply_to(message, f"⏳ Sending {amount} TON...")
    try:
        run_async(send_ton_async(to_address, amount))
        time.sleep(15)
        tx_hash = get_tx_hash()
        if tx_hash:
            tx_url = f"https://tonviewer.com/transaction/{tx_hash}"
        else:
            tx_url = f"https://tonviewer.com/{WALLET_ADDRESS}"
        bot.edit_message_text(
            f"✅ {amount} TON Sent Successfully!\n\n"
            f"💰 Amount: {amount} TON\n"
            f"📬 To: `{to_address}`\n"
            f"🧾 Status: Success\n\n"
            f"[🔍 View on Explorer]({tx_url})\n\n"
            f"🤖 Bot: @GramSenderAiBot",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"[SEND ERROR] {e}")
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    user_id = message.from_user.id
    text = message.text.strip()
    lower = text.lower()

    if lower == "/balance":
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can use this.")
            return
        try:
            r = requests.get(
                "https://toncenter.com/api/v2/getAddressInformation",
                params={"address": WALLET_ADDRESS},
                timeout=10
            ).json()
            balance = int(r["result"]["balance"]) / 1e9
            bot.reply_to(
                message,
                f"💰 Balance: `{balance:.4f} TON`\n\nAddress:\n`{WALLET_ADDRESS}`",
                parse_mode="Markdown"
            )
        except:
            bot.reply_to(message, f"Check manually:\nhttps://tonviewer.com/{WALLET_ADDRESS}")
        return

    if lower.startswith("/send"):
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can send.")
            return
        parts = text.split()

        if len(parts) == 3:
            try:
                amount = float(parts[1])
                to_address = parts[2]
                do_send(message, amount, to_address)
            except:
                bot.reply_to(message, "Format: /send 0.1 <ton_address>")
            return

        if len(parts) == 2:
            if not message.reply_to_message or not message.reply_to_message.text:
                bot.reply_to(message, "⚠️ Address wale message pe reply karke /send 0.1 likho!")
                return
            try:
                amount = float(parts[1])
                to_address = message.reply_to_message.text.strip()
                do_send(message, amount, to_address)
            except:
                bot.reply_to(message, "Format: /send 0.1")
            return

        bot.reply_to(message, "Format:\n/send 0.1 <address>\nYa address pe reply karke /send 0.1")
        return

print("Bot is running...")
bot.polling(none_stop=True)
