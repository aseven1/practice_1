from typing import List
from typing import NamedTuple
from typing import Union

import db


class Student(NamedTuple):
    """Структура добавленного в БД студента"""
    id: int
    name: str
    surname: str
    u_group: str
    phone_number: str
    photo: Union[bytes, None]


def add_student(student_id: int, name: str, surname: str, u_group: str, phone_number: str, photo: str) -> None:
    cursor = db.get_cursor()
    cursor.execute("INSERT INTO student (id, name, surname, u_group, phone_number, photo) "
                   f"VALUES (?, ?, ?, ?, ?, ?)", (student_id, name, surname, u_group, phone_number, photo))
    db.conn.commit()


def get_students(args: List[str]) -> List[Student]:
    """Возвращает из БД список найденых студентов по критериям поиска"""
    query = _parse_query_values(args)
    cursor = db.get_cursor()
    cursor.execute(f"SELECT * FROM student WHERE {query}")
    rows = cursor.fetchall()
    students = [
        Student(
            id=row[0],
            name=row[1],
            surname=row[2],
            u_group=row[3],
            phone_number=row[4],
            photo=row[5]
        ) for row in rows]
    return students


def get_student(student_id: int) -> Union[Student, None]:
    """Возвращает студента по id из БД"""
    cursor = db.get_cursor()
    cursor.execute(f"SELECT * FROM student WHERE id = {student_id}")
    result = cursor.fetchone()
    if not result:
        return
    student = Student(
        id=result[0],
        name=result[1],
        surname=result[2],
        u_group=result[3],
        phone_number=result[4],
        photo=result[5]
    )
    return student


def _parse_query_values(args: List[str]) -> str:
    """Парсит аргументы пришедшего сообщения в текст запроса к БД"""
    query = [f"'{arg}' IN (name, surname, u_group)" for arg in args]
    return ' OR '.join(query)
