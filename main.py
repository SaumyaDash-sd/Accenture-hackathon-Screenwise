import streamlit as st
import pandas as pd
import zipfile
import os
import io
from io import StringIO
import PyPDF2
import docx
import csv


from agent_call import evaluate_candidate
from agent_call import send_email

# Sample function to process the files
def process_files(uploaded_file, uploaded_csv):
    data = []
    for file_name, file_content in uploaded_file:  # Unpack file_name and file_content
        file_type = file_name.split('.')[-1].lower()  # Get the file extension
        
        try:
            if file_type == 'pdf':
                text = extract_text_from_pdf(file_content)
            elif file_type == 'docx':
                text = extract_text_from_docx(file_content)
            else:
                text = 'Unsupported format'
        except PyPDF2.errors.PdfReadError:
            text = 'Error reading PDF file'
        
        # Append data to list
        df = pd.read_csv(uploaded_csv, encoding='ISO-8859-1')
        for index, row in df.iterrows():
            job_title = row['Job Title']  # Replace with your actual column names
            description = row['Job Description']  # Replace with your actual column names
            json_response = evaluate_candidate(job_title, description, text)
            send_email(json_response)
            data.append(json_response)
        # data.append({'file_name': file_name, 'file_type': file_type, 'content': text})
    return pd.DataFrame(data)


# Function to extract text from PDF
def extract_text_from_pdf(file_content):
    try:
        pdf_reader = PyPDF2.PdfReader(file_content)
        text = ""
        for page in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page].extract_text()
        return text
    except PyPDF2.errors.PdfReadError as e:
        st.write(f"Error reading PDF: {e}")
        return ""  # Return empty string if PDF cannot be read

# Function to extract text from DOCX
def extract_text_from_docx(file_content):
    doc = docx.Document(file_content)
    text = ""
    for para in doc.paragraphs:
        text += para.text
    return text

# Function to extract files from a zip
def extract_files_from_zip(zip_file):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall("temp_folder")
    
    extracted_files = []
    for root, dirs, filenames in os.walk("temp_folder"):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            
            # Skip macOS system files like those starting with '._'
            if filename.startswith('._') or filename.startswith('__MACOSX'):
                continue  # Skip these files
            
            with open(file_path, "rb") as f:
                file_content = io.BytesIO(f.read())  # Read file into BytesIO
                extracted_files.append((filename, file_content))  # Store (file_name, file_content)
    
    return extracted_files





# Streamlit app
def app():
    st.title("Resume Processing Tool")
    
    tab1, tab2 = st.tabs(["Upload Single Resume", "Upload Bulk Resume"])
    
    # Tab 1: Upload Single Resume
    with tab1:
        st.header("Upload Single Resume")
        
        # File uploader for one PDF or DOCX file
        uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
        
        # File uploader for CSV file
        uploaded_csv = st.file_uploader("Upload CSV File", type=["csv"])
        
        # Button to submit and process the files
        if st.button("Submit Single Resume", key="submit_single"):
            if uploaded_file is not None and uploaded_csv is not None:
                st.write("Processing files...")
                result_df = process_files([(uploaded_file.name, uploaded_file)], uploaded_csv)
                st.dataframe(result_df)
                
                csv_buffer = StringIO()
                result_df.to_csv(csv_buffer, index=False)
                st.download_button("Download Processed CSV", csv_buffer.getvalue(), file_name="processed_resumes.csv")
            else:
                st.warning("Please upload both a resume and a CSV file.")
    
    # Tab 2: Upload Bulk Resume
    with tab2:
        st.header("Upload Bulk Resumes (ZIP)")
        
        # File uploader for a zip file containing multiple PDF or DOCX files
        uploaded_zip = st.file_uploader("Upload ZIP File with Resumes", type=["zip"])
        
        # File uploader for CSV file for bulk resumes
        uploaded_csv_bulk = st.file_uploader("Upload CSV File for Bulk Resumes", type=["csv"])
        
        # Button to submit and process the files
        if st.button("Submit Bulk Resume", key="submit_bulk"):
            if uploaded_zip is not None and uploaded_csv_bulk is not None:
                st.write("Extracting and processing files from ZIP...")
                extracted_files = extract_files_from_zip(uploaded_zip)
                
                result_df = process_files(extracted_files, uploaded_csv)
                st.dataframe(result_df)
                
                csv_buffer = StringIO()
                result_df.to_csv(csv_buffer, index=False)
                st.download_button("Download Processed CSV", csv_buffer.getvalue(), file_name="processed_resumes.csv")
            else:
                st.warning("Please upload both a ZIP file containing resumes and a CSV file.")

if __name__ == "__main__":
    app()
