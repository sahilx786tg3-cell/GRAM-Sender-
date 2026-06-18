import os
import telebot
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import to_nano
from tonsdk.provider import ToncenterClient

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MNEMONIC = os.environ.get("MNEMONIC").split()

bot = telebot.TeleBot(BOT_TOKEN)

def send_ton(to_address, amount_ton):
    client = ToncenterClient(base_url="https://toncenter.com/api/v2/", api_key="")
    mnemonics, pub_k, priv_k, wallet = Wallets.from_mnemonics(
        MNEMONIC, WalletVersionEnum.v4r2, workchain=0
    )
    seqno = client.run_get_method(
        address=wallet.address.to_string(True, True, True),
        method="seqno", stack_data=[]
    )
    query = wallet.create_transfer_message(
        to_addr=to_address,
        amount=to_nano(amount_ton, "ton"),
        seqno=int(seqno["stack"][0][1], 16)
    )
    client.raw_send_message(query["message"].to_boc(False))

@bot.message_handler(commands=['send'])
def handle_send(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    admins = [a.user.id for a in bot.get_chat_administrators(chat_id)]
    if user_id not in admins:
        bot.reply_to(message, "❌ Sirf admins send kar sakte hain!")
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
        bot.reply_to(message, f"✅ {amount} TON successfully bheja!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

bot.polling()
