"""
Database Helper Module
Handles all database operations for the Student Attendance System
"""
import sqlite3
import os
from datetime import datetime

# Connect to the database
def connect():
    base_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_path, "school.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize tables
def init_database():
    conn = connect()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idno VARCHAR(10) UNIQUE NOT NULL,
            lastname VARCHAR(50) NOT NULL,
            firstname VARCHAR(50) NOT NULL,
            course VARCHAR(10) NOT NULL,
            level VARCHAR(3) NOT NULL,
            image_filename VARCHAR(255)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idno VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            time_in TIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idno) REFERENCES students(idno)
        )
    ''')

    conn.commit()
    conn.close()

# FUNCTIONS 

def getall(table):
    conn = connect()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    conn.close()
    return rows

def getone(table, **kwargs):
    conn = connect()
    cur = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"SELECT * FROM {table} WHERE {field}=?", (value,))
        return cur.fetchone()
    except Exception as e:
        print("ERROR:", e)
        return None
    finally:
        conn.close()

def addrecord(table, **kwargs):
    conn = connect()
    cur = conn.cursor()
    fields = ",".join(kwargs.keys())
    values = tuple(kwargs.values())
    placeholders = ",".join(["?"] * len(values))
    try:
        cur.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", values)
        conn.commit()
        return True
    except Exception as e:
        print("ERROR:", e)
        return False
    finally:
        conn.close()

def updaterecord(table, idfield, idvalue, **kwargs):
    conn = connect()
    cur = conn.cursor()
    set_clause = ",".join([f"{key}=?" for key in kwargs.keys()])
    values = tuple(kwargs.values()) + (idvalue,)
    try:
        cur.execute(f"UPDATE {table} SET {set_clause} WHERE {idfield}=?", values)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("ERROR:", e)
        return False
    finally:
        conn.close()

def deleterecord(table, **kwargs):
    conn = connect()
    cur = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"DELETE FROM {table} WHERE {field}=?", (value,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("ERROR:", e)
        return False
    finally:
        conn.close()

def recordexists(table, **kwargs):
    conn = connect()
    cur = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field}=?", (value,))
        return cur.fetchone()[0] > 0
    except:
        return False
    finally:
        conn.close()

def recordexists_exclude(table, field, value, exclude_field, exclude_value):
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {field}=? AND {exclude_field}!=?",
            (value, exclude_value)
        )
        return cur.fetchone()[0] > 0
    except:
        return False
    finally:
        conn.close()

# USER FUNCTIONS

def add_user(name, email, password):
    return addrecord('users', name=name, email=email, password=password)

def get_user_by_email(email):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cur.fetchone()
    conn.close()
    return user

def get_all_users():
    return getall('users')

def delete_user(user_id):
    return deleterecord('users', id=user_id)

def update_user_password(user_id, hashed_password):
    return updaterecord('users', 'id', user_id, password=hashed_password)

# STUDENT FUNCTIONS

def get_student_by_idno(idno):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE idno=?", (idno,))
    student = cur.fetchone()
    conn.close()
    return student

# ATTENDANCE FUNCTIONS

def record_attendance(idno):
    now = datetime.now()
    date = now.strftime('%Y-%m-%d')
    time_in = now.strftime('%H:%M:%S')
    return addrecord('attendance', idno=idno, date=date, time_in=time_in)

def get_all_attendance():
    conn = connect()
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            a.id,
            a.idno,
            COALESCE(s.lastname, 'N/A') as lastname,
            COALESCE(s.firstname, 'N/A') as firstname,
            COALESCE(s.course, 'N/A') as course,
            COALESCE(s.level, 'N/A') as level,
            a.date,
            a.time_in
        FROM attendance a
        LEFT JOIN students s ON a.idno = s.idno
        ORDER BY a.date DESC, a.time_in DESC
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_attendance_by_date(date):
    conn = connect()
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            a.id,
            a.idno,
            COALESCE(s.lastname, 'N/A') as lastname,
            COALESCE(s.firstname, 'N/A') as firstname,
            COALESCE(s.course, 'N/A') as course,
            COALESCE(s.level, 'N/A') as level,
            a.date,
            a.time_in
        FROM attendance a
        LEFT JOIN students s ON a.idno = s.idno
        WHERE DATE(a.date) = ?
        ORDER BY a.time_in ASC
    ''', (date,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_attendance_today(idno, date):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM attendance WHERE idno=? AND date=?",
        (idno, date)
    )
    record = cur.fetchone()
    conn.close()
    return record
