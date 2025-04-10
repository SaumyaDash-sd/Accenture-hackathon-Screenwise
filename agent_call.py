from langchain_openai import OpenAI, AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
import os
import ast
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv  import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)



def parse_gpt_output(gpt_response: str) -> dict:
    """
    Attempts to parse the provided GPT response as a list or dictionary.
    If that fails, extracts the content between the first and last curly braces
    and parses it using ast.literal_eval.

    Args:
        gpt_response (str): The GPT response to be parsed.

    Returns:
        dict: The parsed GPT response as a dictionary, or an empty dictionary if parsing fails.
    """
    try:
        # Attempt to parse the entire response
        parsed = ast.literal_eval(gpt_response)
        logging.info("GPT response parsed successfully using ast.literal_eval.")
        if isinstance(parsed, (dict, list)):
            return parsed
        else:
            logging.warning("Parsed output is not a dict or list; attempting extraction.")
    except Exception as e:
        logging.warning("Initial parsing failed: %s", e)

    # Fallback: extract content between the first and last curly braces
    try:
        start_index = gpt_response.find("{")
        end_index = gpt_response.rfind("}")
        if start_index != -1 and end_index != -1:
            extracted_content = gpt_response[start_index:end_index + 1]
            parsed = ast.literal_eval(extracted_content)
            logging.info("Extracted content parsed successfully.")
            return parsed
    except Exception as inner_e:
        logging.exception("Failed to parse extracted content: %s", inner_e)

    logging.error("Failed to parse GPT output; returning empty dictionary.")
    return {}


@tool
def print_hello():
    """
    Print hello world.
    """
    print("Hello world!")
    return "Hello world!"

# @tool
def send_email(candidate_details):
    """
    Sends an email to the candidate with the provided details.
    """
    # Set up the SMTP server (using Gmail's SMTP server in this example)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "vashishthaharishankar@gmail.com"  # Replace with your email
    load_dotenv()
    os.environ["EMAIL_PASSWORD"] = os.getenv("EMAIL_PASSWORD", "")
    sender_password = os.getenv("EMAIL_PASSWORD") # os.getenv("EMAIL_PASSWORD")  # Replace with your email password
    print(os.getenv("EMAIL_PASSWORD"))
    
    # Check if the candidate's shortlisted status is accept or reject
    if candidate_details["shortlisted_status"] == "accept":
        subject = f"Congratulations {candidate_details['candidate_name']} - You've been shortlisted!"
        body = f"""
        Dear {candidate_details['candidate_name']},

        We are pleased to inform you that you have been shortlisted for the position of {candidate_details['job_title']}.

        Contact Information:
        - Email: {candidate_details['candidate_email_id']}
        - Phone: {candidate_details['candidate_contact_no']}

        Your score is: {candidate_details['score']}

        Reason for Shortlisting:
        {candidate_details['reason_for_shortlisted_status']}

        Congratulations once again, and we look forward to moving forward with the next steps in the hiring process.

        Best Regards,
        Hiring Team
        """
    elif candidate_details["shortlisted_status"] == "reject":
        subject = f"Sorry {candidate_details['candidate_name']} - Your application status"
        body = f"""
        Dear {candidate_details['candidate_name']},

        Thank you for applying for the position of {candidate_details['job_title']}. Unfortunately, we regret to inform you that you have not been selected for the position.

        We appreciate your time and interest in the role and encourage you to apply for future opportunities.

        Best regards,
        Hiring Team
        """
    else:
        print("Invalid shortlisted status")
        return

    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = candidate_details["candidate_email_id"]
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            text = message.as_string()
            server.sendmail(sender_email, candidate_details["candidate_email_id"], text)
            print(f"Email sent successfully to {candidate_details['candidate_email_id']}")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")



def evaluate_candidate(job_title: str, job_description: str, resume_text: str):
    """
    This function evaluates the candidate's resume based on the provided job description and sends a shortlisted email if applicable.
    
    Parameters:
    job_title (str): The job title for which the candidate is being evaluated.
    job_description (str): The job description that the candidate's resume will be matched against.
    resume_text (str): The candidate's resume text to be analyzed.
    
    Returns:
    str: The result of the evaluation and whether an email was sent.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI bot. You are responsible for evaluating the similarity "
        "between a candidate’s resume and a job description. Based on the evaluation, "
        "you must output a JSON response that includes:\n\n"
         "- candidate_name: as provided in context\n"
        "- job_title: as provided in context\n"
        "- candidate_email_id: as provided in context\n"
        "- candidate_contact_no: as provided in context\n\n"
        "- score: a number from 0 to 100 based on how well the resume matches the job description\n"
        "- shortlisted_status: 'accept' if the candidate scores 80 or above, otherwise 'reject'\n"
        "- reason_for_shortlisted_status: a brief but clear explanation of the decision\n"
        "You must compare and score based on: relevant skills, work experience, education, certifications, "
        "and any other major factors stated in the job description. Be objective, fair, and clear in your evaluation."
        "Send the email using tool send_email to the candidate only if it "
        "is shortlisted with score greater than the threshold value."),
    
        ("human", "This is the Job Title:\n{job_title}\n\n"
        "This is the Job Description:\n{job_description}\n\n"
        "This is the Candidate Resume text content:\n{resume_text}\n\n"),
    
        ("ai", "{agent_scratchpad}")
    ])
    
    llm = AzureChatOpenAI(model=os.getenv("AZURE_OPENAI_MODEL"), max_retries=2, temperature=0.5)
    
    tools = [print_hello]
    llm_with_tools = llm.bind_tools(tools=tools)
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    
    # Run the agent executor with the provided parameters
    response = agent_executor.invoke({
        "job_title": job_title,
        "job_description": job_description,
        "resume_text": resume_text,
    })
    
    return parse_gpt_output(response["output"])

# Example usage:
# job_title = "Data Scientist"
# job_description = """
# We are looking for a skilled Data Scientist to analyze complex datasets, develop predictive models, and provide actionable insights. You will collaborate with cross-functional teams to optimize business strategies and drive data-driven decision-making.

# Responsibilities:
# Collect, clean, and analyze large datasets.
# Develop and deploy machine learning models.
# Build predictive analytics solutions to improve business outcomes.
# Communicate findings through reports and visualizations.
# Stay updated with advancements in data science and AI.
# Qualifications:
# Bachelor�s or Master�s degree in Data Science, Computer Science, or a related field.
# Proficiency in Python, R, SQL, and machine learning frameworks.
# Experience with data visualization tools like Tableau or Power BI.
# Strong analytical and problem-solving skills.
# Ability to work independently and in a team environment."
# """
# resume_text = """

# 1
# Candidate Resume (ID: C1070)
# Name: Scott Saunders
# Email: scottsaunders13@gmail.com
# Phone: +1-367-5130
# Education
# Bachelor of Engineering in Information Technology (2014-2018)
# Concentrated on database management, networking, and cybersecurity.
# Master of Business Administration (2017-2019)
# Focused on Business Strategy, Financial Analysis, and Operations Management.
# Ph.D. in Artificial Intelligence (2016-2021)
# Research in NLP and Computer Vision, with publications in top-tier conferences.
# Work Experience
# Software Engineer at XYZ Corp (2018-2022)
# Developed scalable backend applications, improved system efficiency by 30%, and led agile
# development sprints.
# Skills
# Python & Machine Learning - Proficient in TensorFlow, PyTorch, and Scikit-learn with hands-on
# experience in deploying AI solutions.
# Certifications
# AWS Certified Solutions Architect - Validated expertise in designing and deploying scalable AWS
# solutions, optimizing performance and security.
# Achievements
# Developed an AI chatbot - Built a chatbot that reduced customer support tickets by 40%, enhancing
# user experience and efficiency.
# Tech Stack
# Python, TensorFlow, PyTorch, PostgreSQL, Docker, Kubernetes
# """

# response = evaluate_candidate(job_title, job_description, resume_text)
# print(response)
