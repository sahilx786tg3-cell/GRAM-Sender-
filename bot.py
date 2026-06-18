import telebot
import requests
import time
import base64
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.contract.wallet import WalletV4ContractR2
from tonsdk.utils import to_nano, bytes_to_b64str

BOT_TOKEN = "8532448307:AAFrBbTkMTHQzXjQAxbGWa_in7rdr_F9hkI"
MNEMONIC = "endless woman interest senior inner arrive educate stage talk throw useful sphere ranch urban list above plate join glare peace borrow buyer armed shift".split()
ADMIN_ID = 6520878121
TONCENTER = "https://toncenter.com/api/v2"
TONCENTER_API_KEY = "73f3d7b1bf8117d8d2e2a9cf32b8c9f7d0cee9664908efbeaeee7d37c16f6fd4"

bot = telebot.TeleBot(BOT_TOKEN)
processing = False


def get_headers():
    return {"X-API-Key": TONCENTER_API_KEY}


def get_wallet():
    pub_k, priv_k = mnemonic_to_wallet_key(MNEMONIC)
    wallet = WalletV4ContractR2(public_key=pub_k, private_key=priv_k)
    addr = wallet.address.to_string(True, True, False)
    return addr, wallet, pub_k, priv_k


def get_balance():
    addr, _, _, _ = get_wallet()
    try:
        r = requests.get(
            f"{TONCENTER}/getAddressInformation",
            params={"address": addr},
            headers=get_headers(),
            timeout=10
        ).json()
        print(f"[BALANCE] {r}")
        return int(r["result"]["balance"]) / 1e9
    except Exception as e:
        print(f"[BALANCE ERROR] {e}")
        return None


def get_wallet_state():
    addr, _, _, _ = get_wallet()
    try:
        r = requests.get(
            f"{TONCENTER}/getAddressInformation",
            params={"address": addr},
            headers=get_headers(),
            timeout=10
        ).json()
        return r["result"].get("state", "uninitialized")
    except:
        return "unknown"


def get_seqno():
    addr, _, _, _ = get_wallet()
    try:
        r = requests.get(
            f"{TONCENTER}/getWalletInformation",
            params={"address": addr},
            headers=get_headers(),
            timeout=10
        ).json()
        print(f"[SEQNO] {r}")
        seqno = r["result"].get("seqno") or 0
        return int(seqno)
    except Exception as e:
        print(f"[SEQNO ERROR] {e}")
        return 0


def deploy_wallet():
    addr, wallet, _, _ = get_wallet()
    try:
        query = wallet.create_init_external_message()
        boc = bytes_to_b64str(query["message"].to_boc(False))
        r = requests.post(
            f"{TONCENTER}/sendBoc",
            json={"boc": boc},
            headers=get_headers(),
            timeout=15
        ).json()
        print(f"[DEPLOY] {r}")
        return r
    except Exception as e:
        print(f"[DEPLOY ERROR] {e}")
        return {"ok": False, "error": str(e)}


def send_ton(to_address, amount_ton):
    addr, wallet, _, _ = get_wallet()
    seqno = get_seqno()
    print(f"[SEND] Seqno: {seqno} | To: {to_address} | Amount: {amount_ton}")

    query = wallet.create_transfer_message(
        to_addr=to_address,
        amount=to_nano(amount_ton, "ton"),
        seqno=seqno,
        send_mode=3
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


def get_tx_hash():
    addr, _, _, _ = get_wallet()
    try:
        r = requests.get(
            f"{TONCENTER}/getTransactions",
            params={"address": addr, "limit": 5},
            headers=get_headers(),
            timeout=10
        ).json()
        for tx in r.get("result", []):
            if tx.get("out_msgs") and len(tx["out_msgs"]) > 0:
                raw = tx["transaction_id"]["hash"]
                return base64.b64decode(raw).hex().upper()
    except Exception as e:
        print(f"[HASH ERROR] {e}")
    return None


def do_send(message, amount, to_address):
    global processing
    if processing:
        bot.reply_to(message, "One transaction already running, please wait!")
        return

    clean_address = to_address.strip()
    if len(clean_address) != 48:
        bot.reply_to(
            message,
            f"Invalid TON address!\nGot {len(clean_address)} characters, need 48.\n\nAddress:\n`{clean_address}`",
            parse_mode="Markdown"
        )
        return

    balance = get_balance()
    if balance is None:
        bot.reply_to(message, "Balance check failed! Try again.")
        return

    if balance < amount + 0.01:
        bot.reply_to(
            message,
            f"Insufficient Balance!\n\n"
            f"Available: `{balance:.4f} TON`\n"
            f"Required: `{amount + 0.01:.4f} TON` (including fees)\n\n"
            f"Add more TON to wallet first!",
            parse_mode="Markdown"
        )
        return

    state = get_wallet_state()
    print(f"[STATE] {state}")

    if state == "uninitialized":
        bot.reply_to(message, "Wallet not deployed yet!\nSend /deploy first, then try again.")
        return

    processing = True
    status_msg = bot.reply_to(message, f"Sending {amount} TON...")

    try:
        result = send_ton(clean_address, amount)

        if not result.get("ok"):
            error = result.get("error", "Unknown error")
            bot.edit_message_text(
                f"Transaction Failed!\nReason: {error}",
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id
            )
            processing = False
            return

        time.sleep(15)
        tx_hash = get_tx_hash()
        addr, _, _, _ = get_wallet()
        tx_url = f"https://tonviewer.com/transaction/{tx_hash}" if tx_hash else f"https://tonviewer.com/{addr}"

        bot.edit_message_text(
            f"{amount} TON Sent!\n\n"
            f"Amount: `{amount} TON`\n"
            f"To: `{clean_address}`\n\n"
            f"[View Transaction]({tx_url})",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"[SEND ERROR] {e}")
        bot.edit_message_text(
            f"Error: {str(e)}",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )
    finally:
        processing = False


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    user_id = message.from_user.id
    text = message.text.strip()
    lower = text.lower()
    print(f"[MSG] From: {user_id} | Text: {text}")

    if lower == "/myid":
        bot.reply_to(message, f"Your ID: `{user_id}`", parse_mode="Markdown")
        return

    if lower == "/myaddress":
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin.")
            return
        addr, _, _, _ = get_wallet()
        bot.reply_to(message, f"Wallet Address:\n`{addr}`", parse_mode="Markdown")
        return

    if lower == "/balance":
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin can use this.")
            return
        balance = get_balance()
        addr, _, _, _ = get_wallet()
        state = get_wallet_state()
        if balance is not None:
            bot.reply_to(
                message,
                f"Wallet Balance: `{balance:.4f} TON`\n"
                f"Wallet State: `{state}`\n\n"
                f"Address:\n`{addr}`",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message, f"Check:\nhttps://tonviewer.com/{addr}")
        return

    if lower == "/deploy":
        if user_id != ADMIN_ID:
            bot.reply_to(message, "Only Admin.")
            return
        state = get_wallet_state()
        if state == "active":
            bot.reply_to(message, "Wallet is already active! No need to deploy.")
            return
        bot.reply_to(message, "Deploying wallet...")
        result = deploy_wallet()
        if result.get("ok"):
            bot.reply_to(message, "Wallet deployed! Wait 30 seconds then try /send again.")
        else:
            bot.reply_to(message, f"Deploy failed!\nReason: {result.get('error', 'Unknown')}")
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
            except ValueError:
                bot.reply_to(message, "Format: /send 0.1 UQB9...")
            return

        if len(parts) == 2:
            if not message.reply_to_message or not message.reply_to_message.text:
                bot.reply_to(message, "Reply to address message and send /send 0.1")
                return
            try:
                amount = float(parts[1])
                to_address = message.reply_to_message.text.strip()
                do_send(message, amount, to_address)
            except ValueError:
                bot.reply_to(message, "Format: /send 0.1")
            return

        bot.reply_to(message, "Format: /send 0.1 <address>")
        return


print("Bot is running...")
bot.polling(none_stop=True, interval=0)
