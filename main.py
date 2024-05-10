import openai
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from datetime import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Get the endpoint and key from environment variables
endpoint = os.getenv("ENDPOINT")
key = os.getenv("KEY")
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

def analyze_read_and_return():
    # sample document
    formUrl = "https://quadz.blob.core.windows.net/newpoc/91.jpeg"
    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )
    
    poller = document_analysis_client.begin_analyze_document_from_url(
            "prebuilt-read", formUrl)
    result = poller.result()

    # Extracted text
    extracted_text = result.content

    return extracted_text

if __name__ == "__main__":
    extracted_text = analyze_read_and_return()
    # print(extracted_text)  # or do whatever you want with the extracted text variable


def get_completion(prompt, model="gpt-3.5-turbo"):
    messages = [{"role": "user", "content": prompt}]
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0, # this is the degree of randomness of the model's output
    )
    return completion.choices[0].message

details1 = f"""
You will be provided with the cheque details in triple quotes.

extract below details

- Bank Name
- Branch Name
- IFSC Code / IFSCCode
- Account Number

'''{extracted_text}'''

"""

bank_details = get_completion(details1)
print(bank_details.content)


