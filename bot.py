import telebot
import requests
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.contract.wallet import WalletV4ContractR2
from tonsdk.utils import to_nano, bytes_to_b64str
import base64

BOT_TOKEN = "8532448307:AAG3ASGbyURZ1CSWnlNOD9HpWtdU5zfPIn8"
MNEMONIC = "endless woman interest senior inner arrive educate stage talk throw useful sphere ranch urban list above plate join glare peace borrow buyer armed shift".split()
ADMIN_ID = 6520878121
TONCENTER = "https://toncenter.com/api/v2"

bot = telebot.TeleBot(BOT_TOKEN)

def get_seqno(address):
    r = requests.get(f"{TONCENTER}/runGetMethod", params={
        "address": address, "method": "seqno", "stack": "[]"
    }).json()
    return int(r["result"]["stack"][0][1], 16)

def send_ton(to_address, amount_ton):
    pub_k, priv_k = mnemonic_to_wallet_key(MNEMONIC)
    wallet = WalletV4ContractR2(public_key=pub_k, private_key=priv_k)
    addr = wallet.address.to_string(True, True, True)
    seqno = get_seqno(addr)
    query = wallet.create_transfer_message(
        to_addr=to_address,
        amount=to_nano(amount_ton, "ton"),
        seqno=seqno
    )
    boc = bytes_to_b64str(query["message"].to_boc(False))
    requests.post(f"{TONCENTER}/sendBoc", json={"boc": boc})

@bot.message_handler(commands=['send'])
def handle_send(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Sirf Admin send kar sakta hai!")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "⚠️ Format: /send <amount> <ton_address>")
        return
    amount = float(parts[1])
    address = parts[2]
    bot.reply_to(message, f"⏳ {amount} TON bhej raha hun...")
    try:
        send_ton(address, amount)
        bot.reply_to(message, f"✅ {amount} TON bhej diya!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

bot.polling()
