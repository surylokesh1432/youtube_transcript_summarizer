import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from googletrans import Translator
from gtts import gTTS
import base64
import asyncio
# Load environment variables
load_dotenv()

# Retrieve the API key from the environment variable
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("API Key not found. Please ensure that the GOOGLE_API_KEY is set in the .env file.")
else:
    # Configure Google Generative AI with API key
    genai.configure(api_key=api_key)

# Define the prompt for the summarizer
prompt = """
You are a YouTube video summarizer. You will take the transcript text
and summarize the entire video, providing the important points within 250 words.
Please provide the summary of the text given here:
"""
# Language codes and their full names
languages = {
    "en": "English",
    "bn": "Bengali",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "es": "Spanish",
    "ta": "Tamil",
    "te": "Telugu",
}

# Function to extract transcript details from YouTube
def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("v=")[1]
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        try:
            transcript = transcript_list.find_transcript(['en'])
        except:
            pass
        if not transcript:
            for available_transcript in transcript_list:
                transcript = available_transcript
                break
        transcript_text = transcript.translate('en').fetch()
        transcript = " ".join([i.text for i in transcript_text])
        return transcript
    except TranscriptsDisabled:
        st.error("Transcripts are disabled for this video.")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Function to generate content using Google Generative AI
def generate_gemini_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    try:
        response = model.generate_content(prompt + transcript_text)
        if response and hasattr(response, 'text'):
            return response.text
        else:
            raise ValueError("Failed to generate summary. Please check the response details.")
    except Exception as e:
        st.error(f"An error occurred while generating content: {e}")
        return None

# Function to translate text


def translate_text(text, target_language):
    try:
        translator = Translator()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        translated = loop.run_until_complete(translator.translate(text, dest=target_language))
        return translated.text
    except Exception as e:
        st.error(f"Translation Error: {e}")
        return None


# Function to convert text to speech
def text_to_speech(text, lang):
    tts = gTTS(text, lang=lang)
    tts.save("detailed_notes.mp3")
    return "detailed_notes.mp3"

# Streamlit page configuration
st.set_page_config(page_title="YouTube Transcript to Detailed Notes Converter", layout="centered")

# Streamlit title
st.title("YouTube Transcript to Detailed Notes Converter")

# Streamlit markdown for styling
st.markdown("""
<style>
    .title {
        text-align: center;
        font-size: 2em;
        font-weight: bold;
        color: #4CAF50;
    }
    .header-image {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 50%;
    }
    .note {
        font-size: 1em;
        margin-top: 20px;
        padding: 10px;
        border-right: 3px solid #4CAF50;
        background-color: inherit;
    }
    .button {
        margin-top: 10px;
    }
    @media (prefers-color-scheme: dark) {
            .note {
                color: white;
                background-color: #333;
            }
        }
    @media (prefers-color-scheme: light) {
            .note {
                color: black;
                background-color: #fff;
            }
        }
</style>
""", unsafe_allow_html=True)

# Input field for YouTube link
youtube_link = st.text_input("Enter YouTube Video Link:")

# Display embedded YouTube video if link is provided
if youtube_link:
    video_id = youtube_link.split("v=")[1]
    st.markdown(f"""
        <iframe width="100%" height="315" src="https://www.youtube.com/embed/{video_id}" 
        frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
        allowfullscreen></iframe>
    """, unsafe_allow_html=True)

# State variables
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None

# Button to get detailed notes
if st.button("Get Detailed Notes"):
    with st.spinner("Extracting transcript and generating summary..."):
        transcript_text = extract_transcript_details(youtube_link)
        if transcript_text:
            summary = generate_gemini_content(transcript_text, prompt)
            if summary:
                st.session_state.transcript_text = transcript_text
                st.session_state.summary = summary
            else:
                st.error("Failed to generate summary.")
        else:
            st.error("Failed to extract transcript or generate summary. Please check the video link and try again.")

# Display detailed notes and language selection if summary is generated
if st.session_state.summary:
    # Select box for output language
    output_language_code = st.selectbox("Select Output Language for Detailed Notes:", list(languages.keys()), format_func=lambda x: languages[x])
    translated_summary = translate_text(st.session_state.summary, output_language_code)
    
    if translated_summary:
        st.markdown("## 📄 Detailed Notes:")
        audio_file = text_to_speech(translated_summary, output_language_code)
        st.session_state.audio_file = audio_file
        st.audio(audio_file, format='audio/mp3')
        st.markdown(f'<div class="note" id="notes">{translated_summary}</div>', unsafe_allow_html=True)
    else:
        st.error("Translation failed. Please try again.")

def download_link(object_to_download, download_filename, download_link_text):
    b64 = base64.b64encode(object_to_download.encode()).decode()
    return f'<a href="data:text/plain;base64,{b64}" download="{download_filename}">{download_link_text}</a>'

# Display download link if summary is available
if st.session_state.summary:
    st.markdown(download_link(st.session_state.summary, 'detailed_notes.txt', 'Download Detailed Notes'), unsafe_allow_html=True)