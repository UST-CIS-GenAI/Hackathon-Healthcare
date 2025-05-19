import os
import random
import base64
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify,send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import csv
from openai import AzureOpenAI  # For SDK v1+
import openai
import json
import time
import threading
from fpdf import FPDF
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import uuid
import re
from datetime import datetime, timedelta
from llm_utils import generate_dynamic_questions


scheduler = BackgroundScheduler()
scheduler.start()



client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-05-01-preview",
    azure_endpoint=os.getenv("OPENAI_ENDPOINT")
)

DEPLOYMENT_NAME = os.getenv("OPENAI_DEPLOYMENT")

app = Flask(__name__)



CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

patient_data = {
    "heart_rate": 0,
    "bp_systolic": 0,
    "bp_diastolic": 0,
    "sleep_hours": 0,
    "temperature": 98.6  # Default temperature
}

SEVERE_SYMPTOMS = [
    "chest pain",
    "shortness of breath",
    "severe headache",
    "dizziness",
    "unconsciousness"
   ]
 
# Globals
patient_data = {}
sleeping = False
sleep_hours = 0.0
last_emit_time = time.time()
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#Allow OPTIONS method for preflight
@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response
 
def fetch_hospital_summary(file_path="hospital_summary.json"):
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            return data.get("summary", "No summary found.")
    except Exception as e:
        return f"Error loading summary: {e}"

def fetch_medical_data(patient_id=None):
    return "BP: 135/85 mmHg, HR: 90 bpm, Temp: 98.6°F"

def load_hospital_data():
    file_path = os.path.join(os.path.dirname(__file__), 'hospital_data.json')
    with open(file_path, 'r') as f:
        return json.load(f)


def generate_pdf(questions, answers, filepath):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Prescreening Answers", ln=True, align='C')

    for i, ans in enumerate(answers):
        question = questions[i] if i < len(questions) else f"Question {i+1}"
        pdf.cell(200, 10, txt=f"Q{i+1}: {question}", ln=True)
        pdf.cell(200, 10, txt=f"Answer: {ans}", ln=True)

    pdf.output(filepath)
    print("[✓] PDF generated:", filepath)

def get_hospital_data(file_path="hospital_data.json"):
    with open(file_path, "r") as file:
        hospital_data = json.load(file)
    return hospital_data

def save_session_log(questions, answers, filepath="session_logs.json"):
    session = {
        "timestamp": datetime.now().isoformat(),
        "questions": questions,
        "answers": answers
    }

    # Read existing log file if it exists
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                log_data = []
    else:
        log_data = []

    # Append new session
    log_data.append(session)

    # Write updated log
    with open(filepath, "w") as f:
        json.dump(log_data, f, indent=2)


# Step 1: Symptom Classification (Urgent vs. Non-Urgent)
def classify_symptom(symptom,vitals):


    symptom = symptom.lower()
    hr = vitals.get('heart_rate', 0)
    temp_str = vitals.get('temperature', "98.6°F").replace("°F", "")
    bp = vitals.get('blood_pressure', "0/0")
 
    try:
        temp = float(temp_str)
        systolic, diastolic = map(int, bp.split('/'))
    except:
        temp = 98.6
        systolic, diastolic = 0, 0
 
    if symptom in SEVERE_SYMPTOMS:
        # Vital-based urgency check for all severe symptoms
        if hr > 110 or temp > 101 or systolic > 160 or systolic < 90 or diastolic > 100 or diastolic < 60:
            return "urgent"
        else:
            return "non-urgent"
 
    # Future: Add other symptom-specific rules here
 
    return "non-urgent"
 

# Step 2: Fetching Vitals (simulated for demo)
def fetch_vitals():
    # Get the latest patient data from the global variable
    global patient_data
   
    vitals = {
        "heart_rate": patient_data.get("heart_rate", 120),  # Use real-time heart rate
        "blood_pressure": f"{patient_data.get('bp_systolic', 140)}/{patient_data.get('bp_diastolic', 90)}",  # Use real BP
        "temperature": f"{patient_data.get('temperature', 98.6)}°F"  # Temperature
    }
    return vitals

# Step 3: Find Nearest Emergency Room (simulated with static data)
def find_nearest_emergency_room(location, hospital_data):
    if location not in hospital_data:
        return []  # No data for location
    hospitals = list(hospital_data[location].keys())
    return hospitals
# Symptom to department mapping
SYMPTOM_TO_DEPARTMENT = {
    "chest pain": "Cardiology",
    "shortness of breath": "Pulmonology",
    "severe headache": "Neurology",
    "dizziness": "Neurology",
    "unconsciousness": "Neurology",
    "fever": "Pediatrics",
    "rash": "Dermatology",
    "fracture": "Orthopedics"
}

# Pick hospital, department, doctor, and time slot
def choose_appointment_details(location, department, hospital_data):
    hospitals = hospital_data.get(location, {})
    for hospital_name, departments in hospitals.items():
        if department in departments:
            doctors = departments[department]
            for doctor_name, times in doctors.items():
                if times:
                    return hospital_name, doctor_name, times[0]  # First available time
    return None, None, None

# Enhanced urgent summary generator
def generate_summary_urgent(symptom, vitals, location="Kannur", hospital_data=None):
    if not location:
        location = "Kannur"

    if hospital_data is None:
        hospital_data = load_hospital_data()

    summary = f"Appointment confirmed.\n"
    summary += f"Your symptom '{symptom}' has been identified as potentially urgent.\n"
    summary += f"Vitals: Heart rate: {vitals['heart_rate']}, BP: {vitals['blood_pressure']}, Temp: {vitals['temperature']}\n"

    department = SYMPTOM_TO_DEPARTMENT.get(symptom.lower(), "General Medicine")

    hospital_name, doctor_name, time_slot = choose_appointment_details(location, department, hospital_data)

    if hospital_name and doctor_name and time_slot:
        summary += f"\n➡️ Appointment booked with **{doctor_name}** ({department}) at **{hospital_name}**.\n"
        summary += f"🕒 Time slot: {time_slot}\n"
    else:
        summary += f"\n⚠️ No available appointments in {location} for department: {department}\n"

    summary += "\nWe recommend you visit the hospital immediately. Please call 911 if needed.\n"

    return summary

# Step 5: Appointment Scheduling for Non-Urgent Cases (User Options)



# Step 6: Summary Generator for Non-Urgent Cases
def generate_summary_non_urgent(hospital_data, place, hospital, department, doctor, time):
    summary = (
        f"✅ Appointment confirmed:\n"
        f"📍 Place: {place}\n"
        f"🏥 Hospital: {hospital}\n"
        f"🧪 Department: {department}\n"
        f"👨‍⚕️ Doctor: {doctor}\n"
        f"⏰ Time: {time}"
    )
    return summary

# Main Endpoint: Handle Appointment Request
@app.route('/appointment', methods=['POST'])
def appointment():
    data = request.json
    answers = data.get('answers', [])
    hospital_data = get_hospital_data()

    # Handle first question: What is your symptom?
    if len(answers) == 0:
        return jsonify({
            "response": "What is your symptom?"
        })

    # Handle symptom selection
    if len(answers) == 1:
        symptom = answers[0]
        vitals = fetch_vitals()
        severity = classify_symptom(symptom, vitals)
        # Step 1: Symptom Classification (Urgent vs. Non-Urgent)
      

        if severity == "urgent":
            # Step 2: Vitals fetch
            vitals = fetch_vitals()
            location = "Kannur"  # You can use geo-location here if applicable
            # Step 3: Generate Summary for Urgent Care
            hospital_data = load_hospital_data()
            summary = generate_summary_urgent(symptom, vitals, location)
            return jsonify({
                "response": summary
            })
        
        else:
            # Non-urgent flow: Provide options for place selection
            return jsonify({
                "response": "Which place are you looking in?",
                "options": list(hospital_data.keys())  # List of places (e.g., cities)
            })

    # Handle place selection
    if len(answers) == 2:
        place = answers[1]
        if place not in hospital_data:
            return jsonify({"response": "Invalid place selected."})
        return jsonify({
            "response": f"Select a hospital in {place}:",
            "options": list(hospital_data[place].keys())  # List of hospitals in the place
        })

    # Handle hospital selection
    if len(answers) == 3:
        place = answers[1]
        hospital = answers[2]
        if hospital not in hospital_data.get(place, {}):
            return jsonify({"response": "Invalid hospital selected."})
        return jsonify({
            "response": f"Select a department in {hospital}:",
            "options": list(hospital_data[place][hospital].keys())  # List of departments in the hospital
        })

    # Handle department selection
    if len(answers) == 4:
        place, hospital, department = answers[1:4]
        if department not in hospital_data[place][hospital]:
            return jsonify({"response": "Invalid department selected."})
        return jsonify({
            "response": f"Select a doctor in {department}:",
            "options": list(hospital_data[place][hospital][department].keys())  # List of doctors in the department
        })

    # Handle doctor selection
    if len(answers) == 5:
        place, hospital, department, doctor = answers[1:5]
        if doctor not in hospital_data[place][hospital][department]:
            return jsonify({"response": "Invalid doctor selected."})
        return jsonify({
            "response": f"Select a time for {doctor}:",
            "options": hospital_data[place][hospital][department][doctor]  # List of times for the doctor
        })

    # Handle time selection
    if len(answers) == 6:
        place, hospital, department, doctor, time = answers[1:6]
        summary = generate_summary_non_urgent(hospital_data, place, hospital, department, doctor, time)
        return jsonify({"response": summary})

    return jsonify({"response": "Invalid step."})


@app.route('/prescreening', methods=['POST'])
def prescreening():
    data = request.json
    answers = data.get("answers", [])
    question_set = data.get("question_set", [])
    symptom = data.get("symptom", "")

    # Step 1: Start with initial question
    if not answers:
        return jsonify({
            "response": "How are you feeling today?",
            "question_set": question_set
        })

    # Step 2: Generate dynamic questions only once
    if not question_set:
        hospital_summary = fetch_hospital_summary()
        medical_data = fetch_medical_data()
        symptom = answers[0]
        question_set = generate_dynamic_questions(symptom, hospital_summary, medical_data)

    # Step 3: Continue asking questions
    if len(answers) < len(question_set):
        next_question = question_set[len(answers)]
        return jsonify({
            "response": next_question,
            "question_set": question_set
        })

    # Step 4: All questions answered, generate the PDF + log the session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prescreening_{timestamp}.pdf"
    filepath = os.path.join("uploads", filename)

    # Function to create PDF and log the session
    def create_pdf():
        generate_pdf(question_set, answers, filepath)
        save_session_log(question_set, answers)

    # Run the PDF generation and logging in a background thread
    threading.Thread(target=create_pdf).start()

    file_url = f"http://localhost:5000/uploads/{filename}"
    return jsonify({
        "response": f"Prescreening completed. [📄 Download PDF]({file_url})",
        "file_url": file_url
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)



@app.route('/ask-question', methods=['POST'])
def ask_question():
    print("🚨 Request received at /ask-question")

    if 'file' not in request.files:
        return jsonify({"error": "File is required"}), 400

    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        with open(file_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        prompt = (
            "This is an image of a medical bill. Please carefully read and extract all items from the table. "
            "For each line item, give a clear, patient-friendly explanation that includes:\n"
            "- The medicine name\n"
            "- What it's commonly used for\n"
            "- Its dose or form (e.g., tablet, syrup, injection)\n"
            "- Any helpful usage info if known\n"
            "- MRP, quantity, and total amount charged\n\n"
            "Then summarize the total bill: subtotal, discounts, VAT, freight, insurance, and grand total — "
            "with clear meaning of each.\n\n"
            "If a medicine name is unclear, make your best guess based on known drugs. Avoid making up values. "
            "Be very clear and helpful like a pharmacist or hospital billing assistant."
        )

        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
        messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant who summarizes medical bills and answers related questions."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }}
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.4
        )

        answer = response.choices[0].message.content
        print("🧪 [DEBUG] OpenAI response below:\n", answer)
        socketio.emit('bill_analysis', {'data': answer})
        return jsonify({"response": answer})

    except Exception as e:
        print(f"❌ Error occurred in /ask-question: {str(e)}")
        return jsonify({"error": str(e)}), 500



@app.route('/prescription', methods=['POST'])
def prescription_route():
    print("🚨 Request received at /prescription")
    
    # Check if the file is in the request
    if 'file' not in request.files:
        return jsonify({"error": "File is required"}), 400

    # Save the file to the desired directory
    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        # Read and encode the image file to base64
        with open(file_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Define the prompt for prescription processing
        prompt = (
            "This is a medical prescription. Extract all medicine names, all intake timings (in HH:MM AM/PM format), "
            "whether they should be taken before or after meals, and how many days each medicine must be taken. "
            "Return a list in this format:\n"
            "[{'medicine': 'Paracetamol', 'time': ['08:00 AM', '08:00 PM'], 'meal': 'after meal', 'days': 5}]"
        )

        # OpenAI Vision API call
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]}
            ],
            max_tokens=800,
            temperature=0.4
        )

        # Extract the response content
        content = response.choices[0].message.content
        print("🧪 [DEBUG] OpenAI response:")
        print(content)

        # Try to parse the JSON output from OpenAI
        try:
            meds_data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                json_like = match.group(0).replace("'", '"')
                meds_data = json.loads(json_like)
            else:
                raise ValueError("Could not extract valid JSON from response.")

        # Schedule reminders for the prescription
        start_date = datetime.now()
        scheduled_reminders = []
        refill_reminders = []

        for item in meds_data:
            reminder_id = str(uuid.uuid4())
            medicine = item['medicine']
            time_list = item['time']
            raw_days = item.get('days', 3)

            try:
                days = int(raw_days)
                is_numeric_days = True
            except (ValueError, TypeError):
                days = 3  # fallback for 'Cont.' or 'as needed'
                is_numeric_days = False

            for time_str in time_list:
                try:
                    time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
                except ValueError:
                    print(f"⚠️ Skipping invalid time: {time_str}")
                    continue

                for i in range(days):
                    scheduled_time = (start_date + timedelta(days=i)).replace(
                        hour=time_obj.hour, minute=time_obj.minute, second=0)

                    scheduled_reminders.append({
                        "medicine": medicine,
                        "datetime": scheduled_time.isoformat()
                    })

                    def send_reminder(med=medicine):
                        print(f"⏰ Reminder: Time to take {med}!")

                    scheduler.add_job(
                        send_reminder,
                        'date',
                        run_date=scheduled_time,
                        id=f"{reminder_id}_{i}_{time_str}",
                        replace_existing=True
                    )

            if is_numeric_days and days > 2:
                refill_day = days - 2
                refill_time = (start_date + timedelta(days=refill_day)).replace(
                    hour=23, minute=0, second=0)

                def send_refill_reminder(med=medicine):
                    print(f"🔔 Refill reminder for {med}")

                scheduler.add_job(
                    send_refill_reminder,
                    'date',
                    run_date=refill_time,
                    id=f"refill_{reminder_id}",
                    replace_existing=True
                )

                refill_reminders.append({
                    "medicine": medicine,
                    "refill_date": refill_time.isoformat()
                })

        return jsonify({
            "message": "Reminders scheduled from image prescription",
            "data": meds_data,
            "scheduled_reminders": scheduled_reminders,
            "refill_reminders": refill_reminders
        })

    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


        
@app.route('/stores', methods=['GET'])
def get_stores():
    store_data = {}

    with open('store_data.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            store = row['store']
            location = row['location']
            medicine = {
                'name': row['medicine'],
                'price': row['price'],
                'description': row['description']
            }

            if store not in store_data:
                store_data[store] = {
                    'location': location,
                    'medicines': [medicine]
                }
            else:
                store_data[store]['medicines'].append(medicine)

    return jsonify(store_data)



# Medical Chat Endpoint
@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        question = data.get('question', '').lower()

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        non_medical_keywords = [
            'ai', 'artificial intelligence', 'python', 'java', 'programming', 'computer',
            'software', 'technology', 'tech', 'machine learning', 'robot', 'cloud', 'internet'
        ]
        if any(keyword in question for keyword in non_medical_keywords):
            return jsonify({
                "response": (
                    "I'm a medical assistant and can only help with health-related questions. "
                    "Please ask something about your symptoms, treatments, or other health concerns."
                )
            })

        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return a **structured medical response** under the main heading:\n\n"
                        "## Lab Scan Recommendations\n\n"
                        "Break the content into the following sections, each clearly marked:\n\n"
                        "### 1. Recommended Lab Tests\n"
                        "- List specific diagnostic lab tests with a short explanation for each.\n\n"
                        "### 2. Recommended Scans/Imaging\n"
                        "- Mention relevant scans/imaging (if needed), each with a brief reason.\n\n"
                        "### 3. Possible Treatment Options\n"
                        "- Include general treatment advice, medications, and referral suggestions.\n\n"
                        "**Guidelines:**\n"
                        "- DO NOT answer unrelated or non-medical questions.\n"
                        "- If symptoms are not valid, reply with:\n"
                        "\"Please provide valid medical symptoms for lab test recommendations.\"\n"
                        "- Ensure markdown-style formatting and clarity."
                    )
                },
                {"role": "user", "content": question}
            ],
            max_tokens=600,
            temperature=0.5
        )

        answer = response.choices[0].message.content
        return jsonify({"response": answer})

    except Exception as e:
        print(f"❌ Error in /chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

        
def send_patient_data():
    global patient_data, sleeping, sleep_hours, last_emit_time

    while True:
        now = time.time()
        elapsed = now - last_emit_time
        last_emit_time = now

        # Urgent patient falls asleep/wakes up more often
        if not sleeping and random.random() < 0.1:  # Higher chance to fall asleep
            sleeping = True
            print("💤 Urgent patient started sleeping")
        elif sleeping and random.random() < 0.2:  # Higher chance to wake up
            sleeping = False
            print("☀️ Urgent patient woke up")

        if sleeping:
            sleep_hours += elapsed / 3600  # accumulate sleep in hours

        # Urgent patient vitals — higher and more erratic values
        patient_data = {
            "heart_rate": random.randint(110, 140),       # higher heart rate
            "bp_systolic": random.randint(140, 180),      # higher systolic pressure
            "bp_diastolic": random.randint(90, 110),      # higher diastolic pressure
            "sleeping": sleeping,
            "sleep_hours": round(sleep_hours, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"📡 Emitting urgent patient data: {patient_data}")
        socketio.emit('patient_data', patient_data)

       

        eventlet.sleep(2)


def send_patient_data():
    global patient_data, sleeping, sleep_hours, last_emit_time

    while True:
        now = time.time()
        elapsed = now - last_emit_time
        last_emit_time = now

        # Normal patient sleep transitions are less frequent
        if not sleeping and random.random() < 0.03:  # lower chance to fall asleep
            sleeping = True
            print("💤 Normal patient started sleeping")
        elif sleeping and random.random() < 0.02:  # lower chance to wake up
            sleeping = False
            print("☀️ Normal patient woke up")

        if sleeping:
            sleep_hours += elapsed / 3600  # accumulate sleep hours
           
        # Normal patient vitals - healthy ranges
        patient_data = {
            "heart_rate": random.randint(60, 90),        # normal heart rate
            "bp_systolic": random.randint(110, 125),     # normal systolic BP
            "bp_diastolic": random.randint(70, 85),      # normal diastolic BP
            "sleeping": sleeping,
            "sleep_hours": round(sleep_hours, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"📡 Emitting normal patient data: {patient_data}")
        socketio.emit('patient_data', patient_data)

        eventlet.sleep(2)



        # # Alerts
        # if patient_data["heart_rate"] > 100:
        #     socketio.emit('message', {'data': '⚠️ High heart rate detected!'})

        # if patient_data["sleep_hours"] < 6 and not sleeping:
        #     socketio.emit('message', {'data': '😴 Not enough sleep. Please rest more.'})

        eventlet.sleep(2)

@socketio.on('connect')
def handle_connect():
    print("🟢 Client connected")
    emit('message', {'data': 'Welcome! How can I make your experience easier today?'})

@socketio.on('disconnect')
def handle_disconnect():
    print("🔌 Client disconnected")

# Start the background task
socketio.start_background_task(send_patient_data)

# Run the server
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
 