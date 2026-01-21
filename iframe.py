import streamlit as st
import requests
from datetime import datetime
import json
import time
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(
    page_title="Shivohm AI Assistant",
    page_icon="🤖",
    layout="centered",  # Changed to centered for better iframe display
    initial_sidebar_state="collapsed"  # Collapsed by default for iframe
)

# Custom CSS optimized for iframe embedding
st.markdown("""
<style>
    /* Hide Streamlit branding and menu for iframe */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Remove padding for compact iframe view */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Make iframe scrollable */
    .main {
        overflow-y: auto;
    }
    
    .main-header {
        background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .chat-container {
        height: 400px;
        overflow-y: auto;
        padding: 10px;
        background: white;
        border-radius: 10px;
        border: 2px solid #E5E7EB;
        margin-bottom: 15px;
    }
    
    .chat-message {
        padding: 12px 16px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
        word-wrap: break-word;
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .user-message {
        background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
        margin-left: auto;
        color: #1F2937;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .assistant-message {
        background-color: #F3F4F6;
        margin-right: auto;
        color: #1F2937;
        border: 1px solid #E5E7EB;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
        color: #1F2937;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        transition: all 0.3s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .stTextInput>div>div>input {
        border-radius: 10px;
        border: 2px solid #E5E7EB;
        transition: border-color 0.3s;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #FCD34D;
        box-shadow: 0 0 0 3px rgba(252, 211, 77, 0.1);
    }
    
    .info-banner {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        text-align: center;
        font-size: 0.9em;
    }
    
    .powered-by {
        text-align: center;
        color: #6B7280;
        padding: 10px;
        font-size: 0.85em;
        margin-top: 10px;
    }
    
    /* Compact sidebar for iframe */
    .css-1d391kg {
        padding: 1rem;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        color: #1F2937;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    
    .contact-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        border-left: 4px solid #FCD34D;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = "https://3d866683c5e5.ngrok-free.app"
DEMO_MODE = False  # Set to True for testing without backend
DEBUG_MODE = False  # Show debug info

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm Shivohm's AI assistant. How can I help you today?"}
    ]
if 'session_id' not in st.session_state:
    st.session_state.session_id = None

# Demo mode mock response
def get_mock_response(query):
    """Mock response for demo mode"""
    time.sleep(1)
    
    query_lower = query.lower()
    
    contact_keywords = ['connect', 'contact', 'reach', 'touch', 'call', 'email', 'meeting', 'demo', 
                       'expert', 'team', 'talk', 'speak', 'introduce', 'form']
    show_contact = any(keyword in query_lower for keyword in contact_keywords)
    
    if show_contact:
        answer = "I'd love to help connect you with our team! You can reach out to us through our contact page: https://shivohm.com/contact-us/"
    elif 'service' in query_lower or 'solution' in query_lower:
        answer = "Shivohm offers comprehensive AI and technology solutions including custom software development, cloud services, data analytics, and AI/ML consulting. We've successfully delivered 170+ projects across various industries!"
    elif 'ui' in query_lower or 'ux' in query_lower or 'design' in query_lower:
        answer = "Yes, we do offer UI/UX design services! Our team focuses on creating user-friendly and visually appealing interfaces that enhance user experience. If you'd like to discuss your project in detail, feel free to contact us at: https://shivohm.com/contact-us/"
    elif 'project' in query_lower:
        answer = "We've completed over 170 projects with a 98% client satisfaction rate! Our work spans from enterprise applications to AI-powered solutions. Would you like to know more about any specific type of project?"
    elif 'team' in query_lower:
        answer = "Our team consists of 150+ skilled professionals including developers, designers, data scientists, and AI specialists. We have 7+ years of experience delivering cutting-edge technology solutions."
    else:
        answer = "I'm here to help! Could you tell me more about what you're looking for? Whether it's about our services, past projects, or how we can help your business, I'm all ears! 😊"
    
    return {
        "answer": answer,
        "sources": [],
        "session_id": "demo-session"
    }

# API call function
def call_chat_api(user_input):
    """Call the chat API or use mock response"""
    if DEMO_MODE:
        return get_mock_response(user_input)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "query": user_input,
                "session_id": st.session_state.session_id,
                "top_k": 5
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to API. Enable DEMO_MODE or start the backend.")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Compact Header
st.markdown("""
<div class="main-header">
    <h2 style="margin:0; color:#1F2937; font-size: 1.8em;">🤖 Shivohm AI Assistant</h2>
    <p style="margin:5px 0 0 0; color:#374151; font-size: 0.95em;">Your intelligent guide to our services</p>
</div>
""", unsafe_allow_html=True)

# Mode banner
if DEMO_MODE:
    st.markdown("""
    <div class="info-banner">
        <strong>🎭 DEMO MODE</strong> - Simulated responses
    </div>
    """, unsafe_allow_html=True)

# Compact Sidebar
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%); border-radius: 10px; margin-bottom: 15px;">
        <h2 style="margin:0; color:#1F2937; font-size: 1.5em;">SHIVOHM</h2>
        <p style="margin:0; color:#374151; font-size: 0.85em;">Technology Solutions</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📊 Track Record")
    
    st.markdown("""
    <div class="stat-card">
        <h3 style="margin:0; font-size:1.8em;">170+</h3>
        <p style="margin:5px 0 0 0; font-size:0.85em;">Projects</p>
    </div>
    <div class="stat-card">
        <h3 style="margin:0; font-size:1.8em;">150+</h3>
        <p style="margin:5px 0 0 0; font-size:0.85em;">Team Members</p>
    </div>
    <div class="stat-card">
        <h3 style="margin:0; font-size:1.8em;">7+</h3>
        <p style="margin:5px 0 0 0; font-size:0.85em;">Years Experience</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📞 Contact")
    st.markdown("""
    <div class="contact-card">
        <p style="margin:5px 0;"><strong>📧</strong> <a href="mailto:info@shivohm.com" style="color:#F59E0B;">info@shivohm.com</a></p>
        <p style="margin:5px 0;"><strong>📱</strong> <a href="tel:+919081112202" style="color:#F59E0B;">+91-90811-12202</a></p>
        <p style="margin:5px 0;"><strong>🌐</strong> <a href="https://shivohm.com" target="_blank" style="color:#F59E0B;">www.shivohm.com</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm Shivohm's AI assistant. How can I help you today?"}
        ]
        st.session_state.session_id = None
        st.rerun()

# Chat messages display
st.markdown("### 💬 Chat")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
user_input = st.chat_input("Type your message here... 💬")

if user_input:
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    with st.spinner("🤔 Thinking..."):
        data = call_chat_api(user_input)

    if data:
        if data.get("session_id"):
            st.session_state.session_id = data["session_id"]

        st.session_state.messages.append(
            {"role": "assistant", "content": data["answer"]}
        )

    st.rerun()

# Compact Footer
st.markdown("""
<div class="powered-by">
    Powered by <strong>Shivohm AI</strong> | <a href="https://shivohm.com" target="_blank" style="color:#F59E0B;">www.shivohm.com</a>
</div>
""", unsafe_allow_html=True)