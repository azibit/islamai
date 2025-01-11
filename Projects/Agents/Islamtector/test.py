import gradio as gr
from youtube_transcript_api import YouTubeTranscriptApi
import json
import requests

# OpenAI Endpoint: https://aiiionmodelshu1205052997.openai.azure.com/
# Inference Endpoint: https://aiiionmodelshu1205052997.services.ai.azure.com/models
# Models deployed: Gpt-4o, Gpt-4o-mini
# Version: 2024-08-06
# Requests per minute (RPM): 4.5K (Gpt-4o)
# Tokens per minute: 450K (Gpt-4o)
# Tokens per minute: 2 million (Gpt-4o-mini)
# Corresponding Requests per minute (RPM) = 20K (Gpt-4o-mini)

import os  
import base64
from openai import AzureOpenAI  


def call_api_model(prompt_message):
    endpoint = os.getenv("ENDPOINT_URL", "https://aiiionmodelshu1205052997.openai.azure.com/")  
    deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini")  
    subscription_key = os.getenv("SUBSCRIPTION_KEY_1", "SUBSCRIPTION_KEY_1")

    print("Subscription Key: ", subscription_key)

    # Initialize Azure OpenAI client with key-based authentication    
    client = AzureOpenAI(  
        azure_endpoint=endpoint,  
        api_key=subscription_key,  
        api_version="2024-05-01-preview",  
    )
        
        
    # IMAGE_PATH = "YOUR_IMAGE_PATH"
    # encoded_image = base64.b64encode(open(IMAGE_PATH, 'rb').read()).decode('ascii')

    #Prepare the chat prompt 
    chat_prompt = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an AI assistant that helps people find information."
                },
                {
                    "type": "user",
                    "image": "What is your name?",
                }
            ]
        }
    ] 
        
    # Include speech result if speech is enabled  
    messages = chat_prompt  
        
    # Generate the completion  
    # completion = client.chat.completions.create(  
    #     model=deployment,  
    #     messages=messages,  
    #     max_tokens=800,  
    #     temperature=0.7,  
    #     top_p=0.95,  
    #     frequency_penalty=0,  
    #     presence_penalty=0,  
    #     stop=None,  
    #     stream=False
    # )

    completion = client.chat.completions.create(model = deployment,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": prompt_message
            }
        ])

    print("Completion: ", json.loads(completion.to_json())['choices'][0]['message']['content'])
    return json.loads(completion.to_json())['choices'][0]['message']['content']

def get_video_id(url):
    """Extract video ID from YouTube URL"""
    if "youtu.be" in url:
        return url.split("/")[-1]
    elif "youtube.com" in url:
        return url.split("v=")[1].split("&")[0]
    return url

def process_video(youtube_url, prompt_template="Please summarize this transcript: "):
    try:
        # Get transcript
        video_id = get_video_id(youtube_url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Format transcript
        formatted_transcript = ""
        for entry in transcript:
            formatted_transcript += f"{entry['text']} "
        
        # Combine prompt template with transcript
        full_prompt = prompt_template + formatted_transcript
        
        # Get AI response
        ai_response = call_api_model(full_prompt)
        
        return formatted_transcript, ai_response
    except Exception as e:
        return f"Error: {str(e)}", f"Error: Could not process transcript - {str(e)}"

# Create Gradio interface
iface = gr.Interface(
    fn=process_video,
    inputs=[
        gr.Textbox(label="YouTube URL", placeholder="Enter YouTube video URL..."),
        gr.Textbox(label="Prompt Template", value="Please summarize this transcript: ", lines=2)
    ],
    outputs=[
        gr.Textbox(label="Transcript", lines=10),
        gr.Textbox(label="AI Analysis", lines=10)
    ],
    title="YouTube Video Transcript Analyzer",
    description="Enter a YouTube video URL to get its transcript and AI analysis.",
    examples=[["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Please summarize this transcript: "]]
)

# Launch the interface
if __name__ == "__main__":
    iface.launch()