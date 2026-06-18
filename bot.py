import telebot
import requests
import time
import asyncio
from pytoniq import LiteBalancer, WalletV4R2

BOT_TOKEN = "8532448307:AAEkFjTBmGU_WdSY-lrEFi-zpHWBJvi_pWA"
MNEMONIC = "endless woman interest senior inner arrive educate stage talk throw useful sphere ranch urban list above plate join glare peace borrow buyer armed shift".split()
ADMIN_ID = 6520878121

bot = telebot.TeleBot(BOT_TOKEN)

async def send_ton_async(to_address, amount_ton):
    provider = LiteBalancer.from_mainnet_config(trust_level=1)
    await provider.start_up()
    wallet = await WalletV4R2.from_mnemonic(provider, MNEMONIC)
    await wallet.transfer(to_address, amount=int(amount_ton * 1e9), body="")
    await provider.close_all()

def do_send(message, amount, to_address):
    status_msg = bot.reply_to(message, f"⏳ Sending {amount} TON...")
    try:
        asyncio.run(send_ton_async(to_address, amount))
        time.sleep(10)
        tx_url = f"https://tonviewer.com/{to_address}"
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
