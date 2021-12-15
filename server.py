# import os
import logging
from typing import Union

from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

import reviews
import students
import utils

API_TOKEN = '5096284148:AAEFqVpP_ZuponcDB_c_CShgGLYO6GdUut4'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

callbacks = {
    'rate': utils.update_rating,
    'review': utils.request_review,
    'get_reviews': utils.get_reviews,
    'delete': utils.delete_review,
    'cancel': utils.cancel_review
}

insturctions = 'Для поиска студентов введите Фамилию Имя Отчество (ФИО) и группу ИНКОД-19-1\n' \
               'Вам будет показан выбранный вами студент, которому вы можете оставить отзыв и поставить оценку'


def start(update: Update, context: CallbackContext) -> None:
    """Отправляет приветственное сообщение и помощь по боту"""
    utils.send_message(update=update, context=context, text=f"Инструкция:\n{insturctions}")


def not_authorized(update: Update, context: CallbackContext) -> str:
    """Запрашивает ФИО пользователя"""
    utils.send_message(update=update, context=context, text=f"Необходима авторизация, укажите Имя Фамилия Группа")
    return 'NAME'


def search(update: Update, context: CallbackContext) -> None:
    """Отпарвляет список студентов по критериям поиска"""
    values = update.message.text.split()
    found_students = students.get_students(values)
    if not found_students:
        utils.send_message(update=update, context=context, text=f"Студент не найден: {' '.join(values)}\n"
                                                                f"{insturctions}")
        return

    for student in found_students:
        utils.send_student_info(update=update, context=context, student=student)
    return


def unknown(update: Update, context: CallbackContext) -> None:
    """Обработчик неизвестных команд"""
    utils.send_message(update=update, context=context, text="Введена неизвестная команда")


def button_callback(update: Update, context: CallbackContext) -> Union[None, str]:
    """Обработчик запросов обратного вызова"""
    query = update.callback_query
    query.answer()
    message = query.data.split()
    return callbacks[message[0]](update=update, context=context, query=query, message=message)


def request_full_name(update: Update, context: CallbackContext) -> str:
    """Запрашивает номер телефона пользователя"""
    values = update.message.text.split()
    if len(values) != 3:
        utils.send_message(update=update, context=context, text="Введены неверные данные, укажите Имя Фамилия Группа")
        return 'NAME'

    context.user_data['user'] = {
        'id': update.effective_chat.id,
        'name': values[0],
        'surname': values[1],
        'u_group': values[2]
    }

    keyboard = [[KeyboardButton("Поделиться номером телефона", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    utils.send_message(update=update, context=context, text="Теперь укажите номер телефона", reply_markup=reply_markup)
    return 'PHONE'


def request_phone(update: Update, context: CallbackContext) -> str:
    """Запрашивает фото пользователя"""
    if update.message.text:
        utils.send_message(update=update, context=context,
                           text="Для того что бы поделиться номером телефона нажмите на соответсвующую кнопку")
        return 'PHONE'

    context.user_data['user']['phone_number'] = update.message.contact.phone_number
    utils.send_message(update=update, context=context, text="Хорошо, теперь отправьте фото для своего профиля")
    return 'PHOTO'


def request_photo_and_submit(update: Update, context: CallbackContext) -> Union[str, int]:
    """заносит информацию о пользователе в БД"""
    if update.message.text:
        utils.send_message(update=update, context=context,
                           text="Необходимо отправить фото для своего профиля")
        return 'PHOTO'

    utils.add_student(update=update, context=context)
    utils.send_message(update=update, context=context, text="Регистрация прошла успешно")
    utils.send_message(update=update, context=context, text=f"Инструкция:\n{insturctions}")
    return ConversationHandler.END


def submit_review(update: Update, context: CallbackContext) -> int:
    """Заносит отзыв о студенте в БД"""
    from_user = update.effective_chat
    reviews.add_review(student_id=context.user_data['student_id'], from_id=from_user.id,
                       message=f'{from_user.first_name} {from_user.last_name} @{from_user.username}\n'
                               f'{update.message.text}')
    del context.user_data['student_id']
    utils.send_message(update=update, context=context, text="Ваш отзыв был записан")
    return ConversationHandler.END


def main() -> None:
    """Основная функция запуска бота"""
    updater = Updater(token=API_TOKEN, use_context=True)

    dispatcher = updater.dispatcher

    # authorization callback
    authorization_conv = ConversationHandler(
        entry_points=[MessageHandler(utils.FilterNotAuthorized(), not_authorized)],
        states={
            'NAME': [MessageHandler(Filters.text & ~Filters.command, request_full_name)],
            'PHONE': [MessageHandler((Filters.text | Filters.contact) & ~Filters.command, request_phone)],
            'PHOTO': [MessageHandler((Filters.text | Filters.photo) & ~Filters.command, request_photo_and_submit)]
        },
        fallbacks=[CallbackQueryHandler(button_callback, pattern='^registered')]
    )

    # review callback
    review_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern='^review')],
        states={'SUBMIT': [MessageHandler(Filters.text & ~Filters.command, submit_review)]},
        fallbacks=[CallbackQueryHandler(button_callback, pattern='^cancel')]
    )

    # button callbacks
    dispatcher.add_handler(authorization_conv)
    dispatcher.add_handler(review_conv)
    dispatcher.add_handler(CallbackQueryHandler(button_callback, pattern='^(rate|get_reviews|delete)'))

    # commands
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, search))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
