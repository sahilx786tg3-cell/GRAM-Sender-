import telebot
import requests
import time
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.contract.wallet import WalletV4ContractR2
from tonsdk.utils import to_nano, bytes_to_b64str

BOT_TOKEN = "8532448307:AAG3ASGbyURZ1CSWnlNOD9HpWtdU5zfPIn8"
MNEMONIC = "endless woman interest senior inner arrive educate stage talk throw useful sphere ranch urban list above plate join glare peace borrow buyer armed shift".split()
ADMIN_ID = 6520878121
TONCENTER = "https://toncenter.com/api/v2"
TONCENTER_API_KEY = "73f3d7b1bf8117d8d2e2a9cf32b8c9f7d0cee9664908efbeaeee7d37c16f6fd4"


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
            headers=get_headers(),
            timeout=10
        ).json()
        print(f"[SEQNO] {r}")
        stack = r.get("result", {}).get("stack", [])
        if stack:
            return int(stack[0][1], 16)
        return 0
    except Exception as e:
        print(f"[SEQNO ERROR] {e}")
        return 0


def get_balance(address):
    try:
        r = requests.get(
            f"{TONCENTER}/getAddressInformation",
            params={"address": address},
            headers=get_headers(),
            timeout=10
        ).json()
        print(f"[BALANCE] {r}")
        balance_nano = int(r["result"]["balance"])
        return balance_nano / 1e9
    except Exception as e:
        print(f"[BALANCE ERROR] {e}")
        return None


def send_ton(to_address, amount_ton):
    addr, wallet = get_wallet()
    seqno = get_seqno(addr)
    print(f"[SEND] From: {addr} | To: {to_address} | Amount: {amount_ton} | Seqno: {seqno}")

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
        headers=get_headers(),
        timeout=15
    ).json()
    print(f"[SENDBOC] {r}")
    return r


def get_last_tx_hash(address):
    time.sleep(15)
    try:
        r = requests.get(
            f"{TONCENTER}/getTransactions",
            params={"address": address, "limit": 5},
            headers=get_headers(),
            timeout=10
        ).json()
        for tx in r.get("result", []):
            if tx.get("out_msgs") and len(tx["out_msgs"]) > 0:
                return tx["transaction_id"]["hash"]
    except Exception as e:
        print(f"[HASH ERROR] {e}")
    return None


bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_all(message):
    user_id = message.from_user.id
    text = message.text.strip()
    print(f"[MSG] From: {user_id} | Text: {text}")

    # /myid
    if text == "/myid":
        bot.reply_to(message, f"Your Telegram ID: `{user_id}`", parse_mode="Markdown")
        return

    # /myaddress
    if text == "/myaddress":
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can use this.")
            return
        addr, _ = get_wallet()
        bot.reply_to(message, f"Wallet Address:\n`{addr}`", parse_mode="Markdown")
        return

    # /balance
    if text == "/balance":
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can use this.")
            return
        addr, _ = get_wallet()
        balance = get_balance(addr)
        if balance is not None:
            bot.reply_to(
                message,
                f"Wallet Balance: `{balance:.4f} TON`\n\nAddress:\n`{addr}`",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, "Failed to fetch balance. Check terminal.")
        return

    # /send
    if text.startswith("/send"):
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can send.")
            return

        parts = text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Format: /send <amount> <address>\nExample: /send 0.1 UQB9...")
            return

        try:
            amount = float(parts[1])
            address = parts[2]
        except ValueError:
            bot.reply_to(message, "Invalid amount. Example: /send 0.1 UQB9...")
            return

        if amount <= 0:
            bot.reply_to(message, "Amount must be greater than 0.")
            return

        status_msg = bot.reply_to(
            message,
            f"Sending {amount} TON to\n`{address}`...",
            parse_mode="Markdown"
        )

        try:
            result = send_ton(address, amount)

            if not result.get("ok"):
                error = result.get("error", "Unknown error")
                bot.edit_message_text(
                    f"Transaction Failed!\nReason: {error}",
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id
                )
                return

            addr, _ = get_wallet()
            tx_hash = get_last_tx_hash(addr)

            if tx_hash:
                bot.edit_message_text(
                    f"{amount} TON Sent!\n\nTransaction:\nhttps://tonviewer.com/transaction/{tx_hash}",
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id
                )
            else:
                bot.edit_message_text(
                    f"{amount} TON Sent!\n\nCheck wallet:\nhttps://tonviewer.com/{addr}",
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id
                )

        except Exception as e:
            print(f"[SEND ERROR] {e}")
            bot.edit_message_text(
                f"Error: {str(e)}",
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id
            )
        return


print("Bot is running...")
bot.polling(none_stop=True)
