from flask import Flask, render_template, request, redirect, session, flash
import bcrypt
import datetime
import pickle
import sqlite3
import os
from functools import wraps
from init_db import init_database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'disaster.db')

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = "disasterguard_secret_2026"
app.jinja_env.globals.update(zip=zip, min=min, max=max, round=round, int=int)

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

init_database(DB_PATH)

try:
    model = pickle.load(open(os.path.join(BASE_DIR, "model.pkl"), "rb"))
except:
    model = None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        db  = get_db(); cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone(); db.close()
        if not user:
            flash("Email does not exist", "error"); return redirect('/')
        if not bcrypt.checkpw(password.encode(), user['password'].encode()):
            flash("Incorrect password", "error"); return redirect('/')
        session['user_id']   = user['id']
        session['role']      = user['role']
        session['user_name'] = user['name']
        db = get_db(); cur = db.cursor()
        cur.execute("UPDATE users SET last_login=? WHERE id=?",
                    (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user['id']))
        db.commit(); db.close()
        return redirect('/admin' if user['role'] == 'admin' else '/user')
    return render_template("login.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == "POST":
        name = request.form['name']; email = request.form['email']; password = request.form['password']
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db = get_db(); cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        if cur.fetchone():
            flash("Email already registered","error"); db.close(); return redirect('/register')
        cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,'user')",(name,email,hashed))
        db.commit(); db.close()
        flash("Account created! Please login.","success"); return redirect('/')
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

@app.route('/home')
def home():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE role='user'"); user_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM incident_reports"); incident_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM disaster_details"); disaster_count = cur.fetchone()[0]
    cur.execute("SELECT * FROM alerts WHERE is_active=1 ORDER BY created_at DESC LIMIT 3")
    recent_alerts = cur.fetchall(); db.close()
    return render_template('home.html', user_count=user_count,
                           incident_count=incident_count, disaster_count=disaster_count,
                           recent_alerts=recent_alerts)

@app.route('/user')
@login_required
def user_dashboard():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT disaster_type, ROUND(AVG((score*1.0/total)*100),2) FROM disaster_scores WHERE user_id=? GROUP BY disaster_type", (session['user_id'],))
    score_map = {r[0]: float(r[1]) for r in cur.fetchall()}
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details")
    all_disasters = [d[0] for d in cur.fetchall()]
    disasters, percentages = [], []
    for d in all_disasters:
        disasters.append(d); percentages.append(score_map.get(d, 0))
    recommendation = weak_topic = next_exercise = None; learning_path = []
    if percentages:
        idx = percentages.index(min(percentages))
        recommendation = weak_topic = disasters[idx]
        cur.execute("SELECT DISTINCT exercise_number FROM disaster_scores WHERE user_id=? AND disaster_type=?", (session['user_id'], weak_topic))
        done_ex = [r[0] for r in cur.fetchall()]
        nex = 1
        while nex in done_ex: nex += 1
        if nex <= 3: next_exercise = {'disaster': weak_topic, 'exercise': nex}
        learning_path = [{'disaster': d, 'score': round(s, 1)} for d, s in sorted(zip(disasters, percentages), key=lambda x: x[1])[:3]]
    cur.execute("SELECT id,message,admin_reply FROM feedback WHERE user_id=? AND admin_reply IS NOT NULL AND admin_reply != '[Ignored]'", (session['user_id'],))
    notifications = cur.fetchall()
    cur.execute("SELECT name FROM users WHERE id=?", (session['user_id'],))
    row = cur.fetchone(); user_name = row[0] if row else 'User'
    db.close()
    return render_template("user_dashboard.html", disasters=disasters, percentages=percentages,
                           recommendation=recommendation, notifications=notifications,
                           weak_topic=weak_topic, next_exercise=next_exercise,
                           learning_path=learning_path, user_name=user_name)

@app.route('/delete-notification/<int:id>')
@login_required
def delete_notification(id):
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE feedback SET admin_reply=NULL WHERE id=?", (id,))
    db.commit(); db.close(); return redirect('/user')

@app.route('/feedback-page', methods=['GET','POST'])
@login_required
def feedback_page():
    if request.method == "POST":
        db = get_db(); cur = db.cursor()
        cur.execute("INSERT INTO feedback (user_id,message) VALUES (?,?)",(session['user_id'],request.form['message']))
        db.commit(); db.close(); flash("Feedback submitted","success")
    return render_template("feedback.html")

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT id,name,email,last_login FROM users WHERE role='user'"); users = cur.fetchall()
    cur.execute("SELECT f.id,u.name,f.message,f.admin_reply FROM feedback f JOIN users u ON f.user_id=u.id WHERE f.admin_reply IS NULL"); feedbacks = cur.fetchall()
    cur.execute("SELECT u.name,s.disaster_type,s.exercise_number,s.score,s.total,s.taken_at FROM disaster_scores s JOIN users u ON s.user_id=u.id ORDER BY s.taken_at DESC"); scores = cur.fetchall()
    cur.execute("SELECT d.disaster_type,COALESCE(ROUND(AVG((s.score*1.0/s.total)*100),2),0) FROM disaster_details d LEFT JOIN disaster_scores s ON d.disaster_type=s.disaster_type GROUP BY d.disaster_type"); analytics = cur.fetchall()
    analytics_labels = [a[0] for a in analytics]; analytics_values = [float(a[1]) for a in analytics]
    cur.execute("SELECT COUNT(*) FROM users WHERE last_login >= datetime('now','-7 days') AND role='user'"); active_users = cur.fetchone()[0]
    weak_categories = [a[0] for a in analytics if float(a[1]) < 60]
    cur.execute("SELECT COUNT(*) FROM alerts WHERE is_active=1"); active_alerts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM incident_reports WHERE status='pending'"); pending_incidents = cur.fetchone()[0]
    db.close()
    return render_template("admin_dashboard.html", users=users, feedbacks=feedbacks, scores=scores,
                           analytics_labels=analytics_labels, analytics_values=analytics_values,
                           total_users=len(users), active_users=active_users,
                           pending_feedback=len(feedbacks), quiz_count=len(scores),
                           weak_categories=weak_categories, active_alerts=active_alerts,
                           pending_incidents=pending_incidents)

@app.route('/reply/<int:id>', methods=['POST'])
@admin_required
def reply(id):
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE feedback SET admin_reply=? WHERE id=?",(request.form['reply'],id))
    db.commit(); db.close(); return redirect('/admin')

@app.route('/ignore-feedback/<int:id>')
@admin_required
def ignore_feedback(id):
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE feedback SET admin_reply='[Ignored]' WHERE id=?",(id,))
    db.commit(); db.close(); return redirect('/admin')

@app.route('/delete-user/<int:id>')
@admin_required
def delete_user(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM disaster_scores WHERE user_id=?",(id,))
    cur.execute("DELETE FROM feedback WHERE user_id=?",(id,))
    cur.execute("DELETE FROM users WHERE id=?",(id,))
    db.commit(); db.close(); return redirect('/admin')

@app.route('/reset-password/<int:id>', methods=['POST'])
@admin_required
def reset_password(id):
    hashed = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt()).decode()
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE users SET password=? WHERE id=?",(hashed,id))
    db.commit(); db.close(); return redirect('/admin')

@app.route('/general')
@login_required
def general_disasters():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details"); disasters = cur.fetchall(); db.close()
    return render_template("general_disasters.html", disasters=disasters)

@app.route('/continents')
@login_required
def continents():
    return render_template("continents.html", continents=["Asia","Africa","Europe","North America","South America","Australia","Antarctica"])

@app.route('/continent/<continent>')
@login_required
def continent_disasters(continent):
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details WHERE continent=?",(continent,)); disasters = cur.fetchall(); db.close()
    return render_template("continent_disasters.html", continent=continent, disasters=disasters)

@app.route('/india')
@login_required
def india_states():
    states = ["Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat",
              "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
              "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab",
              "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal"]
    return render_template("india_states.html", states=states)

@app.route('/india/<state>')
@login_required
def state_disasters(state):
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details WHERE state=?",(state,)); disasters = cur.fetchall(); db.close()
    return render_template("state_disasters.html", state=state, disasters=disasters)

@app.route('/simulation/<disaster>')
@login_required
def disaster_details_page(disaster):
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT description,causes,impacts,case_study,lessons,dos,donts FROM disaster_details WHERE disaster_type=?",(disaster,)); details = cur.fetchone()
    cur.execute("SELECT warning_signs,safety_kit,myths_facts,region_tips FROM disaster_articles WHERE disaster_type=?",(disaster,)); article = cur.fetchone()
    db.close()
    return render_template("disaster_details.html", disaster=disaster, details=details, article=article)

@app.route('/simulation/<disaster>/exercises')
@login_required
def exercise_list(disaster):
    return render_template("exercise_select.html", disaster=disaster)

@app.route('/simulation/<disaster>/exercise/<int:exercise>', methods=['GET','POST'])
@login_required
def simulation_exercise(disaster, exercise):
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM disaster_questions WHERE disaster_type=? AND exercise_number=?",(disaster,exercise)); questions = cur.fetchall()
    if request.method == "POST":
        score = 0; total = len(questions); review = []
        for q in questions:
            user_answer = request.form.get(str(q['id'])); correct = q['correct_answer']
            status = "correct" if user_answer == correct else "wrong"
            if status == "correct": score += 1
            review.append({"question":q['question'],"user_answer":user_answer,"correct_answer":correct,"status":status})
        cur.execute("INSERT INTO disaster_scores (user_id,disaster_type,exercise_number,score,total) VALUES (?,?,?,?,?)",(session['user_id'],disaster,exercise,score,total))
        db.commit(); db.close()
        return render_template("result.html",disaster=disaster,score=score,total=total,review=review)
    db.close()
    return render_template("exercise_questions.html",disaster=disaster,exercise=exercise,questions=questions)

@app.route('/disaster-library')
@login_required
def disaster_library():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT disaster_type,description,continent,state FROM disaster_details GROUP BY disaster_type"); disasters = cur.fetchall(); db.close()
    return render_template("disaster_library.html", disasters=disasters)

@app.route('/disaster/<disaster_type>/guide')
@login_required
def disaster_guide(disaster_type):
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM disaster_details WHERE disaster_type=? LIMIT 1",(disaster_type,)); details = cur.fetchone()
    cur.execute("SELECT * FROM disaster_articles WHERE disaster_type=? LIMIT 1",(disaster_type,)); article = cur.fetchone()
    cur.execute("SELECT name,number,category FROM emergency_contacts WHERE category IN ('national','disaster','medical') LIMIT 6"); contacts = cur.fetchall()
    db.close()
    return render_template("disaster_guide.html", disaster=disaster_type, details=details, article=article, contacts=contacts)

@app.route('/alerts')
@login_required
def alerts_page():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM alerts WHERE is_active=1 ORDER BY created_at DESC"); alerts = cur.fetchall(); db.close()
    return render_template("alerts.html", alerts=alerts)

@app.route('/emergency-contacts')
@login_required
def emergency_contacts():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM emergency_contacts ORDER BY category, name"); contacts = cur.fetchall(); db.close()
    return render_template("emergency_contacts.html", contacts=contacts)

@app.route('/shelters')
@login_required
def shelters():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM shelters ORDER BY is_active DESC, state"); shelter_list = cur.fetchall(); db.close()
    return render_template("shelters.html", shelters=shelter_list)

@app.route('/report-incident', methods=['GET','POST'])
@login_required
def report_incident():
    if request.method == 'POST':
        db = get_db(); cur = db.cursor()
        cur.execute("INSERT INTO incident_reports (user_id,incident_type,location,description,severity,contact_number) VALUES (?,?,?,?,?,?)",
                    (session['user_id'],request.form['incident_type'],request.form['location'],request.form['description'],request.form['severity'],request.form.get('contact_number','')))
        db.commit(); db.close()
        flash("Incident reported successfully. Authorities have been notified.","success"); return redirect('/report-incident')
    return render_template("report_incident.html")

@app.route('/preparedness-checklist')
@login_required
def preparedness_checklist():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM preparedness_checklists ORDER BY category, priority DESC, item"); items = cur.fetchall()
    checklist = {}
    for item in items:
        cat = item['category']
        if cat not in checklist: checklist[cat] = []
        checklist[cat].append(item)
    db.close()
    return render_template("preparedness_checklist.html", checklist=checklist)

@app.route('/training')
@login_required
def training():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT DISTINCT disaster_type FROM disaster_details"); disasters = [d[0] for d in cur.fetchall()]
    cur.execute("SELECT disaster_type,exercise_number,ROUND(MAX(score*1.0/total*100),1) FROM disaster_scores WHERE user_id=? GROUP BY disaster_type,exercise_number",(session['user_id'],))
    completed = {(r[0],r[1]):r[2] for r in cur.fetchall()}; db.close()
    return render_template("training.html", disasters=disasters, completed=completed)

@app.route('/admin/content-manager')
@admin_required
def admin_content_manager():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT * FROM alerts ORDER BY created_at DESC"); alerts = cur.fetchall()
    cur.execute("SELECT * FROM emergency_contacts ORDER BY category, name"); contacts = cur.fetchall()
    cur.execute("SELECT id,incident_type,location,severity,status,reported_at FROM incident_reports ORDER BY reported_at DESC"); incidents = cur.fetchall()
    db.close()
    return render_template("admin_content_manager.html", alerts=alerts, contacts=contacts, incidents=incidents)

@app.route('/admin/add-alert', methods=['POST'])
@admin_required
def admin_add_alert():
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO alerts (title,message,severity,location) VALUES (?,?,?,?)",
                (request.form['title'],request.form['message'],request.form['severity'],request.form.get('location','')))
    db.commit(); db.close(); flash("Alert published.","success"); return redirect('/admin/content-manager')

@app.route('/admin/delete-alert/<int:id>')
@admin_required
def admin_delete_alert(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM alerts WHERE id=?",(id,)); db.commit(); db.close(); return redirect('/admin/content-manager')

@app.route('/admin/add-contact', methods=['POST'])
@admin_required
def admin_add_contact():
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO emergency_contacts (name,number,category,description,region) VALUES (?,?,?,?,?)",
                (request.form['name'],request.form['number'],request.form['category'],request.form.get('description',''),request.form.get('region','All India')))
    db.commit(); db.close(); flash("Contact added.","success"); return redirect('/admin/content-manager')

@app.route('/admin/delete-contact/<int:id>')
@admin_required
def admin_delete_contact(id):
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM emergency_contacts WHERE id=?",(id,)); db.commit(); db.close(); return redirect('/admin/content-manager')

@app.route('/admin/update-incident/<int:id>', methods=['POST'])
@admin_required
def update_incident_status(id):
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE incident_reports SET status=? WHERE id=?",(request.form['status'],id))
    db.commit(); db.close(); return redirect('/admin/content-manager')

@app.route('/admin/analytics-expanded')
@admin_required
def admin_analytics_expanded():
    db = get_db(); cur = db.cursor()
    cur.execute("SELECT d.disaster_type,COALESCE(ROUND(AVG((s.score*1.0/s.total)*100),2),0),COUNT(DISTINCT s.user_id) FROM disaster_details d LEFT JOIN disaster_scores s ON d.disaster_type=s.disaster_type GROUP BY d.disaster_type"); disaster_stats = cur.fetchall()
    cur.execute("SELECT u.name,s.disaster_type,s.exercise_number,s.score,s.total,s.taken_at FROM disaster_scores s JOIN users u ON s.user_id=u.id ORDER BY s.taken_at DESC LIMIT 15"); recent_activity = cur.fetchall()
    cur.execute("SELECT DATE(taken_at),COUNT(*) FROM disaster_scores WHERE taken_at >= datetime('now','-7 days') GROUP BY DATE(taken_at) ORDER BY DATE(taken_at)"); daily_activity = cur.fetchall()
    db.close()
    return render_template("admin_analytics.html", disaster_stats=disaster_stats, recent_activity=recent_activity, daily_activity=daily_activity)

if __name__ == "__main__":
    app.run(debug=True)


