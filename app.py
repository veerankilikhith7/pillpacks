from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "pillpack_secret_key"

# ---------------- DATABASE INIT ----------------

# ------------- DATABASE INIT --------------

def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            dosage TEXT,
            time TEXT,
            start_date TEXT,
            end_date TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()
# ---------------- ROUTES ----------------

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ---------------- REGISTER ----------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
        except:
            conn.close()
            return "Username already exists!"

        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['is_admin'] = user[3]   # store admin status

            if user[3] == 1:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))

        else:
            return "Invalid credentials"

    return render_template('login.html')



# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    today = datetime.today().strftime('%Y-%m-%d')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        SELECT * FROM medicines
        WHERE user_id=? AND start_date<=? AND end_date>=?
    ''', (user_id, today, today))

    medicines = cur.fetchall()
    conn.close()

    # Group medicines
    morning = []
    afternoon = []
    night = []

    for med in medicines:
        if med[4] == "Morning":
            morning.append(med)
        elif med[4] == "Afternoon":
            afternoon.append(med)
        elif med[4] == "Night":
            night.append(med)

    return render_template(
        'dashboard.html',
        morning=morning,
        afternoon=afternoon,
        night=night
    )
# ---------------- ADMIN DASHBOARD ----------------

@app.route('/admin_dashboard', methods=['GET'])
def admin_dashboard():

    if 'user_id' not in session or session.get('is_admin') != 1:
        return redirect(url_for('login'))

    search_query = request.args.get('search')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # If search exists → filter users
    if search_query:
        cur.execute(
            "SELECT id, username, is_admin FROM users WHERE username LIKE ?",
            ('%' + search_query + '%',)
        )
    else:
        cur.execute("SELECT id, username, is_admin FROM users")

    users = cur.fetchall()

    # Medicines (unchanged)
    cur.execute("SELECT * FROM medicines")
    medicines = cur.fetchall()

    total_users = len(users)
    total_medicines = len(medicines)

    conn.close()

    return render_template(
        'admin_dashboard.html',
        users=users,
        medicines=medicines,
        total_users=total_users,
        total_medicines=total_medicines
    )

# ---------------- DELETE USER (ADMIN) ----------------

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):

    # Allow only admin
    if 'user_id' not in session or session.get('is_admin') != 1:
        return redirect(url_for('login'))

    # Prevent admin from deleting himself
    if user_id == session['user_id']:
        return "You cannot delete your own admin account!"

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Delete medicines of that user first
    cur.execute("DELETE FROM medicines WHERE user_id=?", (user_id,))

    # Delete user
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))
# ---------------- DELETE MEDICINE (ADMIN) ----------------

@app.route('/delete_medicine_admin/<int:med_id>')
def delete_medicine_admin(med_id):

    if 'user_id' not in session or session.get('is_admin') != 1:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("DELETE FROM medicines WHERE id=?", (med_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))





# ---------------- ADD MEDICINE ----------------

@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        dosage = request.form['dosage']
        time = request.form['time']
        start = request.form['start']
        end = request.form['end']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()

        cur.execute('''
            INSERT INTO medicines (user_id, name, dosage, time, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], name, dosage, time, start, end))

        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template('add_medicine.html')

# ---------------- DELETE MEDICINE ----------------

@app.route('/delete/<int:id>')
def delete(id):
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))
@app.route('/generate_pdf')
def generate_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    today = datetime.today().strftime('%Y-%m-%d')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM medicines
        WHERE user_id=? AND start_date<=? AND end_date>=?
    ''', (user_id, today, today))
    medicines = cur.fetchall()
    conn.close()

    file_path = "pill_schedule.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>SMART PILL PACK - TODAY'S SCHEDULE</b>", styles['Title']))
    elements.append(Spacer(1, 0.5 * inch))

    morning = []
    afternoon = []
    night = []

    for med in medicines:
        if med[4] == "Morning":
            morning.append(med)
        elif med[4] == "Afternoon":
            afternoon.append(med)
        elif med[4] == "Night":
            night.append(med)

    def add_section(title, med_list):
        elements.append(Paragraph(f"<b>{title}</b>", styles['Heading2']))
        elements.append(Spacer(1, 0.2 * inch))

        if med_list:
            for med in med_list:
                elements.append(Paragraph(f"- {med[2]} ({med[3]})", styles['Normal']))
                elements.append(Spacer(1, 0.1 * inch))
        else:
            elements.append(Paragraph("No medicines", styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

        elements.append(Spacer(1, 0.3 * inch))

    add_section("Morning", morning)
    add_section("Afternoon", afternoon)
    add_section("Night", night)

    doc.build(elements)

    return redirect("/static_download")

@app.route('/static_download')
def static_download():
    return send_file("pill_schedule.pdf", as_attachment=True)
# ---------------- EDIT MEDICINE ----------------

@app.route('/edit_medicine/<int:med_id>', methods=['GET', 'POST'])
def edit_medicine(med_id):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # If form submitted → update medicine
    if request.method == 'POST':
        name = request.form['name']
        dosage = request.form['dosage']
        time = request.form['time']

        cur.execute("""
            UPDATE medicines
            SET name=?, dosage=?, time=?
            WHERE id=?
        """, (name, dosage, time, med_id))

        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    # If GET request → load medicine data
    cur.execute("SELECT * FROM medicines WHERE id=?", (med_id,))
    medicine = cur.fetchone()
    conn.close()

    return render_template('edit_medicine.html', medicine=medicine)




# ---------------- RUN ----------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
