import os
import re
from dotenv import load_dotenv
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.messages import AIMessage

# ✅ Load environment variables
load_dotenv()

# ✅ Create prompt template
prompt_template = PromptTemplate.from_template(
    "Given the symptom: {symptom}, hospital summary: {hospital_summary}, and medical data: {medical_data}, generate 5 relevant and concise medical questions to ask the patient."
)

# ✅ Initialize Azure OpenAI Chat LLM
llm = AzureChatOpenAI(
    deployment_name=os.getenv("OPENAI_DEPLOYMENT"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_version="2024-05-01-preview",
    openai_api_base=os.getenv("OPENAI_ENDPOINT"),
    temperature=0.3,
)

# ✅ Chain the prompt into the LLM
prescreen_chain = prompt_template | llm

# ✅ Function to generate a list of questions
def generate_dynamic_questions(symptom, hospital_summary, medical_data):
    result = prescreen_chain.invoke({
        "symptom": symptom,
        "hospital_summary": hospital_summary,
        "medical_data": medical_data
    })

    # ✅ Extract text from AIMessage
    content = result.content if isinstance(result, AIMessage) else str(result)

    # ✅ Parse numbered list (1. / 2. / etc.)
    questions = re.split(r'\n?\d+[\.\)]\s*', content)
    questions = [q.strip() for q in questions if q.strip()]

    print("[✓] Parsed Questions:", questions)
    return questions
