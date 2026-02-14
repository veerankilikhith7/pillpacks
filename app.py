from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "pillpack_secret_key"


# ---------------- DATABASE CONNECTION ----------------

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    return conn


# ---------------- DATABASE INIT ----------------

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            time_period TEXT NOT NULL,
            exact_time TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
# ---------------- HOME ----------------

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

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, 0)",
                (username, hashed_password)
            )
            conn.commit()

            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]

            if total_users == 1:
                cur.execute("UPDATE users SET is_admin=1 WHERE id=1")
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

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['is_admin'] = user[3]

            if user[3] == 1:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))

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

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM medicines
        WHERE user_id=%s AND start_date<=%s AND end_date>=%s
    """, (user_id, today, today))

    medicines = cur.fetchall()
    conn.close()

    # Convert time to 12-hour format
    converted = []
    for med in medicines:
        time_obj = datetime.strptime(med[5], "%H:%M")
        time_12 = time_obj.strftime("%I:%M %p")
        med_list = list(med)
        med_list[5] = time_12
        converted.append(tuple(med_list))

    medicines = converted

    morning, afternoon, night = [], [], []

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

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'user_id' not in session or session.get('is_admin') != 1:
        return redirect(url_for('login'))

    search_query = request.args.get('search')

    conn = get_db_connection()
    cur = conn.cursor()

    # 🔍 SEARCH LOGIC
    if search_query:
        cur.execute(
            "SELECT id, username, is_admin FROM users WHERE username ILIKE %s ORDER BY id ASC",
            ('%' + search_query + '%',)
        )
    else:
        cur.execute("SELECT id, username, is_admin FROM users ORDER BY id ASC")

    users = cur.fetchall()

    # Medicines
    cur.execute("SELECT * FROM medicines ORDER BY id ASC")
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

# ---------------- DELETE USER ----------------

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):

    if 'user_id' not in session or session.get('is_admin') != 1:
        return redirect(url_for('login'))

    if user_id == session['user_id']:
        return "You cannot delete your own admin account!"

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
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
        time_period = request.form['time_period']
        exact_time = request.form['exact_time']
        start_date = request.form['start']
        end_date = request.form['end']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO medicines
            (user_id, name, dosage, time_period, exact_time, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session['user_id'],
            name,
            dosage,
            time_period,
            exact_time,
            start_date,
            end_date
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template('add_medicine.html')


# ---------------- DELETE MEDICINE ----------------

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))


# ---------------- EDIT MEDICINE ----------------

@app.route('/edit_medicine/<int:med_id>', methods=['GET', 'POST'])
def edit_medicine(med_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        dosage = request.form['dosage']
        time_period = request.form['time_period']
        exact_time = request.form['exact_time']

        cur.execute("""
            UPDATE medicines
            SET name=%s, dosage=%s, time_period=%s, exact_time=%s
            WHERE id=%s
        """, (name, dosage, time_period, exact_time, med_id))

        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    cur.execute("SELECT * FROM medicines WHERE id=%s", (med_id,))
    medicine = cur.fetchone()
    conn.close()

    return render_template('edit_medicine.html', medicine=medicine)
# ---------------- GENERATE PDF ----------------

@app.route('/generate_pdf')
def generate_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    today = datetime.today().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM medicines
        WHERE user_id=%s AND start_date<=%s AND end_date>=%s
    """, (user_id, today, today))

    medicines = cur.fetchall()
    conn.close()

    file_path = "pill_schedule.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>SMART PILL PACK - TODAY'S SCHEDULE</b>", styles['Title']))
    elements.append(Spacer(1, 0.5 * inch))

    morning, afternoon, night = [], [], []

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
                elements.append(
                    Paragraph(f"- {med[2]} ({med[3]}) at {med[5]}", styles['Normal'])
                )
                elements.append(Spacer(1, 0.1 * inch))
        else:
            elements.append(Paragraph("No medicines", styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

        elements.append(Spacer(1, 0.3 * inch))

    add_section("Morning", morning)
    add_section("Afternoon", afternoon)
    add_section("Night", night)

    doc.build(elements)

    return send_file("pill_schedule.pdf", as_attachment=True)

init_db()

    
# ---------------- RUN ----------------

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)





