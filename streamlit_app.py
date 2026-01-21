import streamlit as st
import requests
from datetime import datetime
import json
import time

# Page configuration
st.set_page_config(
    page_title="Shivohm AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with improved styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .chat-message {
        padding: 15px 20px;
        border-radius: 18px;
        margin-bottom: 12px;
        max-width: 75%;
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
    
    .contact-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border-left: 4px solid #FCD34D;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
        padding: 25px;
        border-radius: 12px;
        text-align: center;
        color: #1F2937;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%);
        color: #1F2937;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        transition: all 0.3s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div>select {
        border-radius: 10px;
        border: 2px solid #E5E7EB;
        transition: border-color 0.3s;
    }
    
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus,
    .stSelectbox>div>div>select:focus {
        border-color: #FCD34D;
        box-shadow: 0 0 0 3px rgba(252, 211, 77, 0.1);
    }
    
    .info-banner {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        margin: 10px 0;
        text-align: center;
    }
    
    .debug-info {
        background: #FEF3C7;
        border: 2px solid #FCD34D;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.85em;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = "http://localhost:8000"
DEMO_MODE = False  # Set to True for testing without backend
DEBUG_MODE = False  # Show debug info

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm Shivohm's AI assistant. How can I help you today? Feel free to ask about our services, projects, or anything else!"}
    ]
if 'session_id' not in st.session_state:
    st.session_state.session_id = None

# Demo mode mock response
def get_mock_response(query):
    """Mock response for demo mode"""
    time.sleep(1)
    
    query_lower = query.lower()
    
    # Enhanced contact detection
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
            if DEBUG_MODE:
                st.write("**Debug - API Response:**", data)
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

# Header
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; color:#1F2937; font-size: 2.5em;">🤖 Shivohm AI Assistant</h1>
    <p style="margin:5px 0 0 0; color:#374151; font-size: 1.1em;">Your intelligent guide to our services and solutions</p>
</div>
""", unsafe_allow_html=True)

# Debug info
if DEBUG_MODE:
    st.markdown(f"""
    <div class="debug-info">
        <strong>🔍 Debug Info:</strong><br>
        Demo Mode: {DEMO_MODE}<br>
        Session ID: {st.session_state.session_id}<br>
        Messages Count: {len(st.session_state.messages)}
    </div>
    """, unsafe_allow_html=True)

# Mode banner
if DEMO_MODE:
    st.markdown("""
    <div class="info-banner">
        <strong>🎭 DEMO MODE</strong> - Using simulated responses. Connect to backend API for full functionality.
    </div>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%); border-radius: 10px; margin-bottom: 20px;">
        <h1 style="margin:0; color:#1F2937; font-size: 2em;">SHIVOHM</h1>
        <p style="margin:0; color:#374151; font-size: 0.9em;">Technology Solutions</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📊 Our Track Record")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="stat-card">
            <h2 style="margin:0; font-size:2.5em;">170+</h2>
            <p style="margin:5px 0 0 0; font-size:0.9em;">Projects Delivered</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="stat-card">
            <h2 style="margin:0; font-size:2.5em;">20+</h2>
            <p style="margin:5px 0 0 0; font-size:0.9em;">Happy Clients</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("""
        <div class="stat-card">
            <h2 style="margin:0; font-size:2.5em;">150+</h2>
            <p style="margin:5px 0 0 0; font-size:0.9em;">Team Members</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="stat-card">
            <h2 style="margin:0; font-size:2.5em;">7+</h2>
            <p style="margin:5px 0 0 0; font-size:0.9em;">Years Experience</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📞 Quick Contact")
    st.markdown("""
    <div class="contact-card">
        <p style="margin:10px 0;"><strong>📧 Email:</strong><br/>
        <a href="mailto:info@shivohm.com" style="color:#F59E0B;">info@shivohm.com</a></p>
        <p style="margin:10px 0;"><strong>📱 Phone:</strong><br/>
        <a href="tel:+919081112202" style="color:#F59E0B;">+91-90811-12202</a></p>
        <p style="margin:10px 0;"><strong>🌐 Website:</strong><br/>
        <a href="https://shivohm.com" target="_blank" style="color:#F59E0B;">www.shivohm.com</a></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🌐 Visit Contact Page", use_container_width=True):
        st.markdown('<meta http-equiv="refresh" content="0;url=https://shivohm.com/contact-us/">', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm Shivohm's AI assistant. How can I help you today?"}
        ]
        st.session_state.session_id = None
        st.rerun()

# Chat section (full width now - no contact form)
st.markdown("### 💬 Chat")

# Chat messages container
chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
                <div class="chat-message user-message">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
                <div class="chat-message assistant-message">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Type your message here... 💬")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Get response
    with st.spinner("🤔 Thinking..."):
        data = call_chat_api(user_input)
        
        if data:
            # Update session ID
            if data.get("session_id"):
                st.session_state.session_id = data["session_id"]
            
            # Add assistant response
            st.session_state.messages.append({
                "role": "assistant",
                "content": data["answer"]
            })
    
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6B7280; padding: 20px;">
    <p style="margin:5px 0;">Powered by <strong>Shivohm AI</strong> | 
    <a href="https://shivohm.com" target="_blank" style="color:#F59E0B;">www.shivohm.com</a></p>
    <p style="margin:5px 0; font-size:0.9em;">© 2024 Shivohm Technologies. All rights reserved.</p>
</div>
""", unsafe_allow_html=True)