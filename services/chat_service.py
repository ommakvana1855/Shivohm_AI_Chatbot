from openai import OpenAI
from typing import List, Dict, Any, Optional
import uuid
from config.settings import settings
from database.mongo_client import MongoDatabase
from services.retrieval_service import RetrievalService


class ChatService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.CHAT_MODEL
        self.mongo_db = MongoDatabase()
        self.retrieval_service = RetrievalService()
        
        # Contact URL
        self.contact_url = "https://shivohm.com/contact-us/"
        
        # Expanded keywords for contact intent detection
        self.contact_keywords = [
            'contact', 'reach out', 'get in touch', 'talk to', 'speak with',
            'call', 'email', 'phone', 'connect', 'meeting', 'demo',
            'consultation', 'discuss', 'sales', 'inquiry', 'quote',
            'schedule', 'appointment', 'book', 'meet', 'connect with team',
            'talk to someone', 'representative', 'support', 'help me connect',
            'connect me', 'introduce me', 'put me in touch', 'reach your team',
            'contact form', 'fill out', 'get started', 'sign up',
            'connect with expert', 'talk to expert', 'speak to expert',
            'connect you', 'reach you', 'contact you', 'talk with you'
        ]
    
    def _detect_contact_intent(self, query: str) -> bool:
        """Detect if user wants to contact the company"""
        query_lower = query.lower()
        
        # Phrases that strongly indicate contact intent
        strong_contact_phrases = [
            'connect with', 'talk to', 'speak with', 'speak to',
            'reach out', 'get in touch', 'contact', 
            'meet with', 'meeting', 'demo',
            'schedule', 'book', 'appointment',
            'connect me', 'introduce me', 'put me in touch',
            'connect you', 'reach you', 'talk with you',
            'connect your', 'reach your', 'talk to your',
            'expert', 'team', 'representative', 'sales'
        ]
        
        # Check if any phrase exists in the query
        for phrase in strong_contact_phrases:
            if phrase in query_lower:
                print(f"✅ CONTACT DETECTED - Matched phrase: '{phrase}'")  # Debug
                return True
        
        # If no phrase matched
        print(f"❌ NO CONTACT DETECTED - Query: {query_lower}")  # Debug
        return False
    
    def chat(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process a chat query with RAG"""
        # Create or retrieve session
        if not session_id:
            session_id = str(uuid.uuid4())
            self.mongo_db.create_session(session_id)
        
        # Check for contact intent
        has_contact_intent = self._detect_contact_intent(query)
        
        # Log detection for debugging
        print(f"Query: {query}")
        print(f"Contact intent detected: {has_contact_intent}")
        
        # Retrieve relevant context
        retrieval_results = self.retrieval_service.retrieve_relevant_context(
            query,
            top_k
        )
        context = self.retrieval_service.get_context_string(retrieval_results)
        
        # Get conversation history
        history = self.mongo_db.get_session_history(session_id)
        
        # Build messages for OpenAI with enhanced system prompt
        system_content = f"""You are Shivohm's friendly AI assistant, here to help with questions about our services and solutions.

Your personality:
- Warm, helpful, and conversational - like talking to a knowledgeable colleague
- Enthusiastic about technology and how it can solve real business problems
- Professional but approachable - avoid overly formal or robotic language
- Concise and clear - get to the point quickly without long-winded explanations

Response guidelines:
- Keep answers brief and conversational (2-4 sentences for simple questions)
- Use natural, flowing language - no bullet points unless specifically asked
- When discussing our services, be informative but not sales-pushy
- If you don't know something from the context, be honest and offer to connect them with our team
- Sprinkle in relevant details about Shivohm naturally (like "We've delivered 170+ projects" or "Our team of 150+ experts")
- For technical questions, explain clearly without overwhelming jargon
- Always be ready to ask follow-up questions to better understand their needs

Context from our knowledge base:
{context}"""

        # Add special instruction if contact intent detected
        if has_contact_intent:
            system_content += f"""

IMPORTANT: The user wants to connect with the team or get in touch. Provide them with our contact page URL in a friendly, natural way.

Use ONE of these response styles:
- "I'd love to help connect you with our team! You can reach out to us here: {self.contact_url}"
- "Great! Our team would be happy to discuss this with you. Please visit our contact page: {self.contact_url}"
- "Perfect! To connect with our experts, please visit: {self.contact_url}"
- "I can help with that! Feel free to reach out to our team at: {self.contact_url}"

Keep your response brief (1-2 sentences) and always include the contact URL.
"""
        else:
            system_content += """

If the answer isn't in the context, let the user know conversationally and offer alternative help like connecting them with our team at info@shivohm.com or calling +91-90811-12202."""

        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history (keep last 5 exchanges for context)
        for msg in history[-5:]:  
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current query
        messages.append({
            "role": "user",
            "content": query
        })
        
        # Get response from OpenAI with conversational parameters
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.8,  
            max_tokens=500,  
            presence_penalty=0.6,  
            frequency_penalty=0.3  
        )
        
        answer = response.choices[0].message.content
        
        # Save to session
        self.mongo_db.add_message(session_id, "user", query)
        self.mongo_db.add_message(session_id, "assistant", answer)
        
        result = {
            "answer": answer,
            "sources": [
                {
                    "content": r["payload"]["content"][:200] + "..." if len(r["payload"]["content"]) > 200 else r["payload"]["content"],
                    "score": r["score"],
                    "metadata": r["payload"].get("metadata", {})
                }
                for r in retrieval_results
            ],
            "session_id": session_id
        }
        
        return result