import sqlite3
import os

DATABASE = 'library.db'

def get_db():
    db = sqlite3.connect(DATABASE, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

def seed_books():
    db = get_db()
    
    courses = [
        'CIVIL ENGINEERING',
        'COMPUTER ENGINEERING', 
        'ARCHITECTURE',
        'MECHANICAL ENGINEERING',
        'ELECTRICAL ENGINEERING',
        'ELECTRONICS ENGINEERING'
    ]
    
    book_data = {
        'CIVIL ENGINEERING': [
            ('Hydraulics of Open Channel Flow', 'Robert K. Chow', 'CIVIL ENGINEERING'),
            ('Structural Steel Design', 'Besavilla', 'CIVIL ENGINEERING'),
            ('Strength of Materials', 'James M. Gere and Berry J. Goodno', 'CIVIL ENGINEERING'),
            ('Structural Analysis', 'R. C. Hibbler', 'CIVIL ENGINEERING'),
            ('Irrigation and Drainage Engineering', 'Asst. Prof. Dr. Rasul M. Khalaf', 'CIVIL ENGINEERING')
        ],

        'COMPUTER ENGINEERING': [
            ('Computer Organization', 'Carl Hamacher', 'COMPUTER ENGINEERING'),
            ('Operating Systems', 'Abraham Silberschatz', 'COMPUTER ENGINEERING'),
            ('Database Systems', 'Korth & Silberschatz', 'COMPUTER ENGINEERING'),
            ('Software Engineering', 'Ian Sommerville', 'COMPUTER ENGINEERING'),
            ('Embedded Systems', 'Wayne Wolf', 'COMPUTER ENGINEERING')
        ],
        'ARCHITECTURE': [
            ('Form Space and Order', 'Francis D.K. Ching', 'ARCHITECTURE'),
            ('A Pattern Language', 'Christopher Alexander', 'ARCHITECTURE'),
            ('The Architecture of Happiness', 'Alain de Botton', 'ARCHITECTURE'),
            ('Towards a New Architecture', 'Le Corbusier', 'ARCHITECTURE'),
            ('Experiences in Architecture', 'Angela Tamms', 'ARCHITECTURE')
        ],
        'MECHANICAL ENGINEERING': [
            ('Machine Design', 'Robert Norton', 'MECHANICAL ENGINEERING'),
            ('Engineering Mechanics Dynamics', 'Hibbeler', 'MECHANICAL ENGINEERING'),
            ('Vibrations', 'Rao', 'MECHANICAL ENGINEERING'),
            ('Control Systems Engineering', 'Nise', 'MECHANICAL ENGINEERING'),
            ('Manufacturing Engineering', 'Kalpakjian', 'MECHANICAL ENGINEERING')
        ],
        'ELECTRICAL ENGINEERING': [
            ('Electric Circuits', 'Nilsson & Riedel', 'ELECTRICAL ENGINEERING'),
            ('Power System Analysis', 'Grainger & Stevenson', 'ELECTRICAL ENGINEERING'),
            ('Control Systems', 'Katsuhiko Ogata', 'ELECTRICAL ENGINEERING'),
            ('Electromagnetic Fields', 'Sadiku', 'ELECTRICAL ENGINEERING'),
            ('Electrical Machines', 'Chapman', 'ELECTRICAL ENGINEERING')
        ],
        'ELECTRONICS ENGINEERING': [
            ('Communication System', ' Simon Haykin and Michael Moher', 'ELECTRONICS ENGINEERING'),
            ('Digital Signal Processing', 'John G. Proakis and Dimitris G. Manolakis', 'ELECTRONICS ENGINEERING'),
            ('Microelectronic Circuit', 'Adel S. Sedra, Kenneth C. Smith, Tony Chan Carusone, Vincent Gaudet', 'ELECTRONICS ENGINEERING'),
            ('Modern Digital Electronic', 'R P Jain, Kishor Sarawadekar', 'ELECTRONICS ENGINEERING'),
            ('Principles of Electronic Communication Systems', 'Louis E. Frenzel Jr.', 'ELECTRONICS ENGINEERING')
        ]
    }
    
    total_added = 0
    for course in courses:
        current_count = db.execute("SELECT COUNT(*) FROM books WHERE course_category = ? AND status = 'Available'", (course,)).fetchone()[0]
        needed = 5 - current_count
        # Special handling for CIVIL ENGINEERING: enforce exactly the requested titles/authors
        # and keep the count exactly 5.
        if course in ('CIVIL ENGINEERING', 'MECHANICAL ENGINEERING', 'COMPUTER ENGINEERING'):
            desired = book_data.get(course, [])
            existing = db.execute(
                "SELECT id FROM books WHERE course_category = ? AND status = 'Available' ORDER BY id",
                (course,)
            ).fetchall()

            # If more than 5 exist, delete the extras (beyond first 5 by id)
            if len(existing) > len(desired):
                extra_ids = [r['id'] for r in existing[len(desired):]]
                db.executemany("DELETE FROM books WHERE id = ?", [(i,) for i in extra_ids])

            # Update first min(len(existing), 5) rows to match desired titles/authors
            for i, (title, author, cat) in enumerate(desired):
                if i >= len(existing):
                    break
                db.execute(
                    "UPDATE books SET title = ?, author = ? WHERE id = ?",
                    (title, author, existing[i]['id'])
                )

            db.commit()

            # Add missing rows if currently fewer than 5
            current_count = db.execute(
                "SELECT COUNT(*) FROM books WHERE course_category = ? AND status = 'Available'",
                (course,)
            ).fetchone()[0]
            needed = len(desired) - current_count
            if needed > 0:
                books_to_add = desired[:needed]
                db.executemany(
                    "INSERT INTO books (title, author, course_category, status) VALUES (?, ?, ?, 'Available')",
                    books_to_add
                )
                db.commit()
            print(f"{course}: Enforced requested CIVIL ENGINEERING books.")
            continue

        if needed <= 0:
            print(f"{course}: Already has {current_count} books, skipping.")
            continue

        books_to_add = book_data.get(course, [])[:needed]
        db.executemany("INSERT INTO books (title, author, course_category, status) VALUES (?, ?, ?, 'Available')", books_to_add)
        added = len(books_to_add)
        total_added += added
        print(f"{course}: Added {added} books (now {current_count + added}/5)")
    
    db.commit()
    db.close()
    print(f"\nTotal books added: {total_added}. Total 30 target reached.")

if __name__ == '__main__':
    seed_books()

