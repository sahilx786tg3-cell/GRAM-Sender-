import telebot
import requests
import time
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.contract.wallet import WalletV4ContractR2
from tonsdk.utils import to_nano, bytes_to_b64str

BOT_TOKEN = "8532448307:AAEkFjTBmGU_WdSY-lrEFi-zpHWBJvi_pWA"
MNEMONIC = "endless woman interest senior inner arrive educate stage talk throw useful sphere ranch urban list above plate join glare peace borrow buyer armed shift".split()
ADMIN_ID = 6520878121
TONCENTER = "https://toncenter.com/api/v2"
TONCENTER_API_KEY = "73f3d7b1bf8117d8d2e2a9cf32b8c9f7d0cee9664908efbeaeee7d37c16f6fd4"

bot = telebot.TeleBot(BOT_TOKEN)

def get_headers():
    return {"X-API-Key": TONCENTER_API_KEY}

def get_wallet():
    pub_k, priv_k = mnemonic_to_wallet_key(MNEMONIC)
    wallet = WalletV4ContractR2(public_key=pub_k, private_key=priv_k)
    addr = wallet.address.to_string(True, True, True)
    return addr, wallet

def get_seqno(address):
    try:
        r = requests.get(
            f"{TONCENTER}/runGetMethod",
            params={"address": address, "method": "seqno", "stack": "[]"},
            headers=get_headers(), timeout=10
        ).json()
        stack = r.get("result", {}).get("stack", [])
        return int(stack[0][1], 16) if stack else 0
    except:
        return 0

def get_balance(address):
    try:
        r = requests.get(
            f"{TONCENTER}/getAddressInformation",
            params={"address": address},
            headers=get_headers(), timeout=10
        ).json()
        return int(r["result"]["balance"]) / 1e9
    except:
        return None

def send_ton(to_address, amount_ton):
    addr, wallet = get_wallet()
    seqno = get_seqno(addr)
    query = wallet.create_transfer_message(
        to_addr=to_address,
        amount=to_nano(amount_ton, "ton"),
        seqno=seqno,
        send_mode=3,
        payload=""
    )
    boc = bytes_to_b64str(query["message"].to_boc(False))
    r = requests.post(
        f"{TONCENTER}/sendBoc",
        json={"boc": boc},
        headers=get_headers(), timeout=15
    ).json()
    return r

def get_last_tx_hash(address):
    time.sleep(15)
    try:
        r = requests.get(
            f"{TONCENTER}/getTransactions",
            params={"address": address, "limit": 5},
            headers=get_headers(), timeout=10
        ).json()
        for tx in r.get("result", []):
            if tx.get("out_msgs") and len(tx["out_msgs"]) > 0:
                return tx["transaction_id"]["hash"]
    except:
        pass
    return None

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    user_id = message.from_user.id
    text = message.text.strip()
    lower = text.lower()

    # /balance
    if lower == "/balance":
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can use this.")
            return
        addr, _ = get_wallet()
        balance = get_balance(addr)
        if balance is not None:
            bot.reply_to(message, f"Wallet Balance: `{balance:.4f} TON`\n\nAddress:\n`{addr}`", parse_mode="Markdown")
        else:
            bot.reply_to(message, "Failed to fetch balance.")
        return

    # /send - reply karke use karo
    if lower.startswith("/send"):
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can send.")
            return

        # Amount lo
        parts = text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Format: /send <amount>\nReply karke user ke address message pe!")
            return

        try:
            amount = float(parts[1])
        except:
            bot.reply_to(message, "Invalid amount. Example: /send 0.1")
            return

        # Reply check karo
        if not message.reply_to_message:
            bot.reply_to(message, "⚠️ User ke TON address wale message pe reply karke /send karo!")
            return

        # Us message se address uthao
        replied_text = message.reply_to_message.text.strip() if message.reply_to_message.text else ""
        to_address = replied_text.strip()

        if not to_address or len(to_address) < 20:
            bot.reply_to(message, "❌ Valid TON address nahi mila us message mein!")
            return

        status_msg = bot.reply_to(
            message,
            f"⏳ Sending {amount} TON to `{to_address}`...",
            parse_mode="Markdown"
        )

        try:
            result = send_ton(to_address, amount)
            if not result.get("ok"):
                error = result.get("error", "Unknown error")
                bot.edit_message_text(
                    f"❌ Transaction Failed!\nReason: {error}",
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id
                )
                return

            addr, _ = get_wallet()
            tx_hash = get_last_tx_hash(addr)

            if tx_hash:
                tx_url = f"https://tonviewer.com/transaction/{tx_hash}"
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
            else:
                bot.edit_message_text(
                    f"✅ {amount} TON Sent!\n\n"
                    f"💰 Amount: {amount} TON\n"
                    f"📬 To: `{to_address}`\n\n"
                    f"[🔍 View on Explorer](https://tonviewer.com/{addr})\n\n"
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
        return

print("Bot is running...")
bot.polling(none_stop=True)
