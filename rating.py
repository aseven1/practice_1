from typing import List
from typing import NamedTuple
from typing import Optional

import db


class Rate(NamedTuple):
    """Структура добавленного в БД отзыва"""
    from_id: int
    student_id: int
    likes: int
    dislikes: int


def update_rating(student_id: int, from_id: int, rate: bool) -> None:
    """Ставит Лайк или Дизлайк в зависимости от параметра rate"""
    cursor = db.get_cursor()
    likes, dislikes = (int(rate), int(not rate))
    cursor.execute("INSERT INTO rating (from_id, student_id, likes, dislikes) "
                   f"VALUES ({from_id}, {student_id}, {likes}, {dislikes}) "
                   "ON CONFLICT (from_id) DO "
                   f"UPDATE SET likes = {likes}, dislikes = {dislikes}")
    db.conn.commit()


def get_student_rating(student_id: int) -> List[Rate]:
    """Возвращает список оценок из БД"""
    cursor = db.get_cursor()
    cursor.execute(f"SELECT * FROM rating WHERE student_id = {student_id}")
    rows = cursor.fetchall()
    rates = [
        Rate(
            from_id=row[0],
            student_id=row[1],
            likes=row[2],
            dislikes=row[3]
        ) for row in rows]
    return rates
