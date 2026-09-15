import os
from threading import Thread
from flask import Flask
import telebot
from telebot import types

TOKEN = "8993446973:AAHWwhHLX3ufmr9gJEtnZVEK6n-otengvM0"
ADMIN_ID = 6262854630

# 1. आपके मेन दो चैनल
CHANNEL_1 = "@ksp008h"
CHANNEL_2 = "@abjllgt765"

WELCOME_IMAGE_URL = "https://iili.io/ndFZlta.md.jpg"
ADMIN_USERNAME = "Helpbot655_bot"

bot = telebot.TeleBot(TOKEN)

users = {}
pending_refs = {}

# डिफ़ॉल्ट सेटिंग्स: 10 कॉइन्स = ₹1, मिनिमम विथड्रॉल 50, और रेफरल पर 5 कॉइन्स
bot_settings = {
    "coins_per_rupee": 10,
    "min_withdrawal_coins": 50,
    "referral_reward": 5,
}

tasks = [
    {
        "id": 1,
        "title": "Join Sponsor Channel A (+10 Coins)",
        "link": "https://t.me/sponsor_channel_a",
        "channel": "@sponsor_channel_a",
        "type": "channel",
        "reward": 10,
    },
    {
        "id": 2,
        "title": "Install Earn App (+25 Coins)",
        "link": "https://play.google.com/store/apps/details?id=example.app",
        "type": "app",
        "reward": 25,
    },
]
withdrawals = []
app_submissions = []
user_state = {}


def check_subscription(user_id):
  try:
    if user_id == ADMIN_ID:
      return True
    member1 = bot.get_chat_member(CHANNEL_1, user_id)
    member2 = bot.get_chat_member(CHANNEL_2, user_id)
    valid_statuses = ["creator", "administrator", "member"]
    if member1.status in valid_statuses and member2.status in valid_statuses:
      return True
  except Exception as e:
    print(f"Main subscription check error: {e}")
  return False


def get_join_markup():
  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "📢 Join Channel 1",
          url=f"https://t.me/{CHANNEL_1.replace('@', '')}",
      )
  )
  markup.add(
      types.InlineKeyboardButton(
          "📢 Join Channel 2",
          url=f"https://t.me/{CHANNEL_2.replace('@', '')}",
      )
  )
  markup.add(
      types.InlineKeyboardButton(
          "🔄 Check Join / Verify", callback_data="check_join"
      )
  )
  return markup


def get_main_keyboard(user_id):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add(types.KeyboardButton("📋 Tasks"), types.KeyboardButton("💰 Balance"))
  markup.add(
      types.KeyboardButton("👥 Referral Link"),
      types.KeyboardButton("📤 Withdraw"),
  )
  markup.add(types.KeyboardButton("📞 Admin Support"))
  if user_id == ADMIN_ID:
    markup.add(types.KeyboardButton("👑 Admin Panel"))
  return markup


@bot.message_handler(commands=["start"])
def start(message):
  user_id = message.from_user.id
  args = message.text.split()

  if len(args) > 1:
    try:
      ref_id = int(args[1])
      if ref_id != user_id:
        pending_refs[user_id] = ref_id
    except ValueError:
      pass

  if not check_subscription(user_id):
    bot.send_message(
        message.chat.id,
        "❌ **Access Denied!**\n\nYou must join both of our official channels"
        " below to use this bot.",
        parse_mode="Markdown",
        reply_markup=get_join_markup(),
    )
    return

  if user_id not in users:
    users[user_id] = {
        "balance": 0,
        "ref_by": None,
        "completed_tasks": [],
        "upi": "",
    }
    ref_id = pending_refs.get(user_id)
    if ref_id and ref_id in users:
      users[user_id]["ref_by"] = ref_id
      ref_bonus = bot_settings["referral_reward"]
      users[ref_id]["balance"] += ref_bonus
      bot.send_message(
          ref_id, f"🎉 You got a new referral! +{ref_bonus} coins added."
      )
      pending_refs.pop(user_id, None)

  caption_text = (
      "👋 **Welcome to Earning Bot!**\n\nComplete tasks using the options"
      " below and earn money:"
  )

  try:
    bot.send_photo(
        message.chat.id,
        photo=WELCOME_IMAGE_URL,
        caption=caption_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id),
    )
  except Exception:
    bot.send_message(
        message.chat.id,
        caption_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id),
    )


@bot.message_handler(func=lambda message: True, content_types=["text", "photo"])
def handle_messages(message):
  user_id = message.from_user.id

  if not check_subscription(user_id):
    bot.send_message(
        message.chat.id,
        "❌ Please join both channels first to continue using the bot!",
        reply_markup=get_join_markup(),
    )
    return

  text = message.text if message.text else ""

  if user_id not in users:
    users[user_id] = {
        "balance": 0,
        "ref_by": None,
        "completed_tasks": [],
        "upi": "",
    }

  # --- मेनू और नेविगेशन चेक ---
  if text == "🏠 Main Menu":
    user_state[user_id] = None
    bot.send_message(
        message.chat.id,
        "Returned to Main Menu:",
        reply_markup=get_main_keyboard(user_id),
    )
    return

  if user_id == ADMIN_ID and text == "👑 Admin Panel":
    user_state[user_id] = None
    admin_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    admin_markup.add(
        types.KeyboardButton("➕ Add Task"),
        types.KeyboardButton("📋 Manage Tasks"),
    )
    admin_markup.add(
        types.KeyboardButton("💳 Payment Requests"),
        types.KeyboardButton("📱 App Task Requests"),
    )
    admin_markup.add(types.KeyboardButton("⚙️ Set Bot Settings"))
    admin_markup.add(types.KeyboardButton("🏠 Main Menu"))
    bot.send_message(
        message.chat.id,
        "👑 Welcome to Admin Panel:",
        reply_markup=admin_markup,
    )
    return

  # --- स्टेट्स (States) की जाँच ---
  state = user_state.get(user_id)

  if state and state.startswith("WAITING_FOR_APP_PROOF_"):
    task_id = int(state.split("_")[-1])
    task = next((t for t in tasks if t["id"] == task_id), None)

    if task:
      photo_file_id = None
      proof_text = message.text if message.text else ""

      if message.photo:
        photo_file_id = message.photo[-1].file_id
        proof_text = (
            message.caption if message.caption else "Screenshot / Image Proof"
        )

      if not proof_text and not photo_file_id:
        proof_text = "[Screenshot / Image Proof]"

      app_submissions.append({
          "user_id": user_id,
          "task_id": task_id,
          "task_title": task["title"],
          "reward": task["reward"],
          "proof": proof_text,
          "photo": photo_file_id,
          "status": "Pending",
      })

      user_state[user_id] = None
      bot.send_message(
          message.chat.id,
          "✅ **Proof Submitted Successfully!**\nSent to admin for review. Coins"
          " will be added and task will be marked complete once approved.",
          parse_mode="Markdown",
          reply_markup=get_main_keyboard(user_id),
      )
    return

  # Admin Set Bot Settings Handling (Rate, Min Withdrawal & Referral Reward)
  if user_id == ADMIN_ID and user_state.get(user_id) == "WAITING_FOR_SETTINGS":
    try:
      cleaned_text = (
          text.replace("\u200b", "")
          .replace("\u200e", "")
          .replace("\u200f", "")
          .strip()
      )
      parts = cleaned_text.split("|")

      if len(parts) == 3:
        c_rate = int(parts[0].strip())
        min_w = int(parts[1].strip())
        ref_rew = int(parts[2].strip())

        bot_settings["coins_per_rupee"] = c_rate
        bot_settings["min_withdrawal_coins"] = min_w
        bot_settings["referral_reward"] = ref_rew
        user_state[user_id] = None

        bot.send_message(
            message.chat.id,
            f"✅ **Settings Updated Successfully!**\n- Rate: `{c_rate} Coins ="
            f" ₹1`\n- Min Withdrawal: `{min_w} Coins`\n- Referral Reward:"
            f" `{ref_rew} Coins`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(user_id),
        )
      else:
        bot.send_message(
            message.chat.id,
            "❌ Wrong format! Send like"
            " this:\n`Coins_Per_Rupee | Min_Withdrawal_Coins |"
            " Referral_Reward`\nExample: `10 | 50 | 5`",
            parse_mode="Markdown",
        )
    except Exception as e:
      bot.send_message(
          message.chat.id,
          f"❌ Error: {e}\nPlease send in correct format like: `10 | 50 | 5`",
          parse_mode="Markdown",
      )
    return

  # Admin Add Task handling
  if user_id == ADMIN_ID and user_state.get(user_id) == "WAITING_FOR_TASK":
    try:
      cleaned_text = text.replace("\u200b", "").strip()
      parts = cleaned_text.split("|")
      if len(parts) >= 4:
        title = parts[0].strip()
        link = parts[1].strip()
        reward = int(parts[2].strip())
        t_type = parts[3].strip().lower()

        new_id = max([t["id"] for t in tasks], default=0) + 1
        new_task = {
            "id": new_id,
            "title": title,
            "link": link,
            "reward": reward,
            "type": t_type,
        }
        if t_type == "channel" and len(parts) >= 5:
          new_task["channel"] = parts[4].strip()

        tasks.append(new_task)
        user_state[user_id] = None
        bot.send_message(
            message.chat.id,
            f"✅ New task added successfully! (ID: {new_id}, Type: {t_type})",
            reply_markup=get_main_keyboard(user_id),
        )
      else:
        bot.send_message(
            message.chat.id,
            "❌ **Wrong format!**\n\n📌 **For App / Website (Screenshot"
            " proof):**\n`Title | Link | Reward | app`\n\n📌 **For Channel (Auto"
            " verify):**\n`Title | Link | Reward | channel | @channel_username`",
            parse_mode="Markdown",
        )
    except Exception as e:
      bot.send_message(message.chat.id, f"Error: {e}")
    return

  if user_state.get(user_id) == "WAITING_FOR_UPI":
    upi_info = text.strip()
    user_state[user_id] = None

    bal = users[user_id]["balance"]
    min_w = bot_settings["min_withdrawal_coins"]

    if bal < min_w:
      bot.send_message(
          message.chat.id,
          f"❌ **Withdrawal Failed!**\nYour balance is **{bal} Coins**, but the"
          f" minimum withdrawal limit is **{min_w} Coins**. Earn more coins to"
          " withdraw!",
          parse_mode="Markdown",
          reply_markup=get_main_keyboard(user_id),
      )
    else:
      users[user_id]["upi"] = upi_info
      withdrawals.append({
          "user_id": user_id,
          "upi": upi_info,
          "amount": bal,
          "status": "Pending",
      })
      users[user_id]["balance"] = 0
      bot.send_message(
          message.chat.id,
          "✅ Your withdrawal request has been sent to the admin!",
          reply_markup=get_main_keyboard(user_id),
      )
    return

  # --- सामान्य टेक्स्ट कमांड्स ---
  if text == "📞 Admin Support":
    bot.send_message(
        message.chat.id,
        f"💬 **Support & Help**\n\nFor any issues, payments, or questions,"
        f" contact our official admin:\n👉"
        f" [@{ADMIN_USERNAME}](https://t.me/{ADMIN_USERNAME})\n\n(Note: Please"
        f" mention your User ID in the message.)",
        parse_mode="Markdown",
    )
    return

  if text == "💰 Balance":
    bal = users[user_id]["balance"]
    rate = bot_settings["coins_per_rupee"]
    rupees = bal / rate
    bot.send_message(
        message.chat.id,
        f"💳 Your current balance:\n- Coins: **{bal}**\n- Value:"
        f" **₹{rupees:.2f}**",
        parse_mode="Markdown",
    )

  elif text == "👥 Referral Link":
    uname = bot.get_me().username
    link = f"https://t.me/{uname}?start={user_id}"
    ref_rew = bot_settings["referral_reward"]
    bot.send_message(
        message.chat.id,
        f"🔗 Your referral link:\n`{link}`\n\nShare and get **{ref_rew} coins**"
        " per referral!",
        parse_mode="Markdown",
    )

  elif text == "📋 Tasks":
    if not tasks:
      bot.send_message(message.chat.id, "No tasks available at the moment.")
      return

    markup = types.InlineKeyboardMarkup()
    user_completed = users[user_id].get("completed_tasks", [])

    available_found = False
    for t in tasks:
      if t["id"] not in user_completed:
        markup.add(
            types.InlineKeyboardButton(
                f"{t['title']} (+{t['reward']} Coins)",
                callback_data=f"task_{t['id']}",
            )
        )
        available_found = True

    if not available_found:
      bot.send_message(
          message.chat.id,
          "🎉 You have completed all available tasks! New tasks will appear"
          " here soon.",
      )
    else:
      bot.send_message(
          message.chat.id,
          "📋 **Available Tasks:**\nSelect a task below:",
          reply_markup=markup,
          parse_mode="Markdown",
      )

  elif text == "📤 Withdraw":
    min_w = bot_settings["min_withdrawal_coins"]
    rate = bot_settings["coins_per_rupee"]
    min_rs = min_w / rate
    bal = users[user_id]["balance"]

    if bal < min_w:
      bot.send_message(
          message.chat.id,
          f"❌ **Insufficient Balance!**\n- Your Balance: `{bal} Coins`\n- Min"
          f" Limit Required: `{min_w} Coins` (₹{min_rs})\n\nYou need"
          f" `{min_w - bal}` more coins to withdraw.",
          parse_mode="Markdown",
      )
      return

    bot.send_message(
        message.chat.id,
        f"📌 **Withdrawal Info:**\n- Min Limit: `{min_w} Coins` (₹{min_rs})\n-"
        f" Rate: `{rate} Coins = ₹1`\n\nPlease send your UPI ID or Paytm Number"
        " (e.g., `user@upi`):",
        parse_mode="Markdown",
    )
    user_state[user_id] = "WAITING_FOR_UPI"

  elif user_id == ADMIN_ID and text == "⚙️ Set Bot Settings":
    user_state[user_id] = "WAITING_FOR_SETTINGS"
    current_rate = bot_settings["coins_per_rupee"]
    current_min = bot_settings["min_withdrawal_coins"]
    current_ref = bot_settings["referral_reward"]
    bot.send_message(
        message.chat.id,
        f"⚙️ **Current Settings:**\n- Rate: `{current_rate} Coins ="
        f" ₹1`\n- Min Withdrawal: `{current_min} Coins`\n- Referral Reward:"
        f" `{current_ref} Coins`\n\nSend new settings in this exact"
        " format:\n`Coins_Per_Rupee | Min_Withdrawal_Coins |"
        " Referral_Reward`\nExample: `10 | 50 | 5`",
        parse_mode="Markdown",
    )

  elif user_id == ADMIN_ID and text == "➕ Add Task":
    user_state[user_id] = "WAITING_FOR_TASK"
    bot.send_message(
        message.chat.id,
        "➕ **Add New Task**\n\nSend details in format based on task"
        " type:\n\n1️⃣ **For App/Website (Screenshot proof):**\n`Title | Link |"
        " Reward | app`\n\n2️⃣ **For Channel (Auto join verify):**\n`Title | Link"
        " | Reward | channel | @channel_username`",
        parse_mode="Markdown",
    )

  elif user_id == ADMIN_ID and text == "📋 Manage Tasks":
    if not tasks:
      bot.send_message(message.chat.id, "No tasks exist.")
      return
    markup = types.InlineKeyboardMarkup()
    for t in tasks:
      markup.add(
          types.InlineKeyboardButton(
              f"❌ Delete: {t['title']} ({t['type']})",
              callback_data=f"del_task_{t['id']}",
          )
      )
    bot.send_message(
        message.chat.id,
        "Click the button below to remove the task:",
        reply_markup=markup,
    )

  elif user_id == ADMIN_ID and text == "💳 Payment Requests":
    pending_reqs = [w for w in withdrawals if w["status"] == "Pending"]
    if not pending_reqs:
      bot.send_message(message.chat.id, "There are no pending payment requests.")
      return

    rate = bot_settings["coins_per_rupee"]
    for i, req in enumerate(pending_reqs):
      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton(
              "✅ Pay / Approve", callback_data=f"pay_app_{req['user_id']}"
          )
      )
      rupees = req["amount"] / rate
      bot.send_message(
          message.chat.id,
          f"💳 **Payment Request #{i+1}**\n- User ID: `{req['user_id']}`\n- UPI:"
          f" `{req['upi']}`\n- Amount: `{req['amount']}` Coins"
          f" (**₹{rupees:.2f}**)",
          parse_mode="Markdown",
          reply_markup=markup,
      )

  elif user_id == ADMIN_ID and text == "📱 App Task Requests":
    pending_app_reqs = [
        sub for sub in app_submissions if sub["status"] == "Pending"
    ]
    if not pending_app_reqs:
      bot.send_message(message.chat.id, "There are no pending app task proofs.")
      return

    for i, sub in enumerate(pending_app_reqs):
      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton(
              "✅ Approve & Give Reward",
              callback_data=f"app_app_{sub['user_id']}_{sub['task_id']}",
          )
      )
      caption_msg = (
          f"📱 **App Task Proof #{i+1}**\n- User ID:"
          f" `{sub['user_id']}`\n- Task: {sub['task_title']}\n- Proof:"
          f" {sub['proof']}"
      )

      if sub.get("photo"):
        bot.send_photo(
            message.chat.id,
            photo=sub["photo"],
            caption=caption_msg,
            parse_mode="Markdown",
            reply_markup=markup,
        )
      else:
        bot.send_message(
            message.chat.id,
            caption_msg,
            parse_mode="Markdown",
            reply_markup=markup,
        )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
  global tasks
  user_id = call.from_user.id

  if call.data == "check_join":
    if check_subscription(user_id):
      bot.answer_callback_query(
          call.id, "✅ Thank you for joining both channels!"
      )
      if user_id not in users:
        users[user_id] = {
            "balance": 0,
            "ref_by": None,
            "completed_tasks": [],
            "upi": "",
        }
        ref_id = pending_refs.get(user_id)
        if ref_id and ref_id in users:
          users[user_id]["ref_by"] = ref_id
          ref_bonus = bot_settings["referral_reward"]
          users[ref_id]["balance"] += ref_bonus
          bot.send_message(
              ref_id, f"🎉 You got a new referral! +{ref_bonus} coins added."
          )
          pending_refs.pop(user_id, None)

      bot.send_message(
          call.message.chat.id,
          "🎉 Verification successful! Welcome to the bot:",
          reply_markup=get_main_keyboard(user_id),
      )
    else:
      bot.answer_callback_query(
          call.id,
          "❌ You have not joined both channels yet!",
          show_alert=True,
      )
    return

  if not check_subscription(user_id):
    bot.answer_callback_query(
        call.id, "Please join both channels first!", show_alert=True
    )
    return

  if call.data.startswith("task_") and not call.data.startswith("task_verify_"):
    task_id = int(call.data.split("_")[1])
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
      bot.answer_callback_query(call.id, "Task not found!")
      return

    if task_id in users[user_id]["completed_tasks"]:
      bot.answer_callback_query(
          call.id, "You have already completed this task!", show_alert=True
      )
      return

    if task.get("type") == "app":
      user_state[user_id] = f"WAITING_FOR_APP_PROOF_{task_id}"
      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton(
              "📥 Open Link / Visit Website", url=task["link"]
          )
      )
      bot.send_message(
          call.message.chat.id,
          f"📱 **{task['title']}**\n\n1. Click the button above to visit the"
          " link/app.\n2. Complete the task and send your **screenshot or"
          " registered proof** right here in the chat.",
          parse_mode="Markdown",
          reply_markup=markup,
      )
      bot.answer_callback_query(call.id)
    else:
      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton("🔗 Open Channel", url=task["link"])
      )
      markup.add(
          types.InlineKeyboardButton(
              "✅ Verify & Claim Reward", callback_data=f"task_verify_{task_id}"
          )
      )

      bot.send_message(
          call.message.chat.id,
          f"📌 **{task['title']}**\n\n1. Join this specific channel using the"
          " link.\n2. Click **'Verify & Claim Reward'** below.",
          parse_mode="Markdown",
          reply_markup=markup,
      )
      bot.answer_callback_query(call.id)
    return

  if call.data.startswith("task_verify_"):
    task_id = int(call.data.split("_")[2])
    task = next((t for t in tasks if t["id"] == task_id), None)

    if not task:
      bot.answer_callback_query(call.id, "Task not found!")
      return

    if task_id in users[user_id]["completed_tasks"]:
      bot.answer_callback_query(
          call.id, "You have already claimed this task!", show_alert=True
      )
      return

    try:
      member = bot.get_chat_member(task["channel"], user_id)
      valid_statuses = ["creator", "administrator", "member"]

      if member.status in valid_statuses:
        users[user_id]["balance"] += task["reward"]
        users[user_id]["completed_tasks"].append(task_id)
        bot.answer_callback_query(call.id, "Success! Reward added.")
        bot.send_message(
            call.message.chat.id,
            f"✅ **Task Verified Successfully!**\nYou received +{task['reward']}"
            " coins.",
            parse_mode="Markdown",
        )
      else:
        bot.answer_callback_query(
            call.id,
            "❌ You have not joined this task's channel yet!",
            show_alert=True,
        )
    except Exception as e:
      print(f"Task verification error: {e}")
      bot.answer_callback_query(
          call.id,
          "❌ Error verifying membership. Make sure bot is admin in that task"
          " channel!",
          show_alert=True,
      )
    return

  elif call.data.startswith("app_app_") and user_id == ADMIN_ID:
    parts = call.data.split("_")
    target_uid = int(parts[2])
    target_tid = int(parts[3])

    for sub in app_submissions:
      if (
          sub["user_id"] == target_uid
          and sub["task_id"] == target_tid
          and sub["status"] == "Pending"
      ):
        sub["status"] = "Approved"
        if target_uid in users:
          users[target_uid]["balance"] += sub["reward"]
          if target_tid not in users[target_uid]["completed_tasks"]:
            users[target_uid]["completed_tasks"].append(target_tid)

        bot.answer_callback_query(call.id, "App proof approved!")
        bot.send_message(
            call.message.chat.id,
            f"✅ App task proof for user `{target_uid}` approved and reward"
            " credited.",
            parse_mode="Markdown",
        )
        bot.send_message(
            target_uid,
            f"🎉 Your proof for **{sub['task_title']}** was approved by admin!"
            f" +{sub['reward']} coins added.",
            parse_mode="Markdown",
        )
        break

  elif call.data.startswith("del_task_") and user_id == ADMIN_ID:
    t_id = int(call.data.split("_")[2])
    tasks = [t for t in tasks if t["id"] != t_id]
    bot.answer_callback_query(call.id, "Task removed!")
    bot.send_message(call.message.chat.id, "✅ Task deleted successfully.")

  elif call.data.startswith("pay_app_") and user_id == ADMIN_ID:
    target_uid = int(call.data.split("_")[2])
    for req in withdrawals:
      if req["user_id"] == target_uid and req["status"] == "Pending":
        req["status"] = "Paid"
        bot.answer_callback_query(call.id, "Payment approved!")
        bot.send_message(
            call.message.chat.id,
            f"✅ Payment for user `{target_uid}` has been marked as Paid.",
            parse_mode="Markdown",
        )
        bot.send_message(
            target_uid,
            "🎉 Your payment request has been approved by the admin!",
        )
        break


# --- Render के लिए Flask सर्वर और बोट को एक साथ चलाना ---
app = Flask("")


@app.route("/")
def home():
  return "Bot is running and active!"


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
  # बैकग्राउंड में Flask सर्वर शुरू करें
  server_thread = Thread(target=run_flask)
  server_thread.start()

  print("Bot is starting with polling...")
  # टेलीग्राम बोट पोलिंग शुरू करें
  bot.infinity_polling()
