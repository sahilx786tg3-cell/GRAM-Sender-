import telebot
import requests
import time
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.contract.wallet import WalletV4ContractR2
from tonsdk.utils import to_nano, bytes_to_b64str

BOT_TOKEN = "8532448307:AAG3ASGbyURZ1CSWnlNOD9HpWtdU5zfPIn8"
MNEMONIC = "endless woman interest senior inner arrive educate stage talk throw useful sphere ranch urban list above plate join glare peace borrow buyer armed shift".split()
ADMIN_ID = 6520878121

# ✅ Use v3r2 endpoint — more stable
TONCENTER = "https://toncenter.com/api/v2"
# Optional: get free API key from @tonapibot on Telegram to avoid rate limits
TONCENTER_API_KEY = ""  # paste your key here if you have one


def get_headers():
    if TONCENTER_API_KEY:
        return {"X-API-Key": TONCENTER_API_KEY}
    return {}


def get_wallet():
    pub_k, priv_k = mnemonic_to_wallet_key(MNEMONIC)
    wallet = WalletV4ContractR2(public_key=pub_k, private_key=priv_k)
    addr = wallet.address.to_string(True, True, True)
    return addr, wallet, pub_k, priv_k


def get_seqno(address):
    try:
        r = requests.get(
            f"{TONCENTER}/runGetMethod",
            params={"address": address, "method": "seqno", "stack": "[]"},
            headers=get_headers(),
            timeout=10
        ).json()
        print(f"[SEQNO RESPONSE] {r}")
        result = r.get("result", {})
        stack = result.get("stack", [])
        if stack:
            return int(stack[0][1], 16)
        return 0
    except Exception as e:
        print(f"[SEQNO ERROR] {e}")
        return 0


def send_ton(to_address, amount_ton):
    addr, wallet, pub_k, priv_k = get_wallet()
    seqno = get_seqno(addr)
    print(f"[SEND] From: {addr} | To: {to_address} | Amount: {amount_ton} TON | Seqno: {seqno}")

    # ✅ Correct way to build transfer for WalletV4ContractR2
    query = wallet.create_transfer_message(
        to_addr=to_address,
        amount=to_nano(amount_ton, "ton"),
        seqno=seqno,
        send_mode=3,
        payload=""
    )

    boc = bytes_to_b64str(query["message"].to_boc(False))
    print(f"[BOC] {boc[:60]}...")

    r = requests.post(
        f"{TONCENTER}/sendBoc",
        json={"boc": boc},
        headers=get_headers(),
        timeout=15
    ).json()

    print(f"[SENDBOC RESPONSE] {r}")
    return r


def get_last_tx_hash(address):
    # Wait for TON network to confirm
    time.sleep(15)
    try:
        r = requests.get(
            f"{TONCENTER}/getTransactions",
            params={"address": address, "limit": 5},
            headers=get_headers(),
            timeout=10
        ).json()
        print(f"[TX RESPONSE] {r}")
        for tx in r.get("result", []):
            # Outgoing tx has out_msgs
            if tx.get("out_msgs") and len(tx["out_msgs"]) > 0:
                return tx["transaction_id"]["hash"]
    except Exception as e:
        print(f"[HASH ERROR] {e}")
    return None


bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["myaddress"])
def handle_address(message):
    if message.from_user.id != ADMIN_ID:
        return
    addr, _, _, _ = get_wallet()
    bot.reply_to(message, f"Wallet Address:\n`{addr}`", parse_mode="Markdown")


@bot.message_handler(commands=["balance"])
def handle_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    addr, _, _, _ = get_wallet()
    try:
        r = requests.get(
            f"{TONCENTER}/getAddressBalance",
            params={"address": addr},
            headers=get_headers(),
            timeout=10
        ).json()
        print(f"[BALANCE RESPONSE] {r}")
        balance_nano = int(r["result"])
        balance_ton = balance_nano / 1e9
        bot.reply_to(message, f"Balance: `{balance_ton:.4f} TON`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Error fetching balance: {str(e)}")


@bot.message_handler(commands=["send"])
def handle_send(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Only Admin can send!")
        return

    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "Format: /send <amount> <ton_address>\nExample: /send 0.1 UQB9...")
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

    status_msg = bot.reply_to(message, f"Sending {amount} TON to\n`{address}`...", parse_mode="Markdown")

    try:
        result = send_ton(address, amount)

        # ✅ Check if TonCenter accepted it
        if not result.get("ok"):
            error_detail = result.get("error", "Unknown error from TonCenter")
            bot.edit_message_text(
                f"Transaction Failed!\nReason: {error_detail}",
                chat_id=status_msg.chat.id,
                message_id=status_msg.message_id
            )
            return

        # Fetch hash
        addr, _, _, _ = get_wallet()
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
        print(f"[SEND EXCEPTION] {e}")
        bot.edit_message_text(
            f"Error: {str(e)}",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id
        )


print("Bot started...")
bot.polling()
