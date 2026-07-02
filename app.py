from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.debug = False

# IMPORTANT for Vercel
def handler(request, context):
    return app(request.environ, start_response)
app.secret_key = "secret123"   # change to anything secure

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS books(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    author TEXT,
    status TEXT,
    course TEXT   -- ✅ NEW COLUMN
)
''')

    # ISSUED BOOKS TABLE (UPDATED)
    c.execute('''
    CREATE TABLE IF NOT EXISTS issued_books(
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    student_id INTEGER,
    issue_date TEXT,
    return_date TEXT,
    FOREIGN KEY(book_id) REFERENCES books(id),
    FOREIGN KEY(student_id) REFERENCES students(id)
)
''')

    # STUDENTS TABLE
    c.execute('''
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        student_id TEXT,
        course TEXT,
        phone TEXT
    )
    ''')

    conn.commit()
    conn.close()

    
# LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():

    if 'user' in session:
        return redirect('/')

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if username == "admin" and password == "1234":
            session['user'] = username
            return redirect('/')

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")

# LOGOUT ROUTE (FIXED)
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ISSUE BOOK (UPDATED VERSION)
@app.route('/issue/<int:id>', methods=['GET','POST'])
def issue_book(id):

    if request.method == "POST":
        student_name = request.form['student']
        issue_date = request.form['issue_date']
        return_date = request.form['return_date']
        if 'user' not in session:
         return redirect('/login')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # GET STUDENT ID FROM NAME
        c.execute("SELECT id FROM students WHERE name = ?", (student_name,))
        student_data = c.fetchone()

        if not student_data:
            conn.close()
            return "❌ Error: Student not found! Please add student first."

        student_id = student_data[0]

        # CHECK IF BOOK IS ALREADY ISSUED
        c.execute("SELECT status FROM books WHERE id=?", (id,))
        book = c.fetchone()

        if book[0] == "Issued":
            conn.close()
            return "❌ Error: Book already issued!"

        # ISSUE BOOK (NOW USING student_id)
        c.execute('''
        INSERT INTO issued_books(book_id, student_id, issue_date, return_date)
        VALUES(?,?,?,?)
        ''',(id, student_id, issue_date, return_date))

        c.execute("UPDATE books SET status='Issued' WHERE id=?", (id,))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("issue_book.html", book_id=id)


# RETURN BOOK
@app.route('/return/<int:id>')
def return_book(id):

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM issued_books WHERE book_id=?", (id,))
    c.execute("UPDATE books SET status='Available' WHERE id=?", (id,))
    if 'user' not in session:
     return redirect('/login')

    conn.commit()
    conn.close()

    return redirect('/')


# HOME PAGE
# UPDATED HOME PAGE WITH SEARCH
@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')

    # Get the search query from the URL (e.g., /?search=Harry)
    search_query = request.args.get('search', '').strip()

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Base Query
    query = '''
        SELECT 
            books.id, 
            books.title, 
            books.author, 
            books.status, 
            students.name 
        FROM books
        LEFT JOIN issued_books ON books.id = issued_books.book_id
        LEFT JOIN students ON issued_books.student_id = students.id
    '''

    if search_query:
        # Filter results based on title or author
        query += " WHERE books.title LIKE ? OR books.author LIKE ?"
        c.execute(query, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        c.execute(query)

    books = c.fetchall()
    conn.close()

    # If search was performed and no books found, we pass a message
    error_msg = None
    if search_query and not books:
        error_msg = f"❌ No books found matching '{search_query}'"

    return render_template("index.html", books=books, error_msg=error_msg, search_query=search_query)



# ADD BOOK
@app.route('/add', methods=['GET','POST'])
def add_book():

    if 'user' not in session:
        return redirect('/login')

    if request.method == "POST":
        title = request.form['title']
        author = request.form['author']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute(
            "INSERT INTO books(title,author,status) VALUES(?,?,?)",
            (title, author, "Available")
        )

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template("add_book.html")


# DELETE BOOK
@app.route('/delete/<int:id>')
def delete(id):

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("DELETE FROM books WHERE id=?", (id,))
    if 'user' not in session:
     return redirect('/login')

    conn.commit()
    conn.close()

    return redirect('/')


# ADD STUDENT
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        student_id = request.form['student_id']
        course = request.form['course']
        phone = request.form['phone']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("""
        INSERT INTO students (name, student_id, course, phone)
        VALUES (?, ?, ?, ?)
        """, (name, student_id, course, phone))

        conn.commit()
        conn.close()

        return redirect('/students')

    return render_template('add_student.html')


# VIEW STUDENTS
@app.route('/students')
def students():
    if 'user' not in session:
     return redirect('/login')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM students")
    data = c.fetchall()

    conn.close()
    return render_template('students.html', students=data)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
