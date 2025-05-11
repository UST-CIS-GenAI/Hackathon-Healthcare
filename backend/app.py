import os
import random
import base64
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify,send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import openai
import json
import threading
from fpdf import FPDF
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import uuid
import re
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()
scheduler.start()


# Load environment variables
load_dotenv()

openai.api_type = "azure"
openai.api_base = os.getenv("OPENAI_ENDPOINT")
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_version = "2024-05-01-preview"
DEPLOYMENT_NAME = os.getenv("OPENAI_DEPLOYMENT")

app = Flask(__name__)


# ✅ CORS setup for cross-origin requests
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ✅ Allow OPTIONS method for preflight
@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


def load_hospital_data():
    file_path = os.path.join(os.path.dirname(__file__), 'hospital_data.json')
    with open(file_path, 'r') as f:
        return json.load(f)['places']

def generate_pdf(answers, filepath):
    questions = [
    "May I have your full name for the medical record?",
    "What's your age?",
    "Do you have any chronic conditions?",
    "Are you currently on medication?",
    "Can you describe the symptoms you're currently experiencing? (Separate multiple with commas)",
    "When did you first notice these symptoms? (Provide number of days or the specific date)",
    "On a scale of 1 to 10, how intense or uncomfortable are your symptoms currently?",
    "Do you have any recent vital signs available? (e.g., Temperature: 101°F, Heart Rate: 95 bpm, Blood Pressure: 120/80 mmHg)",
    "Do you have any relevant past medical conditions or chronic diseases? (e.g., diabetes, hypertension, asthma)",
    "Are you currently taking any medications? (Please list them with dosage if possible)",
    "Have you experienced similar symptoms in the past? If yes, when and how was it managed?",
    "Is there anything else you'd like the doctor to know before the consultation?"
    ]


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
        "Then summarize the total bill: subtotal, discounts, VAT, freight, insurance, and grand total — with clear meaning of each.\n\n"
        "If a medicine name is unclear, make your best guess based on known drugs. Avoid making up values. "
        "Be very clear and helpful like a pharmacist or hospital billing assistant."

        )   

        response = openai.ChatCompletion.create(
            engine=DEPLOYMENT_NAME,
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
            max_tokens=800,
            temperature=0.4
        )

        answer = response['choices'][0]['message']['content']
        print("🧪 [DEBUG] OpenAI response below:")
        print("--------------------------------------------------")
        print(answer)
        print("--------------------------------------------------")

        socketio.emit('bill_analysis', {'data': answer})
        return jsonify({"response": answer})

    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


# @app.route('/ask-question', methods=['POST'])
# def ask_question():
#     print("🚨 Request received at /ask-question")
    
#     # Dummy response for testing purpose
#     detailed_explanation = """
#     Here is a detailed explanation of each item listed in the medical bill:

#     1. **Pantocid DSR99999**
#        - **Medicine Name**: Pantocid DSR
#        - **Common Use**: This is typically used to treat gastroesophageal reflux disease (GERD), where it helps reduce stomach acid and relieve symptoms like heartburn.
#        - **Dose/Form**: Capsule
#        - **Usage Info**: Usually taken before meals, as directed by a healthcare provider.
#        - **MRP**: ₹240.00
#        - **Quantity**: 2 packs of 15 capsules each
#        - **Total Amount Charged**: ₹430.00

#     2. **Calpol 500mg**
#        - **Medicine Name**: Calpol 500mg
#        - **Common Use**: Used to relieve pain and reduce fever. It contains paracetamol.
#        - **Dose/Form**: Tablet
#        - **Usage Info**: Can be taken with or without food, typically as needed for pain or fever.
#        - **MRP**: ₹18.55
#        - **Quantity**: 1 pack of 15 tablets
#        - **Total Amount Charged**: ₹15.00

#     3. **Baidyanath Vansaar Isabgol Psyllium Husk Powder**
#        - **Medicine Name**: Baidyanath Vansaar Isabgol Psyllium Husk Powder
#        - **Common Use**: A natural fiber supplement used to relieve constipation and promote digestive health.
#        - **Dose/Form**: Edible Powder
#        - **Usage Info**: Usually mixed with water or juice and consumed once or twice daily.
#        - **MRP**: ₹225.00
#        - **Quantity**: 1 pack
#        - **Total Amount Charged**: ₹98.00

#     4. **Azee 500mg**
#        - **Medicine Name**: Azee 500mg
#        - **Common Use**: An antibiotic used to treat various bacterial infections.
#        - **Dose/Form**: Tablet
#        - **Usage Info**: Should be taken as prescribed by a healthcare provider, often once daily.
#        - **MRP**: ₹119.50
#        - **Quantity**: 3 packs of 5 tablets each
#        - **Total Amount Charged**: ₹315.00

#     5. **Amoxyclav 625**
#        - **Medicine Name**: Amoxyclav 625
#        - **Common Use**: An antibiotic used to treat a variety of bacterial infections, combining amoxicillin and clavulanic acid.
#        - **Dose/Form**: Tablet
#        - **Usage Info**: Typically taken with food to reduce stomach upset.
#        - **MRP**: ₹201.47
#        - **Quantity**: 1 pack of 6 tablets
#        - **Total Amount Charged**: ₹105.00

#     6. **Telma 40**
#        - **Medicine Name**: Telma 40
#        - **Common Use**: Used to treat high blood pressure (hypertension).
#        - **Dose/Form**: Tablet
#        - **Usage Info**: Usually taken once daily, with or without food.
#        - **MRP**: ₹246.90
#        - **Quantity**: 2 packs of 10 tablets each
#        - **Total Amount Charged**: ₹390.00

#     7. **Baidyanath Kabzhar Tablet**
#        - **Medicine Name**: Baidyanath Kabzhar Tablet
#        - **Common Use**: Herbal formulation used to relieve constipation.
#        - **Dose/Form**: Tablet
#        - **Usage Info**: Typically taken with water, often at bedtime.
#        - **MRP**: ₹160.00
#        - **Quantity**: 1 pack
#     """

#     # Emit the explanation to the client (simulating real-time communication)
#     socketio.emit('bill_analysis', {'data': detailed_explanation})
    
#     # Return the dummy response in the API response
#     return jsonify({"response": detailed_explanation})


# # Dummy prescription data for testing purpose


@app.route('/prescription', methods=['POST'])
def prescription_route():
    print("🚨 Request received at /prescription")

    # Dummy prescription data (update as needed for test)
    dummy_data = [
        {'medicine': 'Naprosyn', 'time': ['10:04 AM', '04:01 PM'], 'meal': 'after meal', 'days': 1},
        {'medicine': 'Beklo', 'time': ['10:05 AM', '04:03 PM'], 'meal': 'after meal', 'days': 5},
        {'medicine': 'Neocepin-R', 'time': ['10:06 AM', '08:00 PM'], 'meal': 'before meal', 'days': 15},
        {'medicine': 'Ace', 'time': ['08:00 AM', '12:00 PM', '08:00 PM'], 'meal': 'after meal', 'days': 2},
        {'medicine': 'Calbo D', 'time': ['08:00 PM'], 'meal': 'after meal', 'days': 'Cont.'},
        {'medicine': 'Avolac', 'time': ['08:00 AM', '12:00 PM', '08:00 PM'], 'meal': 'after meal', 'days': 'as needed for constipation'}
    ]

    try:
        # Set the start date for testing (example: 5/8/2025)
        start_date = datetime(2025, 5, 8, 0, 0, 0)  # May 8th, 2025 at midnight
        scheduled_reminders = []
        refill_reminders = []

        # Iterate through dummy data for each medicine
        for item in dummy_data:
            reminder_id = str(uuid.uuid4())
            medicine = item['medicine']
            time_list = item['time']
            raw_days = item.get('days', 3)

            try:
                days = int(raw_days)
                is_numeric_days = True
            except (ValueError, TypeError):
                days = 3  # fallback for 'Cont.' or similar
                is_numeric_days = False

            for time_str in time_list:
                try:
                    time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
                except ValueError:
                    print(f"⚠️ Skipping invalid time: {time_str}")
                    continue

                for i in range(days):
                    scheduled_time = (start_date + timedelta(days=i)).replace(
                        hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0
                    )

                    scheduled_reminders.append({
                        "medicine": medicine,
                        "datetime": scheduled_time.isoformat()
                    })

                    # Define reminder function
                    def send_reminder(med=medicine):
                        print(f"⏰ Reminder: Time to take {med}!")

                    # Schedule reminder for each medicine
                    scheduler.add_job(
                        send_reminder,
                        'date',
                        run_date=scheduled_time,
                        id=f"{reminder_id}_{i}_{time_str}",
                        replace_existing=True
                    )

                # ✅ Schedule refill reminder 2 days before the last dose (for numeric durations)
                if is_numeric_days and days > 2:
                    refill_day = days - 2  # Subtract 2 to schedule refill reminder 2 days before last dose
                    refill_time = (start_date + timedelta(days=refill_day)).replace(
                        hour=23, minute=0, second=0, microsecond=0  # Set refill time to 11:00 PM
                    )

                    # Define refill reminder function
                    def send_refill_reminder(med=medicine):
                        print(f"🔔 Refill reminder for {med}")

                    # Schedule refill reminder
                    scheduler.add_job(
                        send_refill_reminder,
                        'date',
                        run_date=refill_time,
                        id=f"refill_{reminder_id}",
                        replace_existing=True
                    )

                    # Add refill reminder info to the list to send to the frontend
                    refill_reminders.append({
                        "medicine": medicine,
                        "refill_date": refill_time.isoformat()
                    })

        return jsonify({
            "message": "Reminders scheduled",
            "data": dummy_data,
            "scheduled_reminders": scheduled_reminders,
            "refill_reminders": refill_reminders
        })

    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500



# @app.route('/prescription', methods=['POST'])
# def prescription_route():
#     print("🚨 Request received at /prescription")
#     if 'file' not in request.files:
#         return jsonify({"error": "File is required"}), 400

#     file = request.files['file']
#     file_path = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(file_path)

#     try:
#         with open(file_path, "rb") as f:
#             image_bytes = f.read()
#             image_base64 = base64.b64encode(image_bytes).decode('utf-8')

#         prompt = (
#             "This is a medical prescription. Extract all medicine names, all intake timings (in HH:MM AM/PM format), "
#             "whether they should be taken before or after meals, and how many days each medicine must be taken. "
#             "Return a list in this format:\n"
#             "[{'medicine': 'Paracetamol', 'time': ['08:00 AM', '08:00 PM'], 'meal': 'after meal', 'days': 5}]"
#         )

#         response = openai.ChatCompletion.create(
#             engine=DEPLOYMENT_NAME,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant."},
#                 {"role": "user", "content": [
#                     {"type": "text", "text": prompt},
#                     {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
#                 ]}
#             ],
#             max_tokens=800,
#             temperature=0.4
#         )

#         content = response['choices'][0]['message']['content']
#         print("🧪 [DEBUG] OpenAI response below:")
#         print("--------------------------------------------------")
#         print(content)
#         print("--------------------------------------------------")

#         try:
#             meds_data = json.loads(content)
#         except json.JSONDecodeError:
#             match = re.search(r"\[.*\]", content, re.DOTALL)
#             if match:
#                 json_like = match.group(0)
#                 json_like = json_like.replace("'", '"')
#                 meds_data = json.loads(json_like)
#             else:
#                 raise ValueError("Could not extract valid JSON from response.")

#         # ✅ Schedule only medicine-taking reminders
#         start_date = datetime.now()
#         for item in meds_data:
#             reminder_id = str(uuid.uuid4())
#             medicine = item['medicine']
#             time_list = item['time']
#             raw_days = item.get('days', 3)

#             try:
#                 days = int(raw_days)
#             except (ValueError, TypeError):
#                 days = 3  # fallback for 'Cont.' or 'as needed'

#             for time_str in time_list:
#                 try:
#                     time_obj = datetime.strptime(time_str.strip(), "%I:%M %p")
#                 except ValueError:
#                     print(f"⚠️ Skipping invalid time: {time_str}")
#                     continue

#                 for i in range(days):
#                     scheduled_time = (start_date + timedelta(days=i)).replace(
#                         hour=time_obj.hour, minute=time_obj.minute, second=0)

#                     def send_reminder(med=medicine):
#                         print(f"⏰ Reminder: Time to take {med}!")

#                     scheduler.add_job(
#                         send_reminder,
#                         'date',
#                         run_date=scheduled_time,
#                         id=f"{reminder_id}_{i}_{time_str}",
#                         replace_existing=True
#                     )

#         return jsonify({"message": "Reminders scheduled", "data": meds_data})

#     except Exception as e:
#         print(f"❌ Error occurred: {str(e)}")
#         return jsonify({"error": str(e)}), 500




@app.route('/prescreening', methods=['POST'])
def prescreening():
    data = request.json
    answers = data.get('answers', [])

    questions = [
    "May I have your full name for the medical record?",
    "What's your age?",
    "Do you have any chronic conditions?",
    "Are you currently on medication?",
    "Can you describe the symptoms you're currently experiencing? (Separate multiple with commas)",
    "When did you first notice these symptoms? (Provide number of days or the specific date)",
    "On a scale of 1 to 10, how intense or uncomfortable are your symptoms currently?",
    "Do you have any recent vital signs available? (e.g., Temperature: 101°F, Heart Rate: 95 bpm, Blood Pressure: 120/80 mmHg)",
    "Do you have any relevant past medical conditions or chronic diseases? (e.g., diabetes, hypertension, asthma)",
    "Are you currently taking any medications? (Please list them with dosage if possible)",
    "Have you experienced similar symptoms in the past? If yes, when and how was it managed?",
    "Is there anything else you'd like the doctor to know before the consultation?"
    ]


    if len(answers) < len(questions):
        next_question = questions[len(answers)]
        return jsonify({"response": next_question})
    else:
        # Generate PDF and get filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prescreening_{timestamp}.pdf"
        filepath = os.path.join("uploads", filename)

        def create_pdf():
            generate_pdf(answers, filepath)

        threading.Thread(target=create_pdf).start()

        file_url = f"http://localhost:5000/uploads/{filename}"  # Replace with actual domain if deployed
        return jsonify({
            "response": f"Prescreening completed. [📄 Download PDF]({file_url})",
            "file_url": file_url
        })
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)




@app.route('/appointment', methods=['POST'])
def appointment():
    data = request.json
    answers = data.get('answers', [])
    hospital_data = load_hospital_data()

    if len(answers) == 0:
        return jsonify({
            "response": "Which place are you looking in?",
            "options": list(hospital_data.keys())
        })

    if len(answers) == 1:
        place = answers[0]
        if place not in hospital_data:
            return jsonify({"response": "Invalid place selected."})
        return jsonify({
            "response": f"Select a hospital in {place}:",
            "options": list(hospital_data[place].keys())
        })

    if len(answers) == 2:
        place, hospital = answers
        departments = hospital_data[place][hospital]
        return jsonify({
            "response": f"Select a department in {hospital}:",
            "options": list(departments.keys())
        })

    if len(answers) == 3:
        place, hospital, department = answers
        doctors = hospital_data[place][hospital][department]
        return jsonify({
            "response": f"Select a doctor in {department}:",
            "options": list(doctors.keys())
        })

    if len(answers) == 4:
        place, hospital, department, doctor = answers
        times = hospital_data[place][hospital][department][doctor]
        return jsonify({
            "response": f"Select a time for {doctor}:",
            "options": times
        })

    if len(answers) == 5:
        place, hospital, department, doctor, time = answers
        summary = (
            f"✅ Appointment confirmed:\n"
            f"📍 Place: {place}\n"
            f"🏥 Hospital: {hospital}\n"
            f"🧪 Department: {department}\n"
            f"👨‍⚕️ Doctor: {doctor}\n"
            f"⏰ Time: {time}"
        )
        return jsonify({"response": summary})

    return jsonify({"response": "Invalid step."})


# #===========================================================================================

@app.route('/chat', methods=['POST', 'OPTIONS'])  # ✅ OPTIONS added for preflight
def chat():
    if request.method == 'OPTIONS':
        return '', 200  # ✅ Preflight handled

    try:
        data = request.get_json()
        question = data.get('question', '').lower()

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        # 🚫 Basic non-medical keyword filter
        non_medical_keywords = [
            'ai', 'artificial intelligence', 'python', 'java', 'programming', 'computer',
            'software', 'technology', 'tech', 'machine learning', 'robot', 'cloud', 'internet'
        ]
        if any(keyword in question for keyword in non_medical_keywords):
            return jsonify({
                "response": "I'm a medical assistant and can only help with health-related questions. "
                            "Please ask something about your symptoms, treatments, or other health concerns."
            })

        response = openai.ChatCompletion.create(
            engine=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        
                    "Return a **structured medical response** under the main heading:"
 
                     ## Lab Scan Recommendations
 
                     "Break the content into the following sections, each clearly marked:"
 
                      ### 1. Recommended Lab Tests  
                      "- List specific diagnostic lab tests with a short explanation for each."
 
                      ### 2. Recommended Scans/Imaging  
                      "- Mention relevant scans/imaging (if needed), each with a brief reason."
 
                       ### 3. Possible Treatment Options  
                      "- Include general treatment advice, medications, and referral suggestions."
 
                       "Guidelines:"
                         "- DO NOT answer unrelated or non-medical questions."
                           "- If symptoms are not valid, reply with:  "
                             "Please provide valid medical symptoms for lab test recommendations."
                          "- Ensure markdown-style formatting and clarity."
                      
                    )
                },
                {"role": "user", "content": question}
            ],
            max_tokens=600,
            temperature=0.5
        )

        answer = response['choices'][0]['message']['content']
        return jsonify({"response": answer})

    except Exception as e:
        print(f"❌ Error in /chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Background emitter for simulated patient data
def send_patient_data():
    while True:
        patient_data = {
            "heart_rate": random.randint(60, 120),
            "bp_systolic": random.randint(100, 140),
            "bp_diastolic": random.randint(60, 90),
            "sleep_hours": round(random.uniform(4.0, 9.0), 1),
        }

        print(f"📡 Emitting patient data: {patient_data}")
        socketio.emit('patient_data', patient_data)

        # if patient_data["heart_rate"] > 100:
        #     socketio.emit('message', {'data': '⚠️ High heart rate detected!'})

        # if patient_data["sleep_hours"] < 6:
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
