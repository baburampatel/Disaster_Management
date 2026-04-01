from flask import Flask, render_template, request, redirect, session, flash
import bcrypt
import datetime
import pickle
import sqlite3
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from init_db import init_database

# ================= PATHS =================
BASE_DIR = project_root
DB_PATH = os.path.join('/tmp', 'disaster.db')

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = "secret123"

# ================= DATABASE HELPERS =================
def get_db():
    db = sqlite3.connect(DB_PATH)
    return db

# Initialize DB on startup
init_database(DB_PATH)

# ================= LOAD AI MODEL =================
try:
    model_path = os.path.join(BASE_DIR, "model.pkl")
    model = pickle.load(open(model_path, "rb"))
except:
    model = None


# =================================================
# LOGIN
# =================================================
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=?",(email,))
        user = cur.fetchone()
        db.close()

        if not user:
            flash("Email does not exist")
            return redirect('/')

        if not bcrypt.checkpw(password.encode(), user[3].encode()):
            flash("Incorrect password")
            return redirect('/')

        session['user_id'] = user[0]
        session['role'] = user[4]

        db = get_db()
        cur = db.cursor()
        cur.execute(
            "UPDATE users SET last_login=? WHERE id=?",
            (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user[0])
        )
        db.commit()
        db.close()

        if user[4] == "admin":
            return redirect('/admin')
        else:
            return redirect('/user')

    return render_template("login.html")


# =================================================
# REGISTER
# =================================================
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        db = get_db()
        cur = db.cursor()

        cur.execute("SELECT id FROM users WHERE email=?",(email,))
        if cur.fetchone():
            flash("Email already registered")
            db.close()
            return redirect('/register')

        cur.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,'user')",
            (name,email,hashed_pw)
        )
        db.commit()
        db.close()
        return redirect('/')

    return render_template("register.html")


# =================================================
# USER DASHBOARD
# =================================================
@app.route('/user')
def user_dashboard():
    if 'user_id' not in session:
        return redirect('/')

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    SELECT disaster_type, ROUND(AVG((score*1.0/total)*100),2)
    FROM disaster_scores WHERE user_id=? GROUP BY disaster_type
    """,(session['user_id'],))
    data = cur.fetchall()

    score_map = {}
    for d in data:
        score_map[d[0]] = float(d[1])

    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details")
    all_disasters = [d[0] for d in cur.fetchall()]

    disasters=[]
    percentages=[]
    for d in all_disasters:
        disasters.append(d)
        percentages.append(score_map.get(d,0))

    recommendation=None
    if percentages:
        min_score=min(percentages)
        recommendation=disasters[percentages.index(min_score)]

    cur.execute("""
    SELECT id,message,admin_reply FROM feedback
    WHERE user_id=? AND admin_reply IS NOT NULL
    """,(session['user_id'],))
    notifications=cur.fetchall()
    db.close()

    return render_template(
        "user_dashboard.html",
        disasters=disasters, percentages=percentages,
        recommendation=recommendation, notifications=notifications
    )


# =================================================
# DELETE NOTIFICATION
# =================================================
@app.route('/delete-notification/<int:id>')
def delete_notification(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE feedback SET admin_reply=NULL WHERE id=?",(id,))
    db.commit()
    db.close()
    return redirect('/user')


# =================================================
# FEEDBACK
# =================================================
@app.route('/feedback-page',methods=['GET','POST'])
def feedback_page():
    if 'user_id' not in session:
        return redirect('/')

    if request.method=="POST":
        msg=request.form['message']
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO feedback (user_id,message) VALUES (?,?)",
                    (session['user_id'],msg))
        db.commit()
        db.close()
        flash("Feedback submitted")

    return render_template("feedback.html")


# =================================================
# ADMIN DASHBOARD
# =================================================
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['role']!='admin':
        return redirect('/')

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT id,name,email,last_login FROM users WHERE role='user'")
    users=cur.fetchall()

    cur.execute("""
    SELECT f.id,u.name,f.message,f.admin_reply FROM feedback f
    JOIN users u ON f.user_id=u.id WHERE f.admin_reply IS NULL
    """)
    feedbacks=cur.fetchall()

    cur.execute("""
    SELECT u.name,s.disaster_type,s.exercise_number,s.score,s.total,s.taken_at
    FROM disaster_scores s JOIN users u ON s.user_id=u.id
    """)
    scores=cur.fetchall()

    cur.execute("""
    SELECT d.disaster_type, COALESCE(ROUND(AVG((s.score*1.0/s.total)*100),2),0)
    FROM disaster_details d LEFT JOIN disaster_scores s
    ON d.disaster_type=s.disaster_type GROUP BY d.disaster_type
    """)
    analytics=cur.fetchall()
    analytics_labels=[a[0] for a in analytics]
    analytics_values=[float(a[1]) for a in analytics]
    db.close()

    return render_template(
        "admin_dashboard.html",
        users=users, feedbacks=feedbacks, scores=scores,
        analytics_labels=analytics_labels, analytics_values=analytics_values
    )


# =================================================
# ADMIN REPLY
# =================================================
@app.route('/reply/<int:id>',methods=['POST'])
def reply(id):
    reply_text=request.form['reply']
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE feedback SET admin_reply=? WHERE id=?",(reply_text,id))
    db.commit()
    db.close()
    return redirect('/admin')


# =================================================
# DELETE USER
# =================================================
@app.route('/delete-user/<int:id>')
def delete_user(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM disaster_scores WHERE user_id=?",(id,))
    cur.execute("DELETE FROM feedback WHERE user_id=?",(id,))
    cur.execute("DELETE FROM users WHERE id=?",(id,))
    db.commit()
    db.close()
    return redirect('/admin')


# =================================================
# RESET PASSWORD
# =================================================
@app.route('/reset-password/<int:id>',methods=['POST'])
def reset_password(id):
    new_password=request.form['password']
    hashed=bcrypt.hashpw(new_password.encode(),bcrypt.gensalt()).decode()
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE users SET password=? WHERE id=?",(hashed,id))
    db.commit()
    db.close()
    return redirect('/admin')


# =================================================
# GENERAL DISASTERS
# =================================================
@app.route('/general')
def general_disasters():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details")
    disasters=cur.fetchall()
    db.close()
    return render_template("general_disasters.html",disasters=disasters)


# =================================================
# CONTINENTS
# =================================================
@app.route('/continents')
def continents():
    continents=["Asia","Africa","Europe","North America","South America","Australia","Antarctica"]
    return render_template("continents.html",continents=continents)


# =================================================
# CONTINENT DISASTERS
# =================================================
@app.route('/continent/<continent>')
def continent_disasters(continent):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details WHERE continent=?",(continent,))
    disasters=cur.fetchall()
    db.close()
    return render_template("continent_disasters.html",continent=continent,disasters=disasters)


# =================================================
# INDIA STATES
# =================================================
@app.route('/india')
def india_states():
    states=[
    "Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh",
    "Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand",
    "Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur",
    "Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
    "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura",
    "Uttar Pradesh","Uttarakhand","West Bengal"
    ]
    return render_template("india_states.html",states=states)


# =================================================
# STATE DISASTERS
# =================================================
@app.route('/india/<state>')
def state_disasters(state):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details WHERE state=?",(state,))
    disasters=cur.fetchall()
    db.close()
    return render_template("state_disasters.html",state=state,disasters=disasters)


# =================================================
# SIMULATION DETAILS
# =================================================
@app.route('/simulation/<disaster>')
def disaster_details_page(disaster):
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    SELECT description,causes,impacts,case_study,lessons,dos,donts
    FROM disaster_details WHERE disaster_type=?
    """,(disaster,))
    details=cur.fetchone()
    db.close()
    return render_template("disaster_details.html",disaster=disaster,details=details)


# =================================================
# EXERCISE SELECT
# =================================================
@app.route('/simulation/<disaster>/exercises')
def exercise_list(disaster):
    return render_template("exercise_select.html",disaster=disaster)


# =================================================
# EXERCISE QUESTIONS
# =================================================
@app.route('/simulation/<disaster>/exercise/<int:exercise>',methods=['GET','POST'])
def simulation_exercise(disaster,exercise):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM disaster_questions WHERE disaster_type=? AND exercise_number=?",
                (disaster,exercise))
    questions=cur.fetchall()

    if request.method=="POST":
        score=0
        total=len(questions)
        review=[]
        for q in questions:
            user_answer=request.form.get(str(q[0]))
            correct=q[7]
            if user_answer==correct:
                score+=1
                status="correct"
            else:
                status="wrong"
            review.append({
                "question":q[2],"user_answer":user_answer,
                "correct_answer":correct,"status":status
            })

        cur.execute("""
        INSERT INTO disaster_scores (user_id,disaster_type,exercise_number,score,total)
        VALUES (?,?,?,?,?)
        """,(session['user_id'],disaster,exercise,score,total))
        db.commit()
        db.close()

        return render_template("result.html",disaster=disaster,
                               score=score,total=total,review=review)

    db.close()
    return render_template("exercise_questions.html",disaster=disaster,
                           exercise=exercise,questions=questions)


# =================================================
# LOGOUT
# =================================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# =================================================
# RUN (local dev only)
# =================================================
if __name__=="__main__":
    app.run(debug=True)
