from telegram.ext import Application, MessageHandler, filters
from telegram.ext import CommandHandler
from telegram import ReplyKeyboardMarkup


async def start(update, context):
    user = update.effective_user
    reply_keyboard = [['/help', '/ask']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    await update.message.reply_html(
        f'Привет, {user.mention_html()}, это бот технической поддержки.',
        reply_markup=markup
    )
    print(update)


async def help(update, context):
    user = update.effective_user
    await update.message.reply_html(
        f'Чтобы задать вопрос, просто напишите его боту.',
    )


async def ask(update, context):
    user = update.effective_user
    ansers = [["Можно сгенерировать любой курс?", "Да"], ["А ваш сайт является фишинговым?", "Нет"],
              ["А можно ли создать несколько курсов?", "Можно"]]
    await update.message.reply_html(
        f'Часто задаваемы вопросы:',
    )
    s = ''
    for i in range(len(ansers)):
        s += ansers[i][0] + ': ' + ansers[i][1] + '\n'
    await update.message.reply_html(
        f'{s}',
    )



async def echo(update, context):
    ansers = open("q.txt", "w", encoding="utf-8")
    ansers.write(f'{update.message.chat.username}: {update.message.text}')
    await update.message.reply_text(f'Сообщение: "{update.message.text}", было передано технической поддержке и пока'
                                    f' обрабатывается')

def main():
    application = Application.builder().token('7609613212:AAEzrcOjI9RlcutVs_2fq7I-8nam28HYL38').build()

    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, echo)

    application.add_handler(text_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("ask", ask))
    application.run_polling()


main()
