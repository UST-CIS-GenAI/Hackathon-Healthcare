# AI Medical Assistant Chatbot

## Table of Contents
- Features
- Demo
- Installation
- Folder Structure
- Usage
- Frontend
- Contributing
- Acknowledgments

##  Features
- Medical Bill Analysis — Upload images of medical bills and get simplified, patient-friendly breakdowns.
- Prescription Management — Extracts medication details, sets reminders, and alerts for refills.
- Prescreening Questionnaire — Interactive questionnaire to collect patient data and export to PDF.
- Appointment Scheduling — Helps users choose place, hospital, department, doctor, and schedule time.
- Health Chat — Provides accurate, structured responses for symptoms, treatment, and lab advice.
- Real-Time Patient Monitoring — Simulates vital signs (heart rate, BP) and streams data to clients.


##  Installation

1. Clone the repository:
   git clone https://github.com/your-username/ai-medical-chatbot.git
   cd ai-medical-chatbot/New_chatbot_0.1/chatboat\ ui/backend

2. Install dependencies:
   Ensure Python 3.8+ is installed. Then run:
   pip install -r requirements.txt

3. Set environment variables:
   Create a `.env` file in the `backend/` directory with:
   OPENAI_ENDPOINT=<your_openai_endpoint>
   OPENAI_API_KEY=<your_openai_api_key>
   OPENAI_DEPLOYMENT=<your_openai_deployment_name>

4. Run the backend:
   python app.py

5. Run the frontend:
   Go to frontend folder, give commands npm i, npm run dev

##  Folder Structure
New_chatbot_0.1/
├── chatboat ui/
│   ├── backend/
│   │   ├── app.py
│   │   ├── hospital_data.json
│   │   ├── .env
│   │   └── uploads/
│   ├── frontend/
│   │   ├── index.html
│   │   ├── styles.css
│   │   ├── app.jsx
│   │   └── assets/
├── requirements.txt
├── README.md
└── LICENSE

##  Usage
- Medical Bill Analysis — Upload a bill image to get a breakdown.
- Prescription Management — Upload a prescription for intake reminders.
- Prescreening — Answer questions to generate a PDF summary.
- Appointment Booking — Follow prompts to schedule with a doctor.
- Medical Chat — Ask health-related questions for AI-powered advice.

## 🌐 Frontend

The frontend is built using React and communicates with the backend using Socket.IO.

Key Files:
- index.html
- app.jsx
- styles.css
- assets/

Note: Ensure the backend is running before using the frontend.

##  Contributing

1. Fork the repository  
2. Create a new branch:  
   git checkout -b my-feature  
3. Commit your changes:  
   git commit -m "Add feature"  
4. Push to the branch:  
   git push origin my-feature  
5. Open a pull request.



##  Acknowledgments
- OpenAI — GPT language model
- Flask — Backend framework
- Flask-SocketIO — Real-time WebSocket support
- FPDF — PDF generation library
