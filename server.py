import telebot
import telekit

import handlers # Package with all your handlers

from database import database

TOKEN = database.Settings.token()
bot = telebot.TeleBot(TOKEN)

telekit.Server(bot).polling()