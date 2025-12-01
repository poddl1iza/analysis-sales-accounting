import sys
import math
import sqlite3
import random
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem, QDateEdit, QDoubleSpinBox, QDialog, QHeaderView, QFormLayout, QGroupBox, QComboBox, QProgressBar,QSpinBox, QTextEdit)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QPainter, QLinearGradient, QColor, QPen, QRadialGradient, QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

try:
    import openpyxl # проверка наличия openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("Предупреждение: openpyxl не установлен. Экспорт в Excel будет недоступен.")

class DatabaseManager:
    def __init__(self, db_name="sales_system.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'employee',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    phone TEXT,
                    branch_id INTEGER,
                    FOREIGN KEY (branch_id) REFERENCES branches (id) ON DELETE SET NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    revenue REAL NOT NULL,
                    transactions INTEGER NOT NULL,
                    average_check REAL,
                    employee_id INTEGER,
                    branch_id INTEGER,
                    notes TEXT,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE SET NULL,
                    FOREIGN KEY (branch_id) REFERENCES branches (id) ON DELETE SET NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS branches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    manager TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch_id INTEGER,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    daily_plan REAL NOT NULL,
                    monthly_plan REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (branch_id) REFERENCES branches (id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                INSERT OR IGNORE INTO users (full_name, email, password, role)
                VALUES (?, ?, ?, ?)
            ''', ('Администратор', 'admin@system.com', 'admin123', 'admin'))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка инициализации БД: {e}")

    def create_user(self, full_name, email, password, role='employee'):
        try:
            if self.user_exists(email):
                return False, "Пользователь с таким email уже существует"
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (full_name, email, password, role)
                VALUES (?, ?, ?, ?)
            ''', (full_name, email, password, role))
            conn.commit()
            conn.close()
            return True, "Пользователь успешно создан"
        except sqlite3.IntegrityError:
            return False, "Пользователь с таким email уже существует"
        except Exception as e:
            return False, f"Ошибка при создании пользователя: {str(e)}"

    def authenticate_user(self, email, password):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, full_name, email, role FROM users 
                WHERE email = ? AND password = ?
            ''', (email, password))
            user = cursor.fetchone()
            conn.close()
            return user
        except Exception as e:
            print(f"Ошибка при аутентификации: {e}")
            return None

    def user_exists(self, email):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            conn.close()
            return user is not None
        except Exception as e:
            print(f"Ошибка при проверке пользователя: {e}")
            return False

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def execute_query(self, query, params=()):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            result = cursor.fetchall()
            conn.close()
            return result
        except Exception as e:
            print(f"Ошибка выполнения запроса: {str(e)}")
            return None

    def delete_sale(self, sale_id):
        return self.execute_query("DELETE FROM sales WHERE id = ?", (sale_id,))

    def delete_employee(self, employee_id):
        return self.execute_query("DELETE FROM employees WHERE id = ?", (employee_id,))

    def get_all_sales(self):
        query = '''
            SELECT s.id, s.date, s.revenue, s.transactions, s.average_check, 
                   COALESCE(e.name, 'Не указан') as employee_name, 
                   COALESCE(b.name, 'Не указан') as branch_name, s.notes,
                   u.full_name as user_name
            FROM sales s 
            LEFT JOIN employees e ON s.employee_id = e.id 
            LEFT JOIN branches b ON s.branch_id = b.id
            LEFT JOIN users u ON s.user_id = u.id
            ORDER BY s.date DESC
        '''
        return self.execute_query(query)

    def get_all_employees(self):
        return self.execute_query("SELECT * FROM employees ORDER BY name")

    def add_sale(self, date, revenue, transactions, average_check, employee_id, branch_id, notes, user_id):
        query = '''
            INSERT INTO sales (date, revenue, transactions, average_check, employee_id, branch_id, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return self.execute_query(query,
                                  (date, revenue, transactions, average_check, employee_id, branch_id, notes, user_id))

    def update_sale(self, sale_id, date, revenue, transactions, average_check, employee_id, branch_id, notes, user_id):
        query = '''
            UPDATE sales SET date=?, revenue=?, transactions=?, average_check=?, employee_id=?, branch_id=?, notes=?, user_id=?
            WHERE id=?
        '''
        return self.execute_query(query,
                                  (date, revenue, transactions, average_check, employee_id, branch_id, notes, user_id,
                                   sale_id))

    def add_employee(self, name, position, phone, branch_id=None):
        query = "INSERT INTO employees (name, position, phone, branch_id) VALUES (?, ?, ?, ?)"
        return self.execute_query(query, (name, position, phone, branch_id))

    def update_employee(self, employee_id, name, position, phone, branch_id=None):
        query = "UPDATE employees SET name=?, position=?, phone=?, branch_id=? WHERE id=?"
        return self.execute_query(query, (name, position, phone, branch_id, employee_id))

    def get_all_branches(self):
        return self.execute_query("SELECT * FROM branches ORDER BY name")

    def add_branch(self, name, address, manager, phone):
        query = "INSERT INTO branches (name, address, manager, phone) VALUES (?, ?, ?, ?)"
        return self.execute_query(query, (name, address, manager, phone))

    def update_branch(self, branch_id, name, address, manager, phone):
        query = "UPDATE branches SET name=?, address=?, manager=?, phone=? WHERE id=?"
        return self.execute_query(query, (name, address, manager, phone, branch_id))

    def delete_branch(self, branch_id):
        return self.execute_query("DELETE FROM branches WHERE id = ?", (branch_id,))

    def get_sales_plans(self, branch_id=None):
        if branch_id:
            query = '''
                SELECT sp.*, b.name as branch_name 
                FROM sales_plans sp 
                LEFT JOIN branches b ON sp.branch_id = b.id 
                WHERE sp.branch_id = ? 
                ORDER BY sp.year DESC, sp.month DESC
            '''
            return self.execute_query(query, (branch_id,))
        else:
            query = '''
                SELECT sp.*, b.name as branch_name 
                FROM sales_plans sp 
                LEFT JOIN branches b ON sp.branch_id = b.id 
                ORDER BY sp.year DESC, sp.month DESC
            '''
            return self.execute_query(query)

    def add_sales_plan(self, branch_id, year, month, daily_plan, monthly_plan):
        query = '''
            INSERT INTO sales_plans (branch_id, year, month, daily_plan, monthly_plan)
            VALUES (?, ?, ?, ?, ?)
        '''
        return self.execute_query(query, (branch_id, year, month, daily_plan, monthly_plan))

    def update_sales_plan(self, plan_id, daily_plan, monthly_plan):
        query = "UPDATE sales_plans SET daily_plan=?, monthly_plan=? WHERE id=?"
        return self.execute_query(query, (daily_plan, monthly_plan, plan_id))

    def delete_sales_plan(self, plan_id):
        return self.execute_query("DELETE FROM sales_plans WHERE id = ?", (plan_id,))

class AnimatedGradientWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.animation_phase = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(50)

    def update_animation(self):
        self.animation_phase += 0.1
        self.update()  # вызов перерисовки (paintEvent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#f8f9fa"))
        gradient.setColorAt(1, QColor("#e9ecef"))
        painter.fillRect(self.rect(), gradient)

        self.draw_animated_waves(painter)

    def draw_animated_waves(self, painter):
        width, height = self.width(), self.height()

        painter.setPen(QPen(QColor(73, 80, 87, 60), 2))
        points = []
        for x in range(0, width + 10, 8):
            y = height * 0.7 + height * 0.08 * math.sin(x * 0.01 + self.animation_phase)
            points.append((x, y))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        painter.setPen(QPen(QColor(108, 117, 125, 40), 1.5))
        points2 = []
        for x in range(0, width + 10, 8):
            y = height * 0.6 + height * 0.06 * math.cos(x * 0.015 + self.animation_phase * 0.8)
            points2.append((x, y))

        for i in range(len(points2) - 1):
            painter.drawLine(points2[i][0], points2[i][1], points2[i + 1][0], points2[i + 1][1])

class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome - Добро пожаловать")
        self.resize(1000, 700)
        self.setMinimumSize(900, 600)
        self.setFont(QFont("Courier New", 10))
        self.init_ui()
        self.start_loading()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 40)

        title_label = QLabel("Добро пожаловать!")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { color: #495057; font-size: 36px; font-weight: bold; margin-bottom: 10px; }")

        subtitle_label = QLabel("Система анализа и учёта продаж")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("QLabel { color: #6c757d; font-size: 16px; margin-bottom: 30px; }")

        info_frame = QFrame()
        info_frame.setStyleSheet(
            "QFrame { background: white; border-radius: 10px; border: 1px solid #dee2e6; padding: 20px; }")
        info_frame.setMaximumWidth(600)

        info_layout = QVBoxLayout()
        features = ["⎷ Анализ продаж", "⎷ Отчётность и статистика", "⎷ Графики выполнения планов"]
        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setStyleSheet("QLabel { color: #495057; font-size: 16px; padding: 8px; }")
            info_layout.addWidget(feature_label)
        info_frame.setLayout(info_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #adb5bd; border-radius: 5px; background: white; height: 20px; }
            QProgressBar::chunk { background: #495057; border-radius: 4px; }
        """)

        self.status_label = QLabel("Загрузка...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #6c757d; font-size: 14px;")

        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addWidget(info_frame, alignment=Qt.AlignCenter)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)

        background = AnimatedGradientWidget()
        background_layout = QVBoxLayout()
        background_layout.addLayout(main_layout)
        background.setLayout(background_layout)

        window_layout = QVBoxLayout()
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(background)
        self.setLayout(window_layout)

    def start_loading(self):
        self.loading_steps = [
            "Инициализация базы данных...",
            "Загрузка модулей аналитики...",
            "Настройка интерфейса...",
            "Проверка лицензии...",
            "Готово!"
        ]
        self.current_step = 0
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading)
        self.loading_timer.start(800)

    def update_loading(self):
        if self.current_step < len(self.loading_steps):
            progress = (self.current_step + 1) * 20
            self.progress_bar.setValue(progress)
            self.status_label.setText(self.loading_steps[self.current_step])
            self.current_step += 1
        else:
            self.loading_timer.stop()
            self.progress_bar.setValue(100)
            self.status_label.setText("Приложение готово к работе!")
            QTimer.singleShot(500, self.open_login_window)

    def open_login_window(self):
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()


class GradientWidget(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#f8f9fa"))
        gradient.setColorAt(1, QColor("#e9ecef"))
        painter.fillRect(self.rect(), gradient)
        self.draw_decoration_graphs(painter)

    def draw_decoration_graphs(self, painter):
        painter.setPen(QPen(QColor(173, 181, 189, 80), 2))
        amplitude = self.height() * 0.1
        frequency = 0.008
        vertical_offset = self.height() * 0.6
        points = []
        for x in range(0, self.width() + 5, 5):
            y = vertical_offset + amplitude * math.sin(frequency * x)
            points.append((x, y))
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])


class BranchManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle("Управление филиалами")
        self.resize(1200, 800)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.branches_table = QTableWidget()
        self.branches_table.setColumnCount(5)
        self.branches_table.setHorizontalHeaderLabels(["№", "Название", "Адрес", "Менеджер", "Телефон"])
        self.branches_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.branches_table)

        form_group = QGroupBox("Добавить/Редактировать филиал")
        form_layout = QFormLayout()

        self.branch_name_input = QLineEdit()
        self.branch_address_input = QTextEdit()
        self.branch_address_input.setMaximumHeight(80)
        self.branch_manager_input = QLineEdit()
        self.branch_phone_input = QLineEdit()

        # Установка масок ввода
        phone_validator = QRegularExpressionValidator(QRegularExpression(r'^[\d\+\(\)\-\s]{0,20}$'))
        self.branch_phone_input.setValidator(phone_validator)
        self.branch_phone_input.setPlaceholderText("+7(XXX)XXX-XX-XX")

        name_validator = QRegularExpressionValidator(QRegularExpression(r'^[A-Za-zА-Яа-я\s\-]{0,50}$'))
        self.branch_manager_input.setValidator(name_validator)

        form_layout.addRow("Название филиала:", self.branch_name_input)
        form_layout.addRow("Адрес:", self.branch_address_input)
        form_layout.addRow("Менеджер:", self.branch_manager_input)
        form_layout.addRow("Телефон:", self.branch_phone_input)

        button_layout = QHBoxLayout()
        self.add_branch_btn = QPushButton("Добавить")
        self.update_branch_btn = QPushButton("Заменить")
        self.delete_branch_btn = QPushButton("Удалить")
        self.clear_branch_btn = QPushButton("Очистить")

        button_layout.addWidget(self.add_branch_btn)
        button_layout.addWidget(self.update_branch_btn)
        button_layout.addWidget(self.delete_branch_btn)
        button_layout.addWidget(self.clear_branch_btn)
        form_layout.addRow(button_layout)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        self.add_branch_btn.clicked.connect(self.add_branch)
        self.update_branch_btn.clicked.connect(self.update_branch)
        self.delete_branch_btn.clicked.connect(self.delete_branch)
        self.clear_branch_btn.clicked.connect(self.clear_branch_form)
        self.branches_table.itemSelectionChanged.connect(self.load_branch_data)

        self.setLayout(layout)
        self.load_branches()

    def load_branches(self):
        branches = self.db.get_all_branches()
        if branches is not None:
            self.branches_table.setRowCount(len(branches))
            for row, branch in enumerate(branches):
                self.branches_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.branches_table.setItem(row, 1, QTableWidgetItem(str(branch[1]) if branch[1] else ""))
                self.branches_table.setItem(row, 2, QTableWidgetItem(str(branch[2]) if branch[2] else ""))
                self.branches_table.setItem(row, 3, QTableWidgetItem(str(branch[3]) if branch[3] else ""))
                self.branches_table.setItem(row, 4, QTableWidgetItem(str(branch[4]) if branch[4] else ""))

    def add_branch(self):
        name = self.branch_name_input.text().strip()
        address = self.branch_address_input.toPlainText().strip()
        manager = self.branch_manager_input.text().strip()
        phone = self.branch_phone_input.text().strip()

        if not name or not address:
            QMessageBox.warning(self, "Ошибка", "Заполните название и адрес филиала")
            return

        result = self.db.add_branch(name, address, manager, phone)
        if result is not None:
            self.load_branches()
            self.clear_branch_form()
            QMessageBox.information(self, "Успех", "Филиал добавлен")

    def update_branch(self):
        selected_row = self.branches_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите филиал для редактирования")
            return

        branches = self.db.get_all_branches()
        if not branches or selected_row >= len(branches):
            return

        branch_id = branches[selected_row][0]
        name = self.branch_name_input.text().strip()
        address = self.branch_address_input.toPlainText().strip()
        manager = self.branch_manager_input.text().strip()
        phone = self.branch_phone_input.text().strip()

        result = self.db.update_branch(branch_id, name, address, manager, phone)
        if result is not None:
            self.load_branches()
            QMessageBox.information(self, "Успех", "Данные филиала обновлены")

    def delete_branch(self):
        selected_row = self.branches_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите филиал для удаления")
            return

        branches = self.db.get_all_branches()
        if not branches or selected_row >= len(branches):
            return

        branch_id = branches[selected_row][0]
        reply = QMessageBox.question(self, "Подтверждение", "Вы уверены, что хотите удалить этот филиал?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            result = self.db.delete_branch(branch_id)
            if result is not None:
                self.load_branches()
                self.clear_branch_form()
                QMessageBox.information(self, "Успех", "Филиал удален")

    def load_branch_data(self):
        selected_row = self.branches_table.currentRow()
        if selected_row >= 0:
            branches = self.db.get_all_branches()
            if branches and selected_row < len(branches):
                branch = branches[selected_row]
                self.branch_name_input.setText(branch[1] if branch[1] else "")
                self.branch_address_input.setPlainText(branch[2] if branch[2] else "")
                self.branch_manager_input.setText(branch[3] if branch[3] else "")
                self.branch_phone_input.setText(branch[4] if branch[4] else "")

    def clear_branch_form(self):
        self.branch_name_input.clear()
        self.branch_address_input.clear()
        self.branch_manager_input.clear()
        self.branch_phone_input.clear()
        self.branches_table.clearSelection()


class EmployeeManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle("Управление сотрудниками магазина")
        self.resize(1200, 800)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.employee_table = QTableWidget()
        self.employee_table.setColumnCount(5)
        self.employee_table.setHorizontalHeaderLabels(["№", "ФИО", "Должность", "Телефон", "Филиал"])
        self.employee_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.employee_table)

        form_group = QGroupBox("Добавить/Редактировать сотрудника")
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.position_input = QComboBox()
        self.position_input.addItems(["Кассир", "Старший кассир", "Администратор магазина"])
        self.phone_input = QLineEdit()
        self.employee_branch_combo = QComboBox()

        # Установка масок ввода для телефона
        phone_validator = QRegularExpressionValidator(QRegularExpression(r'^[\d\+\(\)\-\s]{0,20}$'))
        self.phone_input.setValidator(phone_validator)
        self.phone_input.setPlaceholderText("+7(XXX)XXX-XX-XX")

        # Валидатор для имени (только буквы, пробелы и дефисы)
        name_validator = QRegularExpressionValidator(QRegularExpression(r'^[A-Za-zА-Яа-я\s\-]{0,50}$'))
        self.name_input.setValidator(name_validator)

        form_layout.addRow("ФИО:", self.name_input)
        form_layout.addRow("Должность:", self.position_input)
        form_layout.addRow("Телефон:", self.phone_input)
        form_layout.addRow("Филиал:", self.employee_branch_combo)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить")
        self.update_button = QPushButton("Заменить")
        self.delete_button = QPushButton("Удалить")
        self.clear_button = QPushButton("Очистить")

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.clear_button)
        form_layout.addRow(button_layout)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        self.add_button.clicked.connect(self.add_employee)
        self.update_button.clicked.connect(self.update_employee)
        self.delete_button.clicked.connect(self.delete_employee)
        self.clear_button.clicked.connect(self.clear_form)
        self.employee_table.itemSelectionChanged.connect(self.load_employee_data)

        self.setLayout(layout)
        self.load_branches_combo()
        self.load_employees()

    def load_branches_combo(self):
        branches = self.db.get_all_branches()
        self.employee_branch_combo.clear()
        self.employee_branch_combo.addItem("Не указан", 0)
        if branches:
            for branch in branches:
                branch_id = branch[0]
                branch_name = branch[1]
                self.employee_branch_combo.addItem(branch_name, branch_id)

    def load_employees(self):
        try:
            employees = self.db.get_all_employees()
            if employees is not None:
                self.employee_table.setRowCount(len(employees))
                for row, employee in enumerate(employees):
                    self.employee_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                    self.employee_table.setItem(row, 1, QTableWidgetItem(str(employee[1]) if employee[1] else ""))
                    self.employee_table.setItem(row, 2, QTableWidgetItem(str(employee[2]) if employee[2] else ""))
                    self.employee_table.setItem(row, 3, QTableWidgetItem(str(employee[3]) if employee[3] else ""))
                    branch_id = employee[4] if len(employee) > 4 else None
                    branch_name = "Не указан"
                    if branch_id:
                        branches = self.db.get_all_branches()
                        for branch in branches:
                            if branch[0] == branch_id:
                                branch_name = branch[1]
                                break
                    self.employee_table.setItem(row, 4, QTableWidgetItem(branch_name))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки сотрудников: {str(e)}")

    def get_selected_employee_id(self):
        selected = self.employee_table.currentRow()
        if selected >= 0:
            employees = self.db.get_all_employees()
            if employees and selected < len(employees):
                return employees[selected][0]
        return None

    def add_employee(self):
        name = self.name_input.text().strip()
        position = self.position_input.currentText()
        phone = self.phone_input.text().strip()
        branch_id = self.employee_branch_combo.currentData()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО сотрудника")
            return

        try:
            result = self.db.add_employee(name, position, phone, branch_id if branch_id != 0 else None)
            if result is not None:
                self.load_employees()
                self.clear_form()
                QMessageBox.information(self, "Успех", "Сотрудник добавлен")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка добавления: {str(e)}")

    def update_employee(self):
        employee_id = self.get_selected_employee_id()
        if not employee_id:
            QMessageBox.warning(self, "Ошибка", "Выберите сотрудника для редактирования")
            return

        name = self.name_input.text().strip()
        position = self.position_input.currentText()
        phone = self.phone_input.text().strip()
        branch_id = self.employee_branch_combo.currentData()

        try:
            result = self.db.update_employee(employee_id, name, position, phone, branch_id if branch_id != 0 else None)
            if result is not None:
                self.load_employees()
                QMessageBox.information(self, "Успех", "Данные обновлены")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка обновления: {str(e)}")

    def delete_employee(self):
        employee_id = self.get_selected_employee_id()
        if not employee_id:
            QMessageBox.warning(self, "Ошибка", "Выберите сотрудника для удаления")
            return

        reply = QMessageBox.question(self, "Подтверждение", "Вы уверены, что хотите удалить этого сотрудника?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                result = self.db.delete_employee(employee_id)
                if result is not None:
                    self.load_employees()
                    self.clear_form()
                    QMessageBox.information(self, "Успех", "Сотрудник удален")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка удаления: {str(e)}")

    def load_employee_data(self):
        employee_id = self.get_selected_employee_id()
        if employee_id:
            employees = self.db.get_all_employees()
            if employees:
                for emp in employees:
                    if emp[0] == employee_id:
                        self.name_input.setText(emp[1] if emp[1] else "")
                        self.position_input.setCurrentText(emp[2] if emp[2] else "Кассир")
                        self.phone_input.setText(emp[3] if emp[3] else "")
                        branch_id = emp[4] if len(emp) > 4 else None
                        if branch_id:
                            branch_index = self.employee_branch_combo.findData(branch_id)
                            if branch_index >= 0:
                                self.employee_branch_combo.setCurrentIndex(branch_index)
                        else:
                            self.employee_branch_combo.setCurrentIndex(0)
                        break

    def clear_form(self):
        self.name_input.clear()
        self.position_input.setCurrentIndex(0)
        self.phone_input.clear()
        self.employee_branch_combo.setCurrentIndex(0)
        self.employee_table.clearSelection()


class SalesPlansDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle("Планы продаж")
        self.resize(1250, 750)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.plans_table = QTableWidget()
        self.plans_table.setColumnCount(6)
        self.plans_table.setHorizontalHeaderLabels(["№", "Филиал", "Год", "Месяц", "Ежедневный план", "Месячный план"])
        self.plans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.plans_table)

        form_group = QGroupBox("Добавить/Редактировать план продаж")
        form_layout = QFormLayout()

        self.plan_branch_combo = QComboBox()
        self.plan_year_input = QSpinBox()
        self.plan_year_input.setRange(2020, 2030)
        self.plan_year_input.setValue(datetime.now().year)
        self.plan_month_combo = QComboBox()
        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь",
                  "Ноябрь", "Декабрь"]
        self.plan_month_combo.addItems(months)
        self.plan_month_combo.setCurrentIndex(datetime.now().month - 1)
        self.daily_plan_input = QDoubleSpinBox()
        self.daily_plan_input.setRange(0, 1000000)
        self.daily_plan_input.setPrefix("₽ ")
        self.daily_plan_input.setDecimals(2)
        self.monthly_plan_input = QDoubleSpinBox()
        self.monthly_plan_input.setRange(0, 10000000)
        self.monthly_plan_input.setPrefix("₽ ")
        self.monthly_plan_input.setDecimals(2)

        # Установка валидаторов для полей ввода
        self.setup_validators()

        form_layout.addRow("Филиал:", self.plan_branch_combo)
        form_layout.addRow("Год:", self.plan_year_input)
        form_layout.addRow("Месяц:", self.plan_month_combo)
        form_layout.addRow("Ежедневный план:", self.daily_plan_input)
        form_layout.addRow("Месячный план:", self.monthly_plan_input)

        button_layout = QHBoxLayout()
        self.add_plan_btn = QPushButton("Добавить")
        self.update_plan_btn = QPushButton("Заменить")
        self.delete_plan_btn = QPushButton("Удалить")
        self.clear_plan_btn = QPushButton("Очистить")

        button_layout.addWidget(self.add_plan_btn)
        button_layout.addWidget(self.update_plan_btn)
        button_layout.addWidget(self.delete_plan_btn)
        button_layout.addWidget(self.clear_plan_btn)
        form_layout.addRow(button_layout)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        self.add_plan_btn.clicked.connect(self.add_sales_plan)
        self.update_plan_btn.clicked.connect(self.update_sales_plan)
        self.delete_plan_btn.clicked.connect(self.delete_sales_plan)
        self.clear_plan_btn.clicked.connect(self.clear_plan_form)
        self.plans_table.itemSelectionChanged.connect(self.load_plan_data)

        self.setLayout(layout)
        self.load_branches_combo()
        self.load_sales_plans()

    def setup_validators(self):
        """Установка валидаторов для полей ввода"""
        # валидатор для ежедневного плана
        daily_validator = QRegularExpressionValidator(QRegularExpression(r'^\d*\.?\d*$'))
        self.daily_plan_input.lineEdit().setValidator(daily_validator)

        # валидатор для месячного плана (только цифры и точка)
        monthly_validator = QRegularExpressionValidator(QRegularExpression(r'^\d*\.?\d*$'))
        self.monthly_plan_input.lineEdit().setValidator(monthly_validator)

        # Установка минимальных значений
        self.daily_plan_input.setMinimum(0.00)
        self.monthly_plan_input.setMinimum(0.00)

    def validate_form(self):
        """Проверка заполнения всех полей формы"""
        if self.plan_branch_combo.currentIndex() == -1 or self.plan_branch_combo.currentText() == "":
            QMessageBox.warning(self, "Ошибка", "Выберите филиал")
            return False

        if self.plan_year_input.value() == 0:
            QMessageBox.warning(self, "Ошибка", "Укажите год")
            return False

        if self.plan_month_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите месяц")
            return False

        if self.daily_plan_input.value() <= 0:
            QMessageBox.warning(self, "Ошибка", "Введите корректное значение ежедневного плана")
            return False

        if self.monthly_plan_input.value() <= 0:
            QMessageBox.warning(self, "Ошибка", "Введите корректное значение месячного плана")
            return False

        return True

    def load_branches_combo(self):
        branches = self.db.get_all_branches()
        self.plan_branch_combo.clear()
        if branches:
            for branch in branches:
                branch_id = branch[0]
                branch_name = branch[1]
                self.plan_branch_combo.addItem(branch_name, branch_id)

    def load_sales_plans(self):
        plans = self.db.get_sales_plans()
        if plans is not None:
            self.plans_table.setRowCount(len(plans))
            for row, plan in enumerate(plans):
                self.plans_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.plans_table.setItem(row, 1, QTableWidgetItem(plan[7] if plan[7] else "Все филиалы"))
                self.plans_table.setItem(row, 2, QTableWidgetItem(str(plan[2])))
                self.plans_table.setItem(row, 3, QTableWidgetItem(str(plan[3])))
                self.plans_table.setItem(row, 4, QTableWidgetItem(f"{plan[4]:.2f} ₽"))
                self.plans_table.setItem(row, 5, QTableWidgetItem(f"{plan[5]:.2f} ₽"))

    def add_sales_plan(self):
        # проверка заполнения всех полей
        if not self.validate_form():
            return

        branch_id = self.plan_branch_combo.currentData()
        year = self.plan_year_input.value()
        month = self.plan_month_combo.currentIndex() + 1
        daily_plan = self.daily_plan_input.value()
        monthly_plan = self.monthly_plan_input.value()

        # доп. проверка значений
        if daily_plan <= 0 or monthly_plan <= 0:
            QMessageBox.warning(self, "Ошибка", "Введите корректные значения планов")
            return

        # проверка логической согласованности планов
        if monthly_plan < daily_plan * 30:
            reply = QMessageBox.question(self, "Предупреждение",
                                         f"Месячный план ({monthly_plan:,.2f} ₽) меньше чем ежедневный план × 30 дней ({daily_plan * 30:,.2f} ₽).\nПродолжить?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        result = self.db.add_sales_plan(branch_id, year, month, daily_plan, monthly_plan)
        if result is not None:
            self.load_sales_plans()
            self.clear_plan_form()
            QMessageBox.information(self, "Успех", "План продаж добавлен")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить план продаж")

    def update_sales_plan(self):
        selected_row = self.plans_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите план для редактирования")
            return

        # проверка заполнения всех полей
        if not self.validate_form():
            return

        plans = self.db.get_sales_plans()
        if not plans or selected_row >= len(plans):
            return

        plan_id = plans[selected_row][0]
        daily_plan = self.daily_plan_input.value()
        monthly_plan = self.monthly_plan_input.value()

        # проверка логической согласованности планов
        if monthly_plan < daily_plan * 30:
            reply = QMessageBox.question(self, "Предупреждение",
                                         f"Месячный план ({monthly_plan:,.2f} ₽) меньше чем ежедневный план × 30 дней ({daily_plan * 30:,.2f} ₽).\nПродолжить?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        result = self.db.update_sales_plan(plan_id, daily_plan, monthly_plan)
        if result is not None:
            self.load_sales_plans()
            QMessageBox.information(self, "Успех", "План продаж обновлен")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось обновить план продаж")

    def delete_sales_plan(self):
        selected_row = self.plans_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите план для удаления")
            return

        plans = self.db.get_sales_plans()
        if not plans or selected_row >= len(plans):
            return

        plan_id = plans[selected_row][0]
        reply = QMessageBox.question(self, "Подтверждение", "Вы уверены, что хотите удалить этот план?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            result = self.db.delete_sales_plan(plan_id)
            if result is not None:
                self.load_sales_plans()
                self.clear_plan_form()
                QMessageBox.information(self, "Успех", "План продаж удален")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить план продаж")

    def load_plan_data(self):
        selected_row = self.plans_table.currentRow()
        if selected_row >= 0:
            plans = self.db.get_sales_plans()
            if plans and selected_row < len(plans):
                plan = plans[selected_row]
                branch_index = self.plan_branch_combo.findData(plan[1])
                if branch_index >= 0:
                    self.plan_branch_combo.setCurrentIndex(branch_index)
                self.plan_year_input.setValue(plan[2])
                self.plan_month_combo.setCurrentIndex(plan[3] - 1)
                self.daily_plan_input.setValue(plan[4])
                self.monthly_plan_input.setValue(plan[5])

    def clear_plan_form(self):
        self.plan_branch_combo.setCurrentIndex(-1)
        self.plan_year_input.setValue(datetime.now().year)
        self.plan_month_combo.setCurrentIndex(datetime.now().month - 1)
        self.daily_plan_input.setValue(0.01)
        self.monthly_plan_input.setValue(0.01)
        self.plans_table.clearSelection()


class NavigationMenu(QWidget):
    def __init__(self, parent=None, user_role='employee'):
        super().__init__(parent)
        self.parent = parent
        self.user_role = user_role
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        self.menu_button = QPushButton("☰")
        self.menu_button.setStyleSheet("""
            QPushButton { background: #495057; color: white; border: none; padding: 8px 12px; border-radius: 4px; font-size: 16px; }
            QPushButton:hover { background: #6c757d; }
        """)
        self.menu_button.setFixedSize(40, 30)
        self.menu_button.clicked.connect(self.toggle_menu)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)

        self.prev_button = QPushButton("← Назад")
        self.prev_button.setStyleSheet("""
            QPushButton { background: #6c757d; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #5a6268; }
            QPushButton:disabled { background: #adb5bd; color: #6c757d; }
        """)
        self.prev_button.clicked.connect(self.go_previous)

        self.next_button = QPushButton("Вперед →")
        self.next_button.setStyleSheet("""
            QPushButton { background: #6c757d; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #5a6268; }
            QPushButton:disabled { background: #adb5bd; color: #6c757d; }
        """)
        self.next_button.clicked.connect(self.go_next)

        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)

        layout.addWidget(self.menu_button)
        layout.addLayout(nav_layout)
        layout.addStretch()

        role_label = QLabel(f"Роль: {'Администратор' if self.user_role == 'admin' else 'Сотрудник'}")
        role_label.setStyleSheet("color: #495057; font-weight: bold;")
        layout.addWidget(role_label)

        self.setLayout(layout)

        self.menu_dialog = QDialog(self)
        self.menu_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.menu_dialog.setStyleSheet("QDialog { background: white; border: 1px solid #dee2e6; border-radius: 5px; }")

        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(10, 10, 10, 10)
        menu_layout.setSpacing(5)

        if self.user_role == 'admin':
            for text, slot in [("Управление филиалами", self.show_branches_management),
                               ("Управление сотрудниками", self.show_employees_management),
                               ("Планы продаж", self.show_sales_plans)]:
                btn = QPushButton(text)
                btn.setStyleSheet("""
                    QPushButton { background: white; color: #495057; border: 1px solid #dee2e6; padding: 8px 12px; border-radius: 3px; text-align: left; }
                    QPushButton:hover { background: #e9ecef; }
                """)
                btn.clicked.connect(slot)
                menu_layout.addWidget(btn)

        self.progress_chart_btn = QPushButton("График прогресса")
        self.progress_chart_btn.setStyleSheet("""
            QPushButton { background: white; color: #495057; border: 1px solid #dee2e6; padding: 8px 12px; border-radius: 3px; text-align: left; }
            QPushButton:hover { background: #e9ecef; }
        """)
        self.progress_chart_btn.clicked.connect(self.show_progress_chart)
        menu_layout.addWidget(self.progress_chart_btn)

        self.exit_btn = QPushButton("Выход")
        self.exit_btn.setStyleSheet("""
            QPushButton { background: #dc3545; color: white; border: none; padding: 8px 12px; border-radius: 3px; text-align: left; }
            QPushButton:hover { background: #c82333; }
        """)
        self.exit_btn.clicked.connect(self.exit_application)
        menu_layout.addWidget(self.exit_btn)

        menu_layout.addStretch()
        self.menu_dialog.setLayout(menu_layout)

    def toggle_menu(self):
        button_rect = self.menu_button.rect()
        button_pos = self.menu_button.mapToGlobal(button_rect.bottomLeft())
        self.menu_dialog.move(button_pos)
        self.menu_dialog.resize(200, self.menu_dialog.sizeHint().height())
        self.menu_dialog.exec()

    def show_branches_management(self):
        self.menu_dialog.close()
        if self.parent:
            self.parent.open_branches_management()

    def show_employees_management(self):
        self.menu_dialog.close()
        if self.parent:
            self.parent.open_employees_management()

    def show_sales_plans(self):
        self.menu_dialog.close()
        if self.parent:
            self.parent.open_sales_plans()

    def show_progress_chart(self):
        self.menu_dialog.close()
        if self.parent:
            self.parent.open_progress_chart()

    def go_previous(self):
        reply = QMessageBox.question(self, "Подтверждение выхода", "Вы точно хотите выйти из аккаунта?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.parent:
                self.parent.exit_to_login()

    def go_next(self):
        if hasattr(self.parent, 'open_progress_chart'):
            self.parent.open_progress_chart()

    def exit_application(self):
        """Закрытие приложения"""
        self.menu_dialog.close()
        reply = QMessageBox.question(self, "Подтверждение выхода",
                                     "Вы уверены, что хотите закрыть приложение?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()


class SalesAnalysisWindow(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.db = DatabaseManager()
        self.user_data = user_data
        self.user_role = user_data.get('role', 'employee')
        self.is_closing_via_exit = False
        self.current_sales_data = []  # Для хранения текущих данных

        role_text = "Администратор" if self.user_role == 'admin' else "Сотрудник"
        self.setWindowTitle(f"Система анализа и учета продаж - {user_data['full_name']} ({role_text})")
        self.resize(1250, 750)
        self.setMinimumSize(1250, 750)
        self.setFont(QFont("Courier New", 10))

        central_widget = GradientWidget()
        self.setCentralWidget(central_widget)
        self.init_ui()
        self.load_sales_data()

    def init_ui(self):
        self.navigation_menu = NavigationMenu(self, self.user_role)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.navigation_menu)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)

        if self.user_role == 'employee':
            left_panel = self.create_input_panel()
            left_panel.setMaximumWidth(500)
            content_layout.addWidget(left_panel)
        else:
            left_panel = self.create_admin_info_panel()
            left_panel.setMaximumWidth(500)
            content_layout.addWidget(left_panel)

        right_panel = self.create_table_panel()
        content_layout.addWidget(right_panel)

        main_layout.addLayout(content_layout)
        self.centralWidget().setLayout(main_layout)

    def create_table_panel(self):
        panel = QWidget()
        panel.setStyleSheet(
            "QWidget { background: white; border-radius: 10px; border: 1px solid #dee2e6; padding: 20px; }")
        layout = QVBoxLayout()

        role_text = "просмотра" if self.user_role == 'admin' else "управления"
        table_title = QLabel(f"История продаж (режим {role_text})")
        table_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        table_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(table_title)

        # панель поиска только для админа
        if self.user_role == 'admin':
            search_panel = self.create_search_panel()
            layout.addWidget(search_panel)

        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(8)
        self.sales_table.setHorizontalHeaderLabels([
            "№", "Дата", "Выручка", "Кол-во транзакций", "Сотрудник", "Филиал", "Средний чек", "Примечания"
        ])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sales_table.setSelectionBehavior(QTableWidget.SelectRows)

        if self.user_role == 'admin':
            self.sales_table.setSelectionMode(QTableWidget.NoSelection)
        else:
            self.sales_table.itemSelectionChanged.connect(self.load_selected_row)

        layout.addWidget(self.sales_table)

        # кнопка экспорта в Exel
        if self.user_role == 'admin':
            export_button = QPushButton("Экспорт в Excel")
            export_button.setStyleSheet("""
                QPushButton { 
                    background: #B5C7A3; 
                    color: white; 
                    border: none; 
                    padding: 10px 15px; 
                    border-radius: 5px; 
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover { 
                    background: #218838; 
                }
                QPushButton:pressed { 
                    background: #1e7e34; 
                }
            """)
            export_button.clicked.connect(self.export_to_excel)
            layout.addWidget(export_button)

        panel.setLayout(layout)
        return panel

    def export_to_excel(self):
        """Экспорт данных с автоматическим открытием"""
        try:
            # проверка доступности openpyxl
            if not OPENPYXL_AVAILABLE:
                QMessageBox.warning(
                    self,
                    "Функция недоступна",
                    "Для экспорта в Excel требуется установить библиотеку openpyxl.\n\n"
                    "Установите её с помощью команды:\n"
                    "pip install openpyxl"
                )
                return

            if not self.current_sales_data:
                QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта")
                return

            # создаем DataFrame из данных
            df_data = []
            for sale in self.current_sales_data:
                df_data.append({
                    'ID': sale[0],
                    'Дата': sale[1],
                    'Выручка (руб)': f"{float(sale[2]):,.2f}",
                    'Количество транзакций': int(sale[3]),
                    'Средний чек (руб)': f"{float(sale[4]) if sale[4] else 0:.2f}",
                    'Сотрудник': sale[5] if sale[5] else "Не указан",
                    'Филиал': sale[6] if sale[6] else "Не указан",
                    'Примечания': sale[7] if sale[7] else "",
                    'Пользователь': sale[8] if len(sale) > 8 else "Не указан"
                })

            df = pd.DataFrame(df_data)

            # создаем имя файла с текущей датой
            current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"отчет_продаж_{current_date}.xlsx"

            # сохраняем в Excel с настройками форматирования
            try:
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Отчет продаж', index=False)

                    # Получаем workbook и worksheet для форматирования
                    workbook = writer.book
                    worksheet = writer.sheets['Отчет продаж']

                    # Настраиваем ширину столбцов
                    column_widths = {
                        'A': 8,  # ID
                        'B': 12,  # Дата
                        'C': 15,  # Выручка
                        'D': 10,  # Транзакции
                        'E': 15,  # Средний чек
                        'F': 20,  # Сотрудник
                        'G': 20,  # Филиал
                        'H': 30,  # Примечания
                        'I': 20  # Пользователь
                    }

                    for col, width in column_widths.items():
                        worksheet.column_dimensions[col].width = width

                    # делаем заголовки жирными
                    for cell in worksheet[1]:
                        cell.font = openpyxl.styles.Font(bold=True)
                        cell.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center',
                                                                   wrap_text=True)

            except Exception as e:
                # если произошла ошибка при форматировании, просто сохраняем без форматирования
                df.to_excel(filename, index=False, sheet_name='Отчет продаж')

            # автоматически открываем файл в Excel
            self.open_excel_file(filename)

            # показываем сообщение об успехе
            QMessageBox.information(
                self,
                "Экспорт завершен",
                f"Данные успешно экспортированы в Excel!\n\n"
                f"Всего записей: {len(df)}\n"
                f"Файл: {filename}\n\n"
                f"Файл автоматически открывается..."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка экспорта",
                f"Произошла ошибка:\n{str(e)}"
            )

    def open_excel_file(self, filename):
        """Автоматическое открытие файла в Excel"""
        try:
            import os
            import platform
            import subprocess

            # получаем абсолютный путь к файлу
            filepath = os.path.abspath(filename)
            print(f"Пытаемся открыть файл: {filepath}")  # Для отладки

            # определяем операционную систему
            system = platform.system()

            if system == "Windows":
                os.startfile(filepath)
            elif system == "Darwin":
                # Для macOS
                subprocess.run(["open", filepath])
            else:
                # Для Linux
                subprocess.run(["xdg-open", filepath])

        except Exception as e:
            print(f"Не удалось автоматически открыть файл: {e}")
            # Показываем пользователю где файл
            import os
            filepath = os.path.abspath(filename)
            QMessageBox.information(
                self,
                "Файл создан",
                f"Файл сохранен по пути:\n{filepath}\n\n"
                f"Пожалуйста, откройте его вручную в Excel."
            )

    def create_search_panel(self):
        """Создает панель поиска для таблицы продаж"""
        search_widget = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 10, 0, 10)

        search_label = QLabel("Поиск:")
        search_label.setStyleSheet("font-weight: bold; color: #495057;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по дате, сотруднику, филиалу, примечаниям...")
        self.search_input.setStyleSheet("""
            QLineEdit { 
                padding: 8px; 
                border: 1px solid #adb5bd; 
                border-radius: 5px; 
                background: white; 
                font-size: 14px; 
            }
            QLineEdit:focus { 
                border-color: #495057; 
                background: #ffffff; 
            }
        """)
        self.search_input.textChanged.connect(self.filter_sales_data)

        clear_button = QPushButton("Очистить")
        clear_button.setStyleSheet("""
            QPushButton { 
                background: #adb5bd; 
                color: white; 
                border: none; 
                padding: 8px 12px; 
                border-radius: 5px; 
                font-size: 12px; 
            }
            QPushButton:hover { 
                background: #6c757d; 
            }
        """)
        clear_button.clicked.connect(self.clear_search)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(clear_button)

        search_widget.setLayout(search_layout)
        return search_widget

    def filter_sales_data(self):
        """Фильтрация данных в таблице по поисковому запросу"""
        search_text = self.search_input.text().strip().lower()

        if not search_text:
            # Если поиск пустой, показываем все данные
            self.display_sales_data(self.current_sales_data)
            return

        filtered_data = []
        for sale in self.current_sales_data:
            # Проверяем все текстовые поля на совпадение
            if (search_text in sale[1].lower() or  # Дата
                    search_text in sale[5].lower() or  # Сотрудник
                    search_text in sale[6].lower() or  # Филиал
                    (sale[7] and search_text in sale[7].lower()) or  # Примечания
                    search_text in f"{float(sale[2]):.2f}" or  # Выручка
                    search_text in str(int(sale[3])) or  # Количество транзакций
                    search_text in f"{float(sale[4] if sale[4] else 0):.2f}"):  # Средний чек
                filtered_data.append(sale)

        self.display_sales_data(filtered_data)

    def clear_search(self):
        """Очистка поиска и отображение всех данных"""
        self.search_input.clear()
        self.display_sales_data(self.current_sales_data)

    def load_sales_data(self):
        """Загрузка данных о продажах из базы данных"""
        try:
            sales = self.db.get_all_sales()
            if sales is not None:
                self.current_sales_data = sales  # Сохраняем полные данные
                self.display_sales_data(sales)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки данных: {str(e)}")

    def display_sales_data(self, sales_data):
        """Отображение данных в таблице"""
        try:
            self.sales_table.setRowCount(len(sales_data))
            for row, sale in enumerate(sales_data):
                self.sales_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.sales_table.setItem(row, 1, QTableWidgetItem(sale[1]))  # Дата
                self.sales_table.setItem(row, 2, QTableWidgetItem(f"{float(sale[2]):.2f} ₽"))  # Выручка
                self.sales_table.setItem(row, 3, QTableWidgetItem(str(int(sale[3]))))  # Транзакции
                self.sales_table.setItem(row, 4, QTableWidgetItem(sale[5] if sale[5] else "Не указан"))  # Сотрудник
                self.sales_table.setItem(row, 5, QTableWidgetItem(sale[6] if sale[6] else "Не указан"))  # Филиал

                # Средний чек
                avg_check = sale[4] if sale[4] else 0
                self.sales_table.setItem(row, 6, QTableWidgetItem(f"{float(avg_check):.2f} ₽"))

                # Примечания
                self.sales_table.setItem(row, 7, QTableWidgetItem(sale[7] if sale[7] else ""))

                # Делаем все ячейки нередактируемыми
                for col in range(self.sales_table.columnCount()):
                    item = self.sales_table.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка отображения данных: {str(e)}")

    def create_input_panel(self):
        panel = QWidget()
        panel.setStyleSheet(
            "QWidget { background: white; border-radius: 10px; border: 1px solid #dee2e6; padding: 20px; }")
        layout = QVBoxLayout()
        layout.setSpacing(15)

        title = QLabel("Ввод данных о продажах")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.revenue_input = QDoubleSpinBox()
        self.revenue_input.setRange(0, 1000000)
        self.revenue_input.setPrefix("₽ ")
        self.revenue_input.setDecimals(2)
        self.transactions_input = QDoubleSpinBox()
        self.transactions_input.setRange(0, 10000)
        self.transactions_input.setDecimals(0)
        self.employee_combo = QComboBox()
        self.branch_combo = QComboBox()
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Примечания...")

        # Установка валидатора для примечаний (ограничение длины)
        notes_validator = QRegularExpressionValidator(QRegularExpression(r'^.{0,200}$'))
        self.notes_input.setValidator(notes_validator)

        form_layout.addRow("Дата:", self.date_input)
        form_layout.addRow("Выручка:", self.revenue_input)
        form_layout.addRow("Количество транзакций:", self.transactions_input)
        form_layout.addRow("Сотрудник:", self.employee_combo)
        form_layout.addRow("Филиал:", self.branch_combo)
        form_layout.addRow("Примечания:", self.notes_input)

        layout.addLayout(form_layout)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)

        self.add_button = QPushButton("Добавить запись")
        self.add_button.setStyleSheet("""
            QPushButton { background: #495057; color: white; border: none; padding: 12px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background: #6c757d; }
        """)
        self.add_button.clicked.connect(self.add_sale_record)

        self.update_button = QPushButton("Обновить запись")
        self.update_button.setStyleSheet("""
            QPushButton { background: #495057; color: white; border: none; padding: 12px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background: #6c757d; }
        """)
        self.update_button.clicked.connect(self.update_sale_record)

        self.delete_button = QPushButton("Удалить запись")
        self.delete_button.setStyleSheet("""
            QPushButton { background: #495057; color: white; border: none; padding: 12px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background: #6c757d; }
        """)
        self.delete_button.clicked.connect(self.delete_sale_record)

        self.clear_button = QPushButton("Очистить форму")
        self.clear_button.setStyleSheet("""
            QPushButton { background: #adb5bd; color: white; border: none; padding: 12px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background: #6c757d; }
        """)
        self.clear_button.clicked.connect(self.clear_form)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)
        layout.addStretch()
        panel.setLayout(layout)

        self.load_employees_combo()
        self.load_branches_combo()
        return panel

    def create_admin_info_panel(self):
        panel = QWidget()
        panel.setStyleSheet(
            "QWidget { background: white; border-radius: 10px; border: 1px solid #dee2e6; padding: 20px; }")
        layout = QVBoxLayout()
        layout.setSpacing(15)

        title = QLabel("Панель просмотра")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        info_label = QLabel(
            "Режим администратора\n"
            "Вы находитесь в режиме просмотра данных.\n"
            "Для управления филиалами, сотрудниками и планами продаж используйте меню в левом верхнем углу"
        )
        info_label.setStyleSheet("color: #6c757d; font-size: 14px; line-height: 1.5;")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        stats_group = QGroupBox("Статистика")
        stats_layout = QVBoxLayout()
        sales_count = len(self.db.get_all_sales() or [])
        employees_count = len(self.db.get_all_employees() or [])
        branches_count = len(self.db.get_all_branches() or [])
        stats_layout.addWidget(QLabel(f"Всего продаж: {sales_count}"))
        stats_layout.addWidget(QLabel(f"Сотрудников: {employees_count}"))
        stats_layout.addWidget(QLabel(f"Филиалов: {branches_count}"))
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def load_employees_combo(self):
        try:
            employees = self.db.get_all_employees()
            if not hasattr(self, 'employee_combo') or self.employee_combo is None:
                return
            self.employee_combo.clear()
            self.employee_combo.addItem("Не указан", 0)
            if employees:
                for employee in employees:
                    employee_id = employee[0]
                    employee_name = employee[1]
                    self.employee_combo.addItem(employee_name, employee_id)
        except Exception as e:
            print(f"Ошибка загрузки сотрудников: {e}")

    def load_branches_combo(self):
        try:
            branches = self.db.get_all_branches()
            if not hasattr(self, 'branch_combo') or self.branch_combo is None:
                return
            self.branch_combo.clear()
            self.branch_combo.addItem("Не указан", 0)
            if branches:
                for branch in branches:
                    branch_id = branch[0]
                    branch_name = branch[1]
                    self.branch_combo.addItem(branch_name, branch_id)
        except Exception as e:
            print(f"Ошибка загрузки филиалов: {e}")

    def add_sale_record(self):
        if self.user_role != 'employee':
            QMessageBox.warning(self, "Ошибка", "Только сотрудники могут добавлять записи о продажах")
            return

        date = self.date_input.date().toString("yyyy-MM-dd")
        revenue = self.revenue_input.value()
        transactions = int(self.transactions_input.value())
        employee_id = self.employee_combo.currentData()
        branch_id = self.branch_combo.currentData()
        notes = self.notes_input.text()
        user_id = self.user_data['id']  # Получаем ID текущего пользователя

        if revenue <= 0:
            QMessageBox.warning(self, "Ошибка", "Введите корректную выручку")
            return

        average_check = revenue / transactions if transactions > 0 else 0
        try:
            result = self.db.add_sale(date, revenue, transactions, average_check, employee_id, branch_id, notes,
                                      user_id)
            if result is not None:
                self.load_sales_data()
                self.clear_form()
                QMessageBox.information(self, "Успех", "Запись добавлена")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка добавления: {str(e)}")

    def update_sale_record(self):
        if self.user_role != 'employee':
            QMessageBox.warning(self, "Ошибка", "Только сотрудники могут редактировать записи о продажах")
            return

        sale_id = self.get_selected_sale_id()
        if not sale_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для редактирования")
            return

        date = self.date_input.date().toString("yyyy-MM-dd")
        revenue = self.revenue_input.value()
        transactions = int(self.transactions_input.value())
        employee_id = self.employee_combo.currentData()
        branch_id = self.branch_combo.currentData()
        notes = self.notes_input.text()
        average_check = revenue / transactions if transactions > 0 else 0
        user_id = self.user_data['id']  # Получаем ID текущего пользователя

        try:
            result = self.db.update_sale(sale_id, date, revenue, transactions, average_check, employee_id, branch_id,
                                         notes, user_id)
            if result is not None:
                self.load_sales_data()
                QMessageBox.information(self, "Успех", "Запись обновлена")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка обновления: {str(e)}")

    def delete_sale_record(self):
        if self.user_role != 'employee':
            QMessageBox.warning(self, "Ошибка", "Только сотрудники могут удалять записи о продажах")
            return

        sale_id = self.get_selected_sale_id()
        if not sale_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
            return

        reply = QMessageBox.question(self, "Подтверждение", "Вы уверены, что хотите удалить эту запись?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                result = self.db.delete_sale(sale_id)
                if result is not None:
                    self.load_sales_data()
                    self.clear_form()
                    QMessageBox.information(self, "Успех", "Запись удалена")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка удаления: {str(e)}")

    def get_selected_sale_id(self):
        selected = self.sales_table.currentRow()
        if selected >= 0:
            sales = self.db.get_all_sales()
            if sales and selected < len(sales):
                return sales[selected][0]
        return None

    def load_selected_row(self):
        if self.user_role != 'employee':
            return

        sale_id = self.get_selected_sale_id()
        if sale_id:
            sales = self.db.get_all_sales()
            if sales:
                for sale in sales:
                    if sale[0] == sale_id:
                        date = QDate.fromString(sale[1], "yyyy-MM-dd")
                        self.date_input.setDate(date)
                        self.revenue_input.setValue(float(sale[2]))
                        self.transactions_input.setValue(int(sale[3]))
                        employee_name = sale[5] if sale[5] else ""
                        if self.employee_combo is not None:
                            index = self.employee_combo.findText(employee_name)
                            if index >= 0:
                                self.employee_combo.setCurrentIndex(index)
                        branch_name = sale[6] if sale[6] else ""
                        if self.branch_combo is not None:
                            branch_index = self.branch_combo.findText(branch_name)
                            if branch_index >= 0:
                                self.branch_combo.setCurrentIndex(branch_index)
                        notes = sale[7] if sale[7] else ""
                        self.notes_input.setText(notes)
                        break

    def clear_form(self):
        if self.user_role != 'employee':
            return

        self.date_input.setDate(QDate.currentDate())
        self.revenue_input.setValue(0)
        self.transactions_input.setValue(0)
        if self.employee_combo is not None:
            self.employee_combo.setCurrentIndex(0)
        if self.branch_combo is not None:
            self.branch_combo.setCurrentIndex(0)
        self.notes_input.clear()
        self.sales_table.clearSelection()

    def open_branches_management(self):
        dialog = BranchManagementDialog(self)
        dialog.exec()

    def open_employees_management(self):
        dialog = EmployeeManagementDialog(self)
        dialog.exec()

    def open_sales_plans(self):
        dialog = SalesPlansDialog(self)
        dialog.exec()

    def open_progress_chart(self):
        # Закрываем основное окно перед открытием графика
        self.hide()
        self.progress_window = ProgressChartWindow(self.user_data, self)
        self.progress_window.show()

    def exit_to_login(self):
        self.is_closing_via_exit = True
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()

    def closeEvent(self, event):
        if not self.is_closing_via_exit:
            reply = QMessageBox.question(self, "Подтверждение выхода", "Вы уверены, что хотите выйти из системы?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.is_closing_via_exit = True
                event.accept()
                login_window = LoginWindow()
                login_window.show()
            else:
                event.ignore()
        else:
            event.accept()


class ProgressChartWindow(QMainWindow):
    def __init__(self, user_data, parent_window=None):
        super().__init__()
        self.user_data = user_data
        self.db = DatabaseManager()
        self.parent_window = parent_window
        self.selected_branch_id = None  # Добавляем переменную для хранения выбранного филиала
        self.setWindowTitle("График прогресса выполнения плана")
        self.resize(1250, 750)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("График прогресса выполнения плана")
        title_label.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; color: #495057; padding: 10px; }")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Добавляем выбор филиала
        branch_layout = QHBoxLayout()
        branch_label = QLabel("Выберите филиал:")
        branch_label.setStyleSheet("font-weight: bold; color: #495057;")

        self.branch_combo = QComboBox()
        self.branch_combo.setMinimumWidth(300)
        self.load_branches_combo()
        self.branch_combo.currentIndexChanged.connect(self.on_branch_changed)

        branch_layout.addWidget(branch_label)
        branch_layout.addWidget(self.branch_combo)
        branch_layout.addStretch()
        layout.addLayout(branch_layout)

        button_layout = QHBoxLayout()

        back_button = QPushButton("← Назад")
        back_button.setStyleSheet("""
            QPushButton { background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background: #5a6268; }
        """)
        back_button.clicked.connect(self.go_back_to_main)

        refresh_button = QPushButton("Обновить данные")
        refresh_button.setStyleSheet("""
            QPushButton { background: #495057; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background: #6c757d; }
        """)
        refresh_button.clicked.connect(self.load_data)

        button_layout.addWidget(back_button)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()

        self.figure = Figure(figsize=(14, 10), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        stats_group = QGroupBox("Статистика выполнения плана")
        stats_layout = QHBoxLayout()
        stats_data = [
            ("plan_completion", "Выполнение плана:"),
            ("forecast_percent", "Прогноз выполнения:"),
            ("forecast_value", "Прогноз в рублях:"),
            ("avg_revenue", "Средняя выручка:"),
            ("avg_check", "Средний чек:"),
            ("total_transactions", "Всего транзакций:")
        ]
        self.stats_widgets = {}
        for key, label in stats_data:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout()
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #6c757d; font-size: 12px;")
            value_widget = QLabel("0")
            value_widget.setStyleSheet("font-size: 16px; font-weight: bold; color: #495057;")
            value_widget.setAlignment(Qt.AlignCenter)
            stat_layout.addWidget(label_widget)
            stat_layout.addWidget(value_widget)
            stat_widget.setLayout(stat_layout)
            stats_layout.addWidget(stat_widget)
            self.stats_widgets[key] = value_widget
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        layout.addLayout(button_layout)
        central_widget.setLayout(layout)

    def load_branches_combo(self):
        """Загрузка списка филиалов в комбобокс"""
        try:
            branches = self.db.get_all_branches()
            self.branch_combo.clear()
            self.branch_combo.addItem("Все филиалы", 0)  # Добавляем опцию "Все филиалы"
            if branches:
                for branch in branches:
                    branch_id = branch[0]
                    branch_name = branch[1]
                    self.branch_combo.addItem(branch_name, branch_id)
        except Exception as e:
            print(f"Ошибка загрузки филиалов: {e}")

    def on_branch_changed(self):
        """Обработчик изменения выбранного филиала"""
        self.selected_branch_id = self.branch_combo.currentData()
        self.load_data()

    def go_back_to_main(self):
        """Возврат в главное окно - закрываем текущее и показываем родительское"""
        self.close()
        if self.parent_window:
            self.parent_window.show()

    def closeEvent(self, event):
        """При закрытии окна графиков показываем родительское окно"""
        if self.parent_window:
            self.parent_window.show()
        event.accept()

    def load_data(self):
        try:
            # Получаем данные о продажах с фильтрацией по филиалу
            if self.selected_branch_id and self.selected_branch_id != 0:
                # Если выбран конкретный филиал, фильтруем данные
                all_sales = self.db.get_all_sales()
                if all_sales:
                    filtered_sales = []
                    for sale in all_sales:
                        # sale[6] содержит название филиала, нам нужно найти ID филиала
                        branch_name = sale[6]
                        branches = self.db.get_all_branches()
                        for branch in branches:
                            if branch[1] == branch_name:
                                if branch[0] == self.selected_branch_id:
                                    filtered_sales.append(sale)
                                break
                    sales_data = filtered_sales
                else:
                    sales_data = []
            else:
                # Если выбран "Все филиалы" или филиал не выбран, используем все данные
                sales_data = self.db.get_all_sales()

            # Получаем планы продаж с фильтрацией по филиалу
            if self.selected_branch_id and self.selected_branch_id != 0:
                plans_data = self.db.get_sales_plans(self.selected_branch_id)
            else:
                plans_data = self.db.get_sales_plans()

            if not sales_data:
                self.show_empty_chart()
                return

            df = self.create_sales_dataframe(sales_data)
            current_plan = self.get_current_plan(plans_data)
            self.plot_daily_progress(df, current_plan)
            self.update_statistics(df, current_plan)
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            self.show_empty_chart()

    def create_sales_dataframe(self, sales_data):
        data = []
        for sale in sales_data:
            data.append({
                'date': datetime.strptime(sale[1], '%Y-%m-%d'),
                'revenue': float(sale[2]),
                'transactions': int(sale[3]),
                'average_check': float(sale[4]) if sale[4] else 0
            })
        df = pd.DataFrame(data)
        df = df.sort_values('date')
        daily_sales = df.groupby('date').agg({
            'revenue': 'sum',
            'transactions': 'sum',
            'average_check': 'mean'
        }).reset_index()
        return daily_sales

    def get_current_plan(self, plans_data):
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        monthly_plan = 0
        daily_plan = 0

        if plans_data:
            # Если выбран конкретный филиал, берем план для этого филиала
            if self.selected_branch_id and self.selected_branch_id != 0:
                for plan in plans_data:
                    if plan[2] == current_year and plan[3] == current_month:
                        monthly_plan = float(plan[5])
                        daily_plan = float(plan[4])
                        break
            else:
                # Если выбраны "Все филиалы", суммируем планы всех филиалов
                for plan in plans_data:
                    if plan[2] == current_year and plan[3] == current_month:
                        monthly_plan += float(plan[5])
                        daily_plan += float(plan[4])

        return {
            'monthly_plan': monthly_plan,
            'daily_plan': daily_plan,
            'days_in_month': current_date.day,
            'total_days_in_month': (current_date.replace(month=current_month % 12 + 1, day=1) - timedelta(days=1)).day
        }

    def plot_daily_progress(self, df, current_plan):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Получаем название выбранного филиала для заголовка
        branch_name = self.branch_combo.currentText()

        if df.empty or current_plan['monthly_plan'] == 0:
            ax.text(0.5, 0.5, 'Нет данных для построения графика', ha='center', va='center', transform=ax.transAxes,
                    fontsize=14)
            ax.set_xlabel('Дата')
            ax.set_ylabel('Выручка, руб.')
            self.canvas.draw()
            return

        current_date = datetime.now().date()
        current_month = current_date.month
        current_year = current_date.year

        start_date = datetime(current_year, current_month, 1)
        end_date = datetime(current_year, current_month, 30)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        full_dates_df = pd.DataFrame({'date': date_range})
        df_full = pd.merge(full_dates_df, df, on='date', how='left')
        df_full['revenue'] = df_full['revenue'].fillna(0)
        df_full['transactions'] = df_full['transactions'].fillna(0)
        df_full['average_check'] = df_full['average_check'].fillna(0)

        df_past = df_full[df_full['date'].dt.date <= current_date].copy()
        if df_past.empty:
            ax.text(0.5, 0.5, 'Нет данных за текущий период', ha='center', va='center', transform=ax.transAxes,
                    fontsize=14)
            ax.set_xlabel('Дата')
            ax.set_ylabel('Выручка, руб.')
            self.canvas.draw()
            return

        days = list(range(1, 31))
        max_revenue = max(df_past['revenue'].max(), current_plan['daily_plan']) * 1.2
        y_max = max(max_revenue, current_plan['monthly_plan'] / 30 * 1.5)
        ax.set_xlim(0.5, 30.5)
        ax.set_ylim(0, y_max)
        ax.set_xticks(days)
        ax.grid(True, alpha=0.3, axis='both')

        # Отображаем ежедневный план (уже просуммированный для всех филиалов)
        daily_plan_line = [current_plan['daily_plan']] * len(days)
        ax.plot(days, daily_plan_line, label=f'Ежедневный план: {current_plan["daily_plan"]:,.0f} ₽',
                color='#A23B72', linewidth=2, linestyle='--')

        daily_revenues = []
        for day in days:
            date_to_find = datetime(current_year, current_month, day).date()
            day_data = df_past[df_past['date'].dt.date == date_to_find]
            if not day_data.empty:
                daily_revenues.append(day_data['revenue'].iloc[0])
            else:
                daily_revenues.append(0)

        days_passed = min(current_plan['days_in_month'], 30)
        days_to_show = list(range(1, days_passed + 1))
        revenues_to_show = daily_revenues[:days_passed]
        ax.plot(days_to_show, revenues_to_show, label='Фактическая выручка',
                color='#2E86AB', linewidth=3, marker='o', markersize=6)

        for i, (day, revenue) in enumerate(zip(days_to_show, revenues_to_show)):
            if revenue > 0:
                ax.annotate(f'{revenue:,.0f} ₽', (day, revenue), textcoords="offset points", xytext=(0, 10),
                            ha='center', fontsize=8, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

        if current_date.day <= 30:
            today_revenue = daily_revenues[current_date.day - 1] if current_date.day <= len(daily_revenues) else 0
            ax.plot(current_date.day, today_revenue, 'ro', markersize=10, label='Сегодня')

        ax.set_xlabel('День месяца', fontsize=12, fontweight='bold')
        ax.set_ylabel('Выручка за день, руб.', fontsize=10, fontweight='bold')
        month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь",
                       "Ноябрь", "Декабрь"]
        month_name = month_names[current_month - 1]

        # Обновляем заголовок с учетом выбранного филиала
        title = f'Ежедневное выполнение плана продаж - {month_name} {current_year}'
        if branch_name != "Все филиалы":
            title += f' - {branch_name}'

        ax.set_title(title, fontsize=12, fontweight='bold', pad=7)
        ax.legend(loc='upper right', fontsize=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f} ₽'))
        ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
        ax.set_xticklabels(['1', '5', '10', '15', '20', '25', '30'])
        self.figure.tight_layout()
        self.canvas.draw()

    def update_statistics(self, df, current_plan):
        if df.empty or current_plan['monthly_plan'] == 0:
            for widget in self.stats_widgets.values():
                widget.setText("0")
            return

        current_date = datetime.now().date()
        current_month = current_date.month
        current_year = current_date.year
        df_current_month = df[
            (df['date'].dt.month == current_month) &
            (df['date'].dt.year == current_year) &
            (df['date'].dt.date <= current_date)
            ]
        if df_current_month.empty:
            for widget in self.stats_widgets.values():
                widget.setText("0")
            return

        current_revenue = df_current_month['revenue'].sum()
        plan_completion = (current_revenue / current_plan['monthly_plan']) * 100

        days_passed = min(current_plan['days_in_month'], 30)
        days_remaining = 30 - days_passed
        if days_passed > 0 and days_remaining > 0:
            avg_daily_revenue = df_current_month['revenue'].mean()
            forecast_revenue = current_revenue + (avg_daily_revenue * days_remaining)
            forecast_percent = (forecast_revenue / current_plan['monthly_plan']) * 100
        else:
            forecast_revenue = current_revenue
            forecast_percent = plan_completion

        self.stats_widgets['plan_completion'].setText(f"{plan_completion:.1f}%")
        self.stats_widgets['forecast_percent'].setText(f"{forecast_percent:.1f}%")
        self.stats_widgets['forecast_value'].setText(f"{forecast_revenue:,.0f} ₽")
        self.stats_widgets['avg_revenue'].setText(f"{df_current_month['revenue'].mean():,.0f} ₽")
        self.stats_widgets['avg_check'].setText(f"{df_current_month['average_check'].mean():.0f} ₽")
        self.stats_widgets['total_transactions'].setText(f"{df_current_month['transactions'].sum():,}")

    def show_empty_chart(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Нет данных для отображения\nДобавьте данные о продажах и планах',
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_xlabel('День месяца')
        ax.set_ylabel('Выручка за день, руб.')
        for widget in self.stats_widgets.values():
            widget.setText("0")
        self.canvas.draw()


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.current_user = None
        self.setWindowTitle("Авторизация и регистрация")
        self.resize(800, 700)
        self.setMinimumSize(700, 600)
        self.setFont(QFont("Courier New", 10))
        central_widget = GradientWidget()
        self.setCentralWidget(central_widget)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        title_label = QLabel("Вход в систему")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { color: #495057; font-size: 28px; font-weight: bold; margin-bottom: 10px; }")
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Заполните данные для входа")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("QLabel { color: #6c757d; font-size: 14px; margin-bottom: 30px; }")
        main_layout.addWidget(subtitle_label)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #dee2e6; border-radius: 10px; background: white; }
            QTabWidget::tab-bar { alignment: center; }
            QTabBar::tab { background: #e9ecef; border: 1px solid #dee2e6; border-top-left-radius: 8px; border-top-right-radius: 8px; padding: 8px 16px; margin: 2px; color: #495057; font-weight: bold; }
            QTabBar::tab:selected { background: white; color: #495057; }
            QTabBar::tab:hover { background: #f8f9fa; }
        """)

        login_tab = self.create_login_tab()
        self.tab_widget.addTab(login_tab, "Авторизация")
        register_tab = self.create_register_tab()
        self.tab_widget.addTab(register_tab, "Регистрация")

        main_layout.addWidget(self.tab_widget)

        exit_button = QPushButton("Выход")
        exit_button.setStyleSheet("""
            QPushButton { background: #6c757d; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #5a6268; }
        """)
        exit_button.clicked.connect(self.close_application)
        main_layout.addWidget(exit_button)

        self.centralWidget().setLayout(main_layout)

    def create_login_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        email_label = QLabel("Email:")
        email_label.setStyleSheet("color: #495057; font-weight: bold; font-size: 14px;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Введите ваш email")
        self.set_input_style(self.email_input)

        password_label = QLabel("Пароль:")
        password_label.setStyleSheet("color: #495057; font-weight: bold; font-size: 14px;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите ваш пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.set_input_style(self.password_input)

        login_button = QPushButton("Войти")
        login_button.setStyleSheet("""
            QPushButton { background: #495057; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; margin-top: 10px; }
            QPushButton:hover { background: #6c757d; }
        """)
        login_button.clicked.connect(self.handle_login)

        layout.addWidget(email_label)
        layout.addWidget(self.email_input)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(login_button)

        widget.setLayout(layout)
        return widget

    def create_register_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        name_label = QLabel("ФИО:")
        name_label.setStyleSheet("color: #495057; font-weight: bold;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите ваше полное имя")
        self.name_input.setMinimumHeight(35)
        self.name_input.setMinimumWidth(250)

        # Валидатор для имени
        name_validator = QRegularExpressionValidator(QRegularExpression(r'^[A-Za-zА-Яа-я\s\-]{0,50}$'))
        self.name_input.setValidator(name_validator)
        self.set_input_style(self.name_input)

        email_label = QLabel("Email:")
        email_label.setStyleSheet("color: #495057; font-weight: bold;")
        self.reg_email_input = QLineEdit()
        self.reg_email_input.setPlaceholderText("Введите ваш email")
        self.reg_email_input.setMinimumHeight(35)
        self.reg_email_input.setMinimumWidth(300)

        # Валидатор для email
        email_validator = QRegularExpressionValidator(QRegularExpression(r'^[^@\s]+@[^@\s]+\.[^@\s]+$'))
        self.reg_email_input.setValidator(email_validator)
        self.set_input_style(self.reg_email_input)

        role_label = QLabel("Роль:")
        role_label.setStyleSheet("color: #495057; font-weight: bold;")
        self.role_combo = QComboBox()
        self.role_combo.addItem("Сотрудник", "employee")
        self.role_combo.addItem("Администратор", "admin")
        self.role_combo.setMinimumHeight(35)
        self.role_combo.setMinimumWidth(250)

        password_label = QLabel("Пароль:")
        password_label.setStyleSheet("color: #495057; font-weight: bold;")
        self.reg_password_input = QLineEdit()
        self.reg_password_input.setPlaceholderText("Создайте пароль (мин. 6 символов)")
        self.reg_password_input.setEchoMode(QLineEdit.Password)
        self.reg_password_input.setMinimumHeight(35)
        self.reg_password_input.setMinimumWidth(250)

        # Валидатор для пароля (минимум 6 символов)
        password_validator = QRegularExpressionValidator(QRegularExpression(r'^.{6,}$'))
        self.reg_password_input.setValidator(password_validator)
        self.set_input_style(self.reg_password_input)

        confirm_label = QLabel("Подтвердите пароль:")
        confirm_label.setStyleSheet("color: #495057; font-weight: bold;")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Повторите пароль")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(35)
        self.confirm_password_input.setMinimumWidth(250)
        self.set_input_style(self.confirm_password_input)

        register_button = QPushButton("Зарегистрироваться")
        register_button.setStyleSheet("""
            QPushButton { background: #495057; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; margin-top: 10px; min-height: 15px; }
            QPushButton:hover { background: #6c757d; }
        """)
        register_button.clicked.connect(self.handle_register)

        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(email_label)
        layout.addWidget(self.reg_email_input)
        layout.addWidget(role_label)
        layout.addWidget(self.role_combo)
        layout.addWidget(password_label)
        layout.addWidget(self.reg_password_input)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_password_input)
        layout.addWidget(register_button)

        widget.setLayout(layout)
        return widget

    def set_input_style(self, input_field):
        input_field.setStyleSheet("""
            QLineEdit { padding: 10px; border: 1px solid #adb5bd; border-radius: 5px; background: white; font-size: 14px; min-height: 20px; }
            QLineEdit:focus { border-color: #495057; background: #ffffff; }
        """)

    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все поля")
            return

        user = self.db_manager.authenticate_user(email, password)
        if user:
            user_id, full_name, user_email, user_role = user
            self.current_user = {
                'id': user_id,
                'full_name': full_name,
                'email': user_email,
                'role': user_role
            }
            QMessageBox.information(self, "Успех",
                                    f"Добро пожаловать в систему анализа продаж!\nФИО: {full_name}\nEmail: {user_email}\nРоль: {'Администратор' if user_role == 'admin' else 'Сотрудник'}")
            self.email_input.clear()
            self.password_input.clear()
            self.open_main_window()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный email или пароль. Проверьте введенные данные.")

    def handle_register(self):
        name = self.name_input.text().strip()
        email = self.reg_email_input.text().strip()
        role = self.role_combo.currentData()
        password = self.reg_password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not all([name, email, password, confirm_password]):
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все поля")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать минимум 6 символов")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return

        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Ошибка", "Введите корректный email адрес")
            return

        success, message = self.db_manager.create_user(name, email, password, role)
        if success:
            role_text = "Администратор" if role == "admin" else "Сотрудник"
            QMessageBox.information(self, "Успех",
                                    f"Регистрация завершена!\nФИО: {name}\nEmail: {email}\nРоль: {role_text}")
            self.name_input.clear()
            self.reg_email_input.clear()
            self.reg_password_input.clear()
            self.confirm_password_input.clear()
            self.tab_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Ошибка", message)

    def open_main_window(self):
        self.main_window = SalesAnalysisWindow(self.current_user)
        self.main_window.show()
        self.close()

    def close_application(self):
        reply = QMessageBox.question(self, "Подтверждение выхода",
                                     "Вы уверены, что хотите завершить работу приложения?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Courier New", 10))
    welcome_window = WelcomeWindow()
    welcome_window.show()
    sys.exit(app.exec())