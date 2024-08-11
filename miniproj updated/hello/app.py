from flask import Flask, flash, render_template, redirect, url_for, request, session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key
app.config['MONGO_URI'] = 'mongodb://localhost:27017/patient_queue'
mongo = PyMongo(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = mongo.db.users.find_one({"username": username, "password": password})
        if user and (user['role'] == 'patient' or user['approved']):
            session['username'] = username
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            elif user['role'] == 'patient':
                return redirect(url_for('patient_dashboard'))
        flash('Invalid credentials or account not approved.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if mongo.db.users.find_one({"username": username}):
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        approved = False if role != 'patient' else True
        mongo.db.users.insert_one({"username": username, "password": password, "role": role, "approved": approved})
        if role == 'patient':
            flash('Registration successful. Awaiting admin approval.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Registration successful. Awaiting admin approval.', 'info')
            return redirect(url_for('admin_dashboard'))
    return render_template('register.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
@app.route('/login', methods=['GET', 'POST'])
def login():
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')


@app.route('/admin/manage_users')
def manage_users():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    pending_users = list(mongo.db.users.find({"approved": False}))
    doctors = list(mongo.db.users.find({"role": "doctor", "approved": True}))
    patients = list(mongo.db.users.find({"role": "patient", "approved": True}))

    return render_template('manage_users.html', pending_users=pending_users, doctors=doctors, patients=patients)

@app.route('/admin/approve_user/<username>')
def approve_user(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    mongo.db.users.update_one({"username": username}, {"$set": {"approved": True}})
    flash('User approved successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/delete_user/<username>')
def delete_user(username):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    mongo.db.users.delete_one({"username": username})
    flash('User deleted successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    username = session['username']
    appointments = mongo.db.appointments.find({"doctor_username": username})
    return render_template('doctor_dashboard.html', appointments=appointments, username=username)

@app.route('/doctor/view_patient/<patient_username>')
def view_patient_profile(patient_username):
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    patient = mongo.db.users.find_one({"username": patient_username})
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    return render_template('view_patient_profile.html', patient=patient)
    
@app.route('/doctor/profile', methods=['GET', 'POST'])
def doctor_profile():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        qualification = request.form['qualification']
        branch = request.form['branch']
        phone_number = request.form['phone_number']
        available_time = request.form['available_time']

        mongo.db.users.update_one(
            {"username": session['username']},
            {"$set": {
                "name": name,
                "age": age,
                "qualification": qualification,
                "branch": branch,
                "phone_number": phone_number,
                "available_time": available_time
            }}
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))

    doctor = mongo.db.users.find_one({"username": session['username']})
    return render_template('doctor_profile.html', doctor=doctor)

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'username' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    if request.method == 'POST':
        doctor_username = request.form['doctor']
        appointment_date = request.form['date']
        appointment_time = request.form['time']

        # Fetch doctor's available timings and branch from the database
        doctor = mongo.db.users.find_one({"username": doctor_username})
        if not doctor:
            flash('Doctor not found.', 'danger')
            return redirect(url_for('book_appointment'))

        available_times = doctor.get('available_time', "")
        if not check_availability(available_times, appointment_date, appointment_time):
            flash('Doctor is not available at the selected time. Please choose a different time.', 'danger')
            return redirect(url_for('book_appointment'))

        room_number = random.randint(100, 999)
        existing_appointment = mongo.db.appointments.find_one({
            "doctor_username": doctor_username,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time
        })
        if existing_appointment:
            flash('This time slot is already booked. Please choose a different time.', 'danger')
            return redirect(url_for('book_appointment'))

        mongo.db.appointments.insert_one({
            "patient_username": session['username'],
            "doctor_username": doctor_username,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "room_number": room_number,
            "status": "Pending"  # Default status
        })

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient_dashboard'))

    doctors = mongo.db.users.find({"role": "doctor"})
    return render_template('book_appointment.html', doctors=doctors)

def check_availability(available_times, appointment_date, appointment_time):
    time_slots = available_times.split(',')
    for slot in time_slots:
        start_time, end_time = slot.split('-')
        if start_time <= appointment_time <= end_time:
            return True
    return False


@app.route('/doctor/manage_appointments')
def manage_appointments():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    doctor_username = session['username']
    appointments = mongo.db.appointments.find({"doctor_username": doctor_username})

    return render_template('manage_appointments.html', appointments=appointments, username=doctor_username)

@app.route('/doctor/appointment_action/<appointment_id>/<action>')
def appointment_action(appointment_id, action):
    if 'username' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))

    if action not in ['accept', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('manage_appointments'))

    result = mongo.db.appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {"status": action.capitalize()}}
    )

    if result.modified_count:
        flash(f'Appointment {action.capitalize()}ed successfully!', 'success')

    return redirect(url_for('manage_appointments'))

@app.route('/patient/dashboard', methods=['GET', 'POST'])
def patient_dashboard():
    if 'username' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    if request.method == 'POST':
        doctor_username = request.form['doctor']
        appointment_date = request.form['date']
        appointment_time = request.form['time']
        room_number = random.randint(100, 999)

        existing_appointment = mongo.db.appointments.find_one({
            "doctor_username": doctor_username,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time
        })
        if existing_appointment:
            flash('This time slot is already booked. Please choose a different time.', 'danger')
            return redirect(url_for('patient_dashboard'))

        mongo.db.appointments.insert_one({
            "patient_username": session['username'],
            "doctor_username": doctor_username,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "room_number": room_number,
            "status": "Pending"  # Default status
        })

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient_dashboard'))

    doctors = mongo.db.users.find({"role": "doctor"})
    return render_template('patient_dashboard.html', doctors=doctors, username=session['username'])

@app.route('/emergency_appointment', methods=['GET', 'POST'])
def emergency_appointment():
    if 'username' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    if request.method == 'POST':
        doctor_username = request.form.get('doctor')
        appointment_date = request.form.get('date')
        appointment_time = datetime.now().strftime("%H:%M")  # Current time in HH:MM format
        room_number = random.randint(100, 999)

        doctor = mongo.db.users.find_one({"username": doctor_username})
        if doctor:
            available_times = doctor.get('available_time', "")

            if not check_availability(available_times, appointment_date, appointment_time):
                flash('Doctor is not available at this time. Please choose another time.', 'danger')
                return redirect(url_for('emergency_appointment'))

            existing_appointment = mongo.db.appointments.find_one({
                "doctor_username": doctor_username,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time
            })
            if existing_appointment:
                flash('This time slot is already booked. Please choose a different time.', 'danger')
                return redirect(url_for('emergency_appointment'))

            appointment = {
                "patient_username": session['username'],
                "doctor_username": doctor_username,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "room_number": room_number,
                "appointment_type": "emergency_case",
                "status": "confirmed"
            }

            mongo.db.appointments.insert_one(appointment)

            flash('Emergency appointment booked successfully!', 'success')
            return redirect(url_for('patient_dashboard'))

        else:
            flash('Doctor not found.', 'danger')
            return redirect(url_for('emergency_appointment'))

    doctors = mongo.db.users.find({"role": "doctor"})
    return render_template('emergency_appointment.html', doctors=doctors)

def check_availability(available_times, appointment_date, appointment_time):
    time_slots = available_times.split(',')
    for slot in time_slots:
        start_time, end_time = slot.split('-')
        if start_time <= appointment_time <= end_time:
            return True
    return False

@app.route('/patient/profile', methods=['GET', 'POST'])
def patient_profile():
    if 'username' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        medical_history = request.form['medical_history']
        phone_number = request.form['phone_number']
        address = request.form['address']
        area_of_living = request.form['area_of_living']

        mongo.db.users.update_one(
            {"username": session['username']},
            {"$set": {
                "name": name,
                "age": age,
                "gender": gender,
                "blood_group": blood_group,
                "medical_history": medical_history,
                "phone_number": phone_number,
                "address": address,
                "area_of_living": area_of_living
            }}
        )
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient_dashboard'))

    patient = mongo.db.users.find_one({"username": session['username']})
    return render_template('patient_profile.html', patient=patient)

@app.route('/patient/view_appointments')
def view_appointments():
    if 'username' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))

    patient_username = session['username']
    appointments = mongo.db.appointments.find({"patient_username": patient_username})

    return render_template('view_appointments.html', appointments=appointments, username=patient_username)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
