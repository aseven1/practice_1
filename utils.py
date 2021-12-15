import base64
import io
from typing import List
from typing import Optional
from typing import Union

from telegram import CallbackQuery
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler
from telegram.ext import MessageFilter

import rating
import reviews
import students


def send_message(update: Update, context: CallbackContext, text: str, photo: Optional[bytes] = None,
                 reply_markup: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]] = None) -> None:
    """Отправляет сообщение, фотографию и встроенную клавиатуру"""
    if photo:
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=text, reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)


def add_student(update: Update, context: CallbackContext) -> None:
    """Заносит информацию о пользователе в БД"""
    data = context.user_data['user']

    photo_stream = io.BytesIO()
    update.message.photo[-1].get_file().download(out=photo_stream)
    photo = base64.b64encode(photo_stream.getvalue())

    students.add_student(
        student_id=data['id'],
        name=data['name'],
        surname=data['surname'],
        u_group=data['u_group'],
        phone_number=data['phone_number'],
        photo=photo.decode()
    )
    del context.user_data['user']


def send_student_info(update: Update, context: CallbackContext, student: students.Student) -> None:
    """Отправляет карточку студента"""
    student_info = f"{student.name} {student.surname}\n{student.u_group}"
    student_photo = base64.b64decode(student.photo) if student.photo else None
    reply_markup = get_student_markup(student_id=student.id)
    send_message(update=update, context=context, text=student_info, photo=student_photo, reply_markup=reply_markup)


def get_student_markup(student_id: int) -> InlineKeyboardMarkup:
    """Генерирует встроенную клавиатуру для карточки студента"""
    student_rating = rating.get_student_rating(student_id)

    likes = sum([int(rate.likes) for rate in student_rating])
    dislikes = sum([int(rate.dislikes) for rate in student_rating])

    keyboard = [
        [
            InlineKeyboardButton(f"👍 {likes}", callback_data=f'rate {student_id} likes'),
            InlineKeyboardButton(f"👎 {dislikes}", callback_data=f'rate {student_id} dislikes'),
        ],
        [InlineKeyboardButton("Оставить отзыв", callback_data=f'review {student_id}')],
        [InlineKeyboardButton("Посмотреть отзывы", callback_data=f'get_reviews {student_id}')]
    ]
    return InlineKeyboardMarkup(keyboard)


def update_rating(update: Update, query: CallbackQuery, message: List[str], **_) -> None:
    """Изменяет рейтинг студента и обновляет его карточку"""
    student_id = int(message[1])
    rating.update_rating(student_id=student_id, from_id=update.effective_chat.id, rate=message[2] == "likes")
    reply_markup = get_student_markup(student_id=student_id)
    query.edit_message_reply_markup(reply_markup)


def request_review(update: Update, context: CallbackContext, message: List[str], **_) -> str:
    """Запрашивает отзыв о студенте"""
    context.user_data['student_id'] = message[1]
    keyboard = [[InlineKeyboardButton("Отмена", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    send_message(update=update, context=context, text="Напишите отзыв, который хотите оставить",
                 reply_markup=reply_markup)
    return 'SUBMIT'


def get_reviews(update: Update, context: CallbackContext, message: List[str], **_) -> None:
    """Отправляет все отзывы о студенте"""
    student_reviews = reviews.get_reviews(student_id=int(message[1]))
    if not student_reviews:
        send_message(update=update, context=context, text="Нет отзывов об этом студенте")
        return

    for review in student_reviews:
        reply_markup = get_review_markup(update=update, review=review)
        send_message(update=update, context=context, text=review.message, reply_markup=reply_markup)


def delete_review(query: CallbackQuery, message: List[str], **_) -> None:
    """Удаляет отзыв о студенте и сообщение"""
    reviews.delete_review(int(message[1]))
    query.delete_message()


def cancel_review(context: CallbackContext, query: CallbackQuery, **_) -> str:
    """Отменяет запрос и удаляет сообщение"""
    query.delete_message()
    del context.user_data['student_id']
    return ConversationHandler.END


def get_review_markup(update: Update, review: reviews.Review) -> Union[InlineKeyboardMarkup, None]:
    """Генерирует встроенную клавиатуру для отзыва о студенте"""
    reply_markup = None
    if update.effective_chat.id == review.from_id:
        keyboard = [[InlineKeyboardButton("Удалить", callback_data=f'delete {review.id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


class FilterNotAuthorized(MessageFilter):
    """Фильтр на проверку """
    def filter(self, message):
        return not students.get_student(message.chat_id)
