import os
import json
import urllib.parse
import base64
import requests
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables from .env file
load_dotenv()

# Get the endpoint and key from environment variables
endpoint = os.getenv("ENDPOINT")
key = os.getenv("KEY")
api_key = os.getenv("OPENAI_API_KEY")

# Initialize Document Analysis Client
document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

def analyze_document(document_url):
    # Decode the URL to handle special characters
    document_url_decoded = urllib.parse.unquote(document_url)
    
    # Initialize variables
    new_ration_card_number = None
    old_ration_card_number = None
    ration_card_detected = False
    bank_cheque_detected = False
    document_type = None

    # Analyze document for Ration Card and Bank Cheque
    poller_ration = document_analysis_client.begin_analyze_document_from_url("prebuilt-document", document_url_decoded)
    result_ration = poller_ration.result()

    for kv_pair in result_ration.key_value_pairs:
        if kv_pair.key and kv_pair.value:
            if "New Ration Card No" in kv_pair.key.content:
                new_ration_card_number = kv_pair.value.content
                ration_card_detected = True
            elif "Old RationCard No" in kv_pair.key.content or "Old RCNo" in kv_pair.key.content:
                old_ration_card_number = kv_pair.value.content
                ration_card_detected = True
            elif any(term in kv_pair.key.content for term in ["A/C No", "account No", "IFSCCode", "IFSC Code", "IFS Code"]):
                document_type = "bank cheque"
                bank_cheque_detected = True
                break

    if not bank_cheque_detected:
        # Analyze document for Aadhar or PAN card
        poller_id = document_analysis_client.begin_analyze_document_from_url("prebuilt-idDocument", document_url_decoded)
        id_documents = poller_id.result()

        for idx, id_document in enumerate(id_documents.documents):
            document_number = id_document.fields.get("DocumentNumber")
            if document_number:
                doc_number = document_number.value.replace(" ", "")  # Remove spaces for processing
                if len(doc_number) == 12 and doc_number.isdigit():
                    document_type = "Aadhar card"
                    break
                elif len(doc_number) == 10 and doc_number[:5].isalpha() and doc_number[5:9].isdigit() and doc_number[-1].isalpha():
                    document_type = "PAN card"
                    break

    document_details = None
    if document_type == "Aadhar card":
        print("Given document is an Aadhar card")
        document_details = extract_aadhar_pan_details(document_url)
    elif document_type == "PAN card":
        print("Given document is a PAN card")
        document_details = extract_aadhar_pan_details(document_url)
    elif ration_card_detected:
        print("Given document is a Ration Card")
        document_details = extract_rationcard_details(document_url)
    elif bank_cheque_detected:
        print("Given document is a Bank Cheque")
        document_details = extract_bank_cheque_details(document_url)
    else:
        print("Document type is unknown")
        document_type = identify_document_type(document_url_decoded)
        if document_type == "Aadhar card":
            print("Given document is an Aadhar card")
            document_details = extract_aadhar_pan_details(document_url)
        else:
            document_details = {
                "Name": None,
                "Aadhar Number": None,
                "Pan Number": None,
                "Fathers Name": None,
                "DateOfBirth": None,
                "Ration_card_details": None
            }
            print("Document type is unknown")
            print("Name: ", document_details["Name"])
            print("Aadhar Number: ", document_details["Aadhar Number"])
            print("Pan Number: ", document_details["Pan Number"])
            print("Fathers Name: ", document_details["Fathers Name"])
            print("DateOfBirth: ", document_details["DateOfBirth"])
            print("Ration_card_details:", document_details["Ration_card_details"])

    return document_type, document_details

def identify_document_type(document_url):
    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-document", document_url)
    result = poller.result()

    for kv_pair in result.key_value_pairs:
        if kv_pair.key and kv_pair.value and kv_pair.key.content == "Your Aadhaar No. :":
            return "Aadhar card"
    return "Unknown"

def encode_image_from_url(image_url):
    image_data = requests.get(image_url).content
    return base64.b64encode(image_data).decode('utf-8')

def extract_aadhar_pan_details(document_url):
 # Get the base64 string from the document URL
    base64_image = encode_image_from_url(document_url)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please extract Name, Aadhar number, Pan Number, DateofBirth, Fathers Name and address from the image"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 500
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response_data = json.loads(response.content)

    # Extract relevant details
    message_content = response_data['choices'][0]['message']['content']
    return message_content


def extract_rationcard_details(document_url):
    # Get the base64 string from the document URL
    base64_image = encode_image_from_url(document_url)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4-turbo",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Read the image and extract data from the image"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 500
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    # print(response.content)
    response_data = json.loads(response.content)

    # Extract relevant details
    message_content = response_data['choices'][0]['message']['content']

    # Print relevant details
    print(message_content)

def extract_bank_cheque_details(document_url):
    # Analyze document to extract text
    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-read", document_url)
    result = poller.result()

    # Extracted text
    extracted_text = result.content

    def get_completion(prompt, model="gpt-4o"):
        messages = [{"role": "user", "content": prompt}]
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages}
        )
        response_data = response.json()
        return response_data['choices'][0]['message']['content']

    details_prompt = f"""
    You will be provided with the cheque details in triple quotes.

    Extract the following details:
    - Bank Name
    - Branch Name
    - IFSC Code / IFSCCode
    - Account Number

    '''{extracted_text}'''
    """

    bank_details = get_completion(details_prompt)
    # print(bank_details)
    return bank_details

if __name__ == "__main__":
    document_url = "https://quadz.blob.core.windows.net/newpoc/Media 1.jpg"
    document_type, document_details = analyze_document(document_url)
    print(f"Document Type: {document_type}")
    print(f"Document Details: {document_details}")
