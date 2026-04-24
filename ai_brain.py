import openai
from config_manager import config_manager
import re
from memory_manager import memory_manager

class AIBrain:
    """
    AI Brain using OpenRouter API.
    Provides a fallback to OpenAI if OpenRouter is not configured.
    Compatible with both OpenAI SDK < 1.0.0 and >= 1.0.0
    """
    def __init__(self):
        self.openrouter_key = config_manager.get("api_keys.openrouter")
        self.openai_key = config_manager.get("api_keys.openai")
        self.client = None
        self.is_legacy = False

        # Use a more reliable free model ID for OpenRouter
        # gemini-2.0-flash-lite is often restricted or renamed
        self.default_model = "openai/gpt-5.3-chat" 

        try:
            from openai import OpenAI
            if self.openrouter_key:
                self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.openrouter_key)
                self.model = self.default_model
                print(f"[AI] OpenRouter initialized with {self.model}")
            elif self.openai_key:
                self.client = OpenAI(api_key=self.openai_key)
                self.model = "gpt-4o-mini"
                print(f"[AI] OpenAI initialized with {self.model}")
        except ImportError:
            self.is_legacy = True
            if self.openrouter_key:
                openai.api_key = self.openrouter_key
                openai.api_base = "https://openrouter.ai/api/v1"
                self.model = self.default_model
                print(f"[AI] OpenRouter initialized (Legacy) with {self.model}")
            elif self.openai_key:
                openai.api_key = self.openai_key
                self.model = "gpt-4o-mini"
                print(f"[AI] OpenAI initialized (Legacy) with {self.model}")

    def get_response(self, prompt):
        if not self.openrouter_key and not self.openai_key:
            return "Please configure your OpenRouter or OpenAI API key in config.json."

        try:
            memory_context = memory_manager.get_notes_string()
            system_msg = (
                "You are Shadow, a highly advanced but deeply human-like AI assistant. "
                "You have a warm, friendly personality, a sense of humor, and you speak colloquially in both English and Urdu. "
                "Instead of acting like a rigid robot, you express emotions, empathy, and conversational nuance. Keep responses concise but natural. "
                "You have a long-term memory system. "
                f"{memory_context}\n"
                "If the user asks you to remember something, note down a fact, or set a reminder, you MUST append "
                "`[SAVE_MEMORY: the information to remember]` at the very end of your response. "
                "For example, if the user says 'remember that my favorite color is red', you reply normally and end with '[SAVE_MEMORY: User\\'s favorite color is red]'."
            )
            
            if not self.is_legacy and self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200
                )
                response_text = response.choices[0].message.content.strip()
            else:
                # Legacy style
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200
                )
                response_text = response.choices[0].message.content.strip()

            # Process memory tags
            memory_match = re.search(r'\[SAVE_MEMORY:\s*(.+?)\]', response_text, re.IGNORECASE)
            if memory_match:
                note = memory_match.group(1).strip()
                memory_manager.add_note(note)
                response_text = re.sub(r'\[SAVE_MEMORY:\s*.+?\]', '', response_text, flags=re.IGNORECASE).strip()
            
            return response_text

        except Exception as e:
            print(f"[AI] Error: {e}")
            # Try a different model if the first one fails
            if "not a valid model ID" in str(e) and self.model != "openai/gpt-3.5-turbo":
                print("[AI] Retrying with gpt-3.5-turbo...")
                self.model = "openai/gpt-3.5-turbo"
                return self.get_response(prompt)
            return "I am having trouble connecting to my AI core."

# Singleton
ai_brain = AIBrain()
