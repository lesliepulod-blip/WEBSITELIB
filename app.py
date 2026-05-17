from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify, flash
import os
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'engiarch_digital_library_2026')
DATABASE = 'library.db'

# --- DATABASE SETTINGS ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Create Tables
        db.execute('CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, student_no TEXT UNIQUE, course TEXT, password TEXT, role TEXT DEFAULT "student")')
        db.execute('CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, author TEXT, course_category TEXT, status TEXT DEFAULT "Available")')
        
        # Borrow requests table for admin approval
        db.execute('''CREATE TABLE IF NOT EXISTS borrow_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_no TEXT,
            book_id INTEGER,
            request_date DATE DEFAULT CURRENT_DATE,
            status TEXT DEFAULT "pending",
            FOREIGN KEY(student_no) REFERENCES students(student_no),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )''')
        
        # Fixed transaction table with CURRENT_DATE
        db.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            student_no TEXT, 
            book_id INTEGER, 
            borrow_date DATE DEFAULT CURRENT_DATE, 
            return_date DATE DEFAULT NULL)''')
        
        # Seed Books if empty
        if db.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
            # Seed exactly 5 books per course category (30 total)
            # Categories must match the course_category values used in the app.
            books = [
                # COMPUTER ENGINEERING (5) - original seed set
                ('Computer Networks', 'Kurose & Ross', 'COMPUTER ENGINEERING'),
                ('Data Structures and Algorithms', 'Goodrich', 'COMPUTER ENGINEERING'),
                ('Digital Logic Design', 'M. Morris Mano', 'COMPUTER ENGINEERING'),
                ('Operating Systems', 'Silberschatz', 'COMPUTER ENGINEERING'),
                ('Introduction to Programming', 'Cormen', 'COMPUTER ENGINEERING'),

                # ELECTRONICS ENGINEERING (5)
                ('Electronic Devices', 'S. Salivahanan', 'ELECTRONICS ENGINEERING'),
                ('Digital Signal Processing', 'Proakis', 'ELECTRONICS ENGINEERING'),
                ('Analog Circuits', 'Sedra & Smith', 'ELECTRONICS ENGINEERING'),
                ('Microelectronics', 'Rabaey', 'ELECTRONICS ENGINEERING'),
                ('Communication Systems', 'Taub & Schilling', 'ELECTRONICS ENGINEERING'),

                # MECHANICAL ENGINEERING (5)
                ('Thermodynamics', 'Yunus Cengel', 'MECHANICAL ENGINEERING'),
                ('Fluid Mechanics', 'White', 'MECHANICAL ENGINEERING'),
                ('Heat Transfer', 'Incropera', 'MECHANICAL ENGINEERING'),
                ('Strength of Materials', 'Gere', 'MECHANICAL ENGINEERING'),
                ('Machine Design', 'Norton', 'MECHANICAL ENGINEERING'),

                # CIVIL ENGINEERING (5)
                ('Hydraulics of Open Channel Flow', 'Robert K. Chow', 'CIVIL ENGINEERING'),
                ('Structural Steel Design', 'Besavilla', 'CIVIL ENGINEERING'),
                ('Strength of Materials', 'James M. Gere and Berry J. Goodno', 'CIVIL ENGINEERING'),
                ('Structural Analysis', 'R. C. Hibbler', 'CIVIL ENGINEERING'),
                ('Irrigation and Drainage Engineering', 'Asst. Prof. Dr. Rasul M. Khalaf', 'CIVIL ENGINEERING'),



                # ELECTRICAL ENGINEERING (5)
                ('Circuit Analysis', 'Hayt & Kemmerly', 'ELECTRICAL ENGINEERING'),
                ('Electromagnetics', 'Sadiku', 'ELECTRICAL ENGINEERING'),
                ('Power Systems', 'Grainger', 'ELECTRICAL ENGINEERING'),
                ('Signals and Systems', 'Oppenheim', 'ELECTRICAL ENGINEERING'),
                ('Control Systems', 'Ogata', 'ELECTRICAL ENGINEERING'),

                # ARCHITECTURE (5)
                ('Theory of Architecture', 'Paul-Alan Johnson', 'ARCHITECTURE'),
                ('Building Construction', 'Francis Ching', 'ARCHITECTURE'),
                ('AutoCAD Architecture', 'Fawkes', 'ARCHITECTURE'),
                ('Architectural Design', 'Neufert', 'ARCHITECTURE'),
                ('Architectural Graphics', 'Francis Ching', 'ARCHITECTURE')
            ]

            db.executemany(
                "INSERT INTO books (title, author, course_category, status) VALUES (?, ?, ?, 'Available')",
                books,
            )
    
    
        # Add role column if missing
        try:
            db.execute('ALTER TABLE students ADD COLUMN role TEXT DEFAULT "student"')
        except sqlite3.OperationalError:
            pass
        
        # Add password column if missing (for existing DB)
        try:
            db.execute('ALTER TABLE students ADD COLUMN password TEXT')
        except sqlite3.OperationalError:
            pass
        
        # Add section column
        try:
            db.execute('ALTER TABLE students ADD COLUMN section TEXT')
        except sqlite3.OperationalError:
            pass
        
        # Create default admin if not exists
        admin_count = db.execute('SELECT COUNT(*) FROM students WHERE student_no = "admin" AND role = "admin"').fetchone()[0]
        if admin_count == 0:
            from werkzeug.security import generate_password_hash
            hashed_admin = generate_password_hash('admin123')
            db.execute('INSERT INTO students (student_no, name, role, password) VALUES (?, ?, ?, ?)', 
                      ('admin', 'Library Administrator', 'admin', hashed_admin))
        
        db.commit()

# --- LOGIN PROTECTION DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_no' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- ADMIN PROTECTION DECORATOR ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_no' not in session:
            return redirect(url_for('login_page'))
        db = get_db()
        user = db.execute("SELECT role FROM students WHERE student_no = ?", (session['student_no'],)).fetchone()
        if not user or user['role'] != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def login_page():
    return render_template('login_improved.html')

@app.route('/signup_page')
def signup_page():
    return render_template('signup_improved.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        s_no = request.form.get('student_no')
        course_year = request.form.get('course_year')
        course = course_year.split(' - ')[0] if course_year else request.form.get('course')
        password = request.form.get('password', '').strip()
        
        # Client-side should validate, but server-side too
        # import re
        # if not re.match(r'^\d{4,}$', password):
        #     flash('Password must be numbers only, at least 4 digits.', 'error')
        #     return render_template('signup_improved.html')
        
        hashed_pw = generate_password_hash(password)
        
        db = get_db()
        
        if db.execute("SELECT 1 FROM students WHERE student_no = ?", (s_no,)).fetchone():
            flash('Student ID already registered.', 'error')
            return render_template('signup_improved.html')
        
        try:
            db.execute("INSERT INTO students (name, student_no, course, section, password) VALUES (?, ?, ?, ?, ?)", 
                       (name, s_no, course, request.form.get('section'), hashed_pw))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login_page'))
        except sqlite3.IntegrityError as e:

            if 'student_no' in str(e):
                flash('Student ID already registered.', 'error')
            elif 'password' in str(e):
                flash('Password already in use.', 'error')
            else:
                flash('Registration failed. Try again.', 'error')
            return render_template('signup_improved.html')
    return render_template('signup_improved.html')
    
    hashed_pw = generate_password_hash(password)
    
    db = get_db()
    
    if db.execute("SELECT 1 FROM students WHERE student_no = ?", (s_no,)).fetchone():
        flash('Student ID already registered.', 'error')
        return redirect(url_for('signup_page'))
    
    try:
        db.execute("INSERT INTO students (name, student_no, course, section, password) VALUES (?, ?, ?, ?, ?)", 
                   (name, s_no, course, request.form.get('section'), hashed_pw))
        db.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login_page'))
    except sqlite3.IntegrityError as e:

        if 'student_no' in str(e):
            flash('Student ID already registered.', 'error')
        elif 'password' in str(e):
            flash('Password already in use.', 'error')
        else:
            flash('Registration failed. Try again.', 'error')
        return redirect(url_for('signup_page'))

@app.route('/login', methods=['POST'])
def login():
    s_no = request.form.get('student_no')
    password = request.form.get('password', '').strip()
    db = get_db()
    user = db.execute("SELECT * FROM students WHERE student_no = ?", (s_no,)).fetchone()
    if user and check_password_hash(user['password'], password):
        session['student_no'] = user['student_no']
        session['user_name'] = user['name']
        session['course'] = user['course']
        session['section'] = user['section']
        session['role'] = user['role']
        if user['role'] == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('home'))
    flash('Invalid Student Number or Password. Try again.', 'error')
    return redirect(url_for('login_page'))

@app.route('/home')
@login_required
def home():
    """Renders the Search Page"""
    return render_template('home.html')

@app.route('/courses')
@login_required
def courses():
    """Course-specific books pages"""
    db = get_db()
    course = request.args.get('course')
    if course:
        books = db.execute(
            "SELECT * FROM books WHERE course_category = ? AND status = 'Available' ORDER BY title", 
            (course,)
        ).fetchall()
        return render_template('course_books.html', course_books=books, course_name=course, book_count=len(books))
    return render_template('courses.html')

@app.route('/profile')
@login_required
def profile():
    """Renders Student Record and Transaction History"""
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE student_no = ?", (session['student_no'],)).fetchone()
    
    # Stats for admin profile
    stats = {
        'total_borrows': db.execute('SELECT COUNT(*) FROM transactions WHERE return_date IS NULL').fetchone()[0],
        'total_books': db.execute('SELECT COUNT(*) FROM books').fetchone()[0],
        'available_books': db.execute('SELECT COUNT(*) FROM books WHERE status = "Available"').fetchone()[0],
        'total_users': db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    }
    
    if session.get('role') == 'admin':
        return render_template('admin_profile.html', student=student, stats=stats)
    
    # Get pending borrow requests
    pending_requests = db.execute('''
        SELECT br.id, b.title, br.request_date, br.status 
        FROM borrow_requests br JOIN books b ON br.book_id = b.id 
        WHERE br.student_no = ? AND br.status = "pending"
    ''', (session['student_no'],)).fetchall()
    
    # Get active borrows for students
    current = db.execute('''
        SELECT b.id, b.title, t.borrow_date 
        FROM transactions t JOIN books b ON t.book_id = b.id 
        WHERE t.student_no = ? AND t.return_date IS NULL
    ''', (session['student_no'],)).fetchall()
    
    # Get history
    history = db.execute('''
        SELECT b.title, t.borrow_date, t.return_date 
        FROM transactions t JOIN books b ON t.book_id = b.id 
        WHERE t.student_no = ? AND t.return_date IS NOT NULL
    ''', (session['student_no'],)).fetchall()
    
    return render_template('profile.html', student=student, current=current, history=history, pending_requests=pending_requests)

@app.route('/admin')
@admin_required
def admin():
    """Admin Dashboard"""
    db = get_db()
    # Stats
    stats = {
        'total_borrows': db.execute('SELECT COUNT(*) FROM transactions WHERE return_date IS NULL').fetchone()[0],
        'total_books': db.execute('SELECT COUNT(*) FROM books').fetchone()[0],
        'available_books': db.execute('SELECT COUNT(*) FROM books WHERE status = "Available"').fetchone()[0],
        'total_users': db.execute('SELECT COUNT(*) FROM students').fetchone()[0],
        'registered_students': db.execute('SELECT COUNT(*) FROM students WHERE role = "student"').fetchone()[0]
    }
    # Pending borrow requests
    borrow_requests = db.execute('''
        SELECT br.id, b.title as book_title, s.name as student_name, s.student_no, s.course, s.section, br.request_date
        FROM borrow_requests br 
        JOIN books b ON br.book_id = b.id 
        JOIN students s ON br.student_no = s.student_no
        WHERE br.status = "pending"
        ORDER BY br.request_date DESC
    ''').fetchall()
    # Pending borrows with student details
    pending_borrows = db.execute('''
        SELECT t.id, b.title as book_title, s.name as student_name, s.student_no, s.course, s.section, t.borrow_date
        FROM transactions t 
        JOIN books b ON t.book_id = b.id 
        JOIN students s ON t.student_no = s.student_no
        WHERE t.return_date IS NULL
        ORDER BY t.borrow_date DESC
    ''').fetchall()
    # All registered users
    all_users = db.execute('''
        SELECT name, student_no, course, section, role FROM students ORDER BY student_no
    ''').fetchall()
    return render_template('admin.html', stats=stats, borrow_requests=borrow_requests, pending_borrows=pending_borrows, all_users=all_users)

@app.route('/admin_return/<int:trans_id>')
@admin_required
def admin_return(trans_id):
    """Admin return book"""
    db = get_db()
    db.execute('''
        UPDATE transactions SET return_date = CURRENT_DATE 
        WHERE id = ? AND return_date IS NULL
    ''', (trans_id,))
    book_id = db.execute('SELECT book_id FROM transactions WHERE id = ?', (trans_id,)).fetchone()['book_id']
    db.execute("UPDATE books SET status = 'Available' WHERE id = ?", (book_id,))
    db.commit()
    # Avoid showing a misleading message on the wrong page.
    # The admin return action already updates the dashboard state.
    return redirect(url_for('admin'))


@app.route('/admin_approve_request/<int:req_id>')
@admin_required
def admin_approve_request(req_id):
    """Admin approve borrow request"""
    db = get_db()
    request = db.execute('SELECT * FROM borrow_requests WHERE id = ? AND status = "pending"', (req_id,)).fetchone()
    if not request:
        flash('Request not found or already processed.', 'error')
        return redirect(url_for('admin'))
    
    student_no = request['student_no']
    book_id = request['book_id']
    
    # Create transaction
    db.execute('''
        INSERT INTO transactions (student_no, book_id) VALUES (?, ?)
    ''', (student_no, book_id))
    
    # Update book status
    db.execute('UPDATE books SET status = "Borrowed" WHERE id = ?', (book_id,))
    
    # Mark request as approved
    db.execute('UPDATE borrow_requests SET status = "approved" WHERE id = ?', (req_id,))
    
    db.commit()
    flash('Request approved and book borrowed!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin_reject_request/<int:req_id>')
@admin_required
def admin_reject_request(req_id):
    """Admin reject borrow request"""
    db = get_db()

    # SQLite's cursor.rowcount is unreliable across drivers.
    # Determine success by checking the affected request after update.
    db.execute(
        'UPDATE borrow_requests SET status = "rejected" WHERE id = ? AND status = "pending"',
        (req_id,)
    )
    db.commit()

    updated = db.execute(
        'SELECT id, status FROM borrow_requests WHERE id = ?',
        (req_id,)
    ).fetchone()

    if updated and updated['status'] == 'rejected':
        flash('Request rejected.', 'success')
    else:
        flash('Request not found or already processed.', 'error')

    return redirect(url_for('admin'))


@app.route('/api/courses')
@login_required
def api_courses():
    """API for dynamic course cards"""
    db = get_db()
    courses = db.execute("""
        SELECT course_category as name, COUNT(*) as count 
        FROM books WHERE status = 'Available' 
        GROUP BY course_category 
        ORDER BY count DESC
    """).fetchall()
    return jsonify({'courses': [dict(course) for course in courses]})

@app.route('/books', methods=['GET', 'POST'])
@app.route('/search', methods=['GET'])
@login_required
def books():
    """Search and render books"""
    db = get_db()
    query = request.args.get('q') or request.form.get('q') or request.form.get('course_filter', '')
    if query:
        books = db.execute(
            "SELECT * FROM books WHERE (title LIKE ? OR author LIKE ? OR course_category LIKE ?) AND status = 'Available' ORDER BY title",
            (f'%{query}%', f'%{query}%', f'%{query}%')
        ).fetchall()
    else:
        books = db.execute("SELECT * FROM books WHERE status = 'Available' ORDER BY title").fetchall()
    
    return render_template('book.html', books=books)

@app.route('/borrow/<int:book_id>')
@login_required
def borrow_book(book_id):
    """Request to borrow a book (admin approval needed)"""
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        flash('Book not found!', 'error')
        return redirect(url_for('books'))
    
    # Check if already requested
    existing = db.execute('SELECT 1 FROM borrow_requests WHERE student_no = ? AND book_id = ? AND status = "pending"', 
                         (session['student_no'], book_id)).fetchone()
    if existing:
        flash('Request already pending!', 'error')
        return redirect(url_for('profile'))
    
    db.execute("""
        INSERT INTO borrow_requests (student_no, book_id) 
        VALUES (?, ?)
    """, (session['student_no'], book_id))
    db.commit()
    flash('Borrow request submitted! Awaiting admin approval.', 'success')
    return redirect(url_for('profile'))

@app.route('/return/<int:book_id>')
@login_required
def return_book(book_id):
    """Return a book"""
    db = get_db()
    db.execute("""
        UPDATE transactions SET return_date = CURRENT_DATE 
        WHERE student_no = ? AND book_id = ? AND return_date IS NULL
    """, (session['student_no'], book_id))
    db.execute("UPDATE books SET status = 'Available' WHERE id = ?", (book_id,))
    db.commit()
    return redirect(url_for('profile'))

@app.route('/api/courses_public')
def courses_public():
    """Public courses for signup dropdown"""
    db = get_db()
    courses = db.execute("SELECT DISTINCT course_category FROM books ORDER BY course_category").fetchall()
    return jsonify([{'name': c['course_category']} for c in courses])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
