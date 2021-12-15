from typing import List
from typing import NamedTuple
from typing import Optional

import db


class Review(NamedTuple):
    """Структура добавленного в БД отзыва"""
    id: Optional[int]
    from_id: int
    student_id: int
    message: str


def add_review(student_id: int, from_id: int, message: str) -> None:
    """Заносит отзыв о студенте в БД"""
    cursor = db.get_cursor()
    cursor.execute("INSERT INTO review (from_id, student_id, message) "
                   f"VALUES ({from_id}, {student_id}, '{message}') ")
    db.conn.commit()


def get_reviews(student_id: int) -> List[Review]:
    """Возвращает список отзывов из БД"""
    cursor = db.get_cursor()
    cursor.execute(f"SELECT * FROM review WHERE student_id = {student_id}")
    rows = cursor.fetchall()
    reviews = [
        Review(
            id=row[0],
            from_id=row[1],
            student_id=row[2],
            message=row[3]
        ) for row in rows]
    return reviews


def delete_review(review_id: int):
    """Удаляет отзыв из БД"""
    cursor = db.get_cursor()
    cursor.execute(f"DELETE from review where id={review_id}")
    db.conn.commit()
