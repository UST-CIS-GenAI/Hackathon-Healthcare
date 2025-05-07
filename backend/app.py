import os
import random
import base64
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import openai

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

# @app.route('/ask-question', methods=['POST'])
# def ask_question():
#     print("🚨 Request received at /ask-question")
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
#         "This is an image of a medical bill. Please carefully read and extract all items from the table. "
#         "For each line item, give a clear, patient-friendly explanation that includes:\n"
#         "- The medicine name\n"
#         "- What it's commonly used for\n"
#         "- Its dose or form (e.g., tablet, syrup, injection)\n"
#         "- Any helpful usage info if known\n"
#         "- MRP, quantity, and total amount charged\n\n"
#         "Then summarize the total bill: subtotal, discounts, VAT, freight, insurance, and grand total — with clear meaning of each.\n\n"
#         "If a medicine name is unclear, make your best guess based on known drugs. Avoid making up values. "
#         "Be very clear and helpful like a pharmacist or hospital billing assistant."
#         )   

#         response = openai.ChatCompletion.create(
#             engine=DEPLOYMENT_NAME,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are a helpful assistant who summarizes medical bills and answers related questions."
#                 },
#                 {
#                     "role": "user",
#                     "content": [
#                         {"type": "text", "text": prompt},
#                         {"type": "image_url", "image_url": {
#                             "url": f"data:image/jpeg;base64,{image_base64}"
#                         }}
#                     ]
#                 }
#             ],
#             max_tokens=800,
#             temperature=0.4
#         )

#         answer = response['choices'][0]['message']['content']
#         print("🧪 [DEBUG] OpenAI response below:")
#         print("--------------------------------------------------")
#         print(answer)
#         print("--------------------------------------------------")

#         socketio.emit('bill_analysis', {'data': answer})
#         return jsonify({"response": answer})

#     except Exception as e:
#         print(f"❌ Error occurred: {str(e)}")
#         return jsonify({"error": str(e)}), 500
@app.route('/ask-question', methods=['POST'])
def ask_question():
    print("🚨 Request received at /ask-question")
    
    # Dummy response for testing purpose
    detailed_explanation = """
    Here is a detailed explanation of each item listed in the medical bill:

    1. **Pantocid DSR99999**
       - **Medicine Name**: Pantocid DSR
       - **Common Use**: This is typically used to treat gastroesophageal reflux disease (GERD), where it helps reduce stomach acid and relieve symptoms like heartburn.
       - **Dose/Form**: Capsule
       - **Usage Info**: Usually taken before meals, as directed by a healthcare provider.
       - **MRP**: ₹240.00
       - **Quantity**: 2 packs of 15 capsules each
       - **Total Amount Charged**: ₹430.00

    2. **Calpol 500mg**
       - **Medicine Name**: Calpol 500mg
       - **Common Use**: Used to relieve pain and reduce fever. It contains paracetamol.
       - **Dose/Form**: Tablet
       - **Usage Info**: Can be taken with or without food, typically as needed for pain or fever.
       - **MRP**: ₹18.55
       - **Quantity**: 1 pack of 15 tablets
       - **Total Amount Charged**: ₹15.00

    3. **Baidyanath Vansaar Isabgol Psyllium Husk Powder**
       - **Medicine Name**: Baidyanath Vansaar Isabgol Psyllium Husk Powder
       - **Common Use**: A natural fiber supplement used to relieve constipation and promote digestive health.
       - **Dose/Form**: Edible Powder
       - **Usage Info**: Usually mixed with water or juice and consumed once or twice daily.
       - **MRP**: ₹225.00
       - **Quantity**: 1 pack
       - **Total Amount Charged**: ₹98.00

    4. **Azee 500mg**
       - **Medicine Name**: Azee 500mg
       - **Common Use**: An antibiotic used to treat various bacterial infections.
       - **Dose/Form**: Tablet
       - **Usage Info**: Should be taken as prescribed by a healthcare provider, often once daily.
       - **MRP**: ₹119.50
       - **Quantity**: 3 packs of 5 tablets each
       - **Total Amount Charged**: ₹315.00

    5. **Amoxyclav 625**
       - **Medicine Name**: Amoxyclav 625
       - **Common Use**: An antibiotic used to treat a variety of bacterial infections, combining amoxicillin and clavulanic acid.
       - **Dose/Form**: Tablet
       - **Usage Info**: Typically taken with food to reduce stomach upset.
       - **MRP**: ₹201.47
       - **Quantity**: 1 pack of 6 tablets
       - **Total Amount Charged**: ₹105.00

    6. **Telma 40**
       - **Medicine Name**: Telma 40
       - **Common Use**: Used to treat high blood pressure (hypertension).
       - **Dose/Form**: Tablet
       - **Usage Info**: Usually taken once daily, with or without food.
       - **MRP**: ₹246.90
       - **Quantity**: 2 packs of 10 tablets each
       - **Total Amount Charged**: ₹390.00

    7. **Baidyanath Kabzhar Tablet**
       - **Medicine Name**: Baidyanath Kabzhar Tablet
       - **Common Use**: Herbal formulation used to relieve constipation.
       - **Dose/Form**: Tablet
       - **Usage Info**: Typically taken with water, often at bedtime.
       - **MRP**: ₹160.00
       - **Quantity**: 1 pack
    """

    # Emit the explanation to the client (simulating real-time communication)
    socketio.emit('bill_analysis', {'data': detailed_explanation})
    
    # Return the dummy response in the API response
    return jsonify({"response": detailed_explanation})
# @app.route('/ask-question', methods=['POST'])
# def ask_question():
#     print("🚨 Request received at /ask-question")
    
#     doc_type = request.form.get('docType', '').lower()  # 👈 Get the document type

#     if 'file' not in request.files:
#         return jsonify({"error": "File is required"}), 400

#     file = request.files['file']
#     file_path = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(file_path)

#     try:
#         with open(file_path, "rb") as f:
#             image_bytes = f.read()
#             image_base64 = base64.b64encode(image_bytes).decode('utf-8')

#         if doc_type == 'bill':
#             prompt = """You are an expert in analyzing medical bills. Extract all billing items from this image and explain them in patient-friendly language..."""
#         elif doc_type == 'prescription':
#             prompt = """You are a medical assistant. Carefully review this prescription image and list each medication prescribed along with usage instructions..."""
#         else:
#             prompt = "Please analyze the medical document and provide helpful information."

#         response = openai.ChatCompletion.create(
#             engine=DEPLOYMENT_NAME,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant who summarizes medical documents."},
#                 {"role": "user", "content": [
#                     {"type": "text", "text": prompt},
#                     {"type": "image_url", "image_url": {
#                         "url": f"data:image/jpeg;base64,{image_base64}"
#                     }}
#                 ]}
#             ],
#             max_tokens=800,
#             temperature=0.4
#         )

#         answer = response['choices'][0]['message']['content']
#         socketio.emit('bill_analysis', {'data': answer})
#         return jsonify({"response": answer})

#     except Exception as e:
#         print(f"❌ Error occurred: {str(e)}")
#         return jsonify({"error": str(e)}), 500



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
                        "You are a medical assistant. "
                        "Only respond to health-related topics such as symptoms, treatments, lab tests, or wellness. "
                        "If a question is not medical-related, respond with: "
                        "'I'm a medical assistant and can only help with health-related questions. "
                        "Please ask me something related to your symptoms or medical concerns.'"
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
    emit('message', {'data': 'Welcome! You are connected to the patient data server.'})

@socketio.on('disconnect')
def handle_disconnect():
    print("🔌 Client disconnected")

# Start the background task
socketio.start_background_task(send_patient_data)

# Run the server
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
