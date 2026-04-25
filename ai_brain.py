import openai
import time
from config_manager import config_manager
import re
import base64
from memory_manager import memory_manager

# Hard caps for AI calls — keep the assistant snappy and prevent it from
# hanging if the upstream service is slow.
_AI_TIMEOUT = 8         # seconds before we give up on a single request
_AI_MAX_TOKENS = 160    # short, conversational responses (was 200)


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
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes TTL

        # Use a more reliable free model ID for OpenRouter
        self.default_model = "openai/gpt-4o-mini" 

        try:
            from openai import OpenAI
            if self.openrouter_key:
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.openrouter_key,
                    timeout=_AI_TIMEOUT,
                )
                self.model = self.default_model
                print(f"[AI] OpenRouter initialized with {self.model}")
            elif self.openai_key:
                self.client = OpenAI(api_key=self.openai_key, timeout=_AI_TIMEOUT)
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

    def get_response(self, prompt, stream=False):
        if not self.openrouter_key and not self.openai_key:
            return "Please configure your OpenRouter or OpenAI API key in config.json."

        cache_key = (prompt or "").strip().lower()
        cached = self._cache.get(cache_key)
        if cached and cached[0] > time.time():
            return cached[1]

        try:
            memory_context = memory_manager.get_notes_string()
            system_msg = (
                "You are Shadow, a highly expressive and friendly female AI assistant. "
                "Speak ONLY in natural, colloquial Urdu. Use emotive words like 'واہ', 'ارے', 'اوہ'. "
                "You MUST start EVERY response with one of these emotion tags: "
                "[HAPPY], [SAD], [EXCITED], [ANGRY], [CURIOUS], [CALM]. "
                "Be human-like, warm, and natural. Do not be robotic. "
                "NEVER say 'Shadow' or 'شیڈو'. "
                f"{memory_context}\n"
                "Append `[SAVE_MEMORY: info]` if asked to remember something."
            )
            
            if not self.is_legacy and self.client:
                # Use streaming for lower latency
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=_AI_MAX_TOKENS,
                    timeout=_AI_TIMEOUT,
                    stream=stream
                )
                
                if not stream:
                    response_text = response.choices[0].message.content.strip()
                    return self._process_response(response_text, cache_key)
                else:
                    return self._stream_generator(response, cache_key)
            else:
                # Legacy or fallback (no stream support implemented for legacy here)
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=_AI_MAX_TOKENS,
                    request_timeout=_AI_TIMEOUT,
                )
                response_text = response.choices[0].message.content.strip()
                return self._process_response(response_text, cache_key)

        except Exception as e:
            print(f"[AI] Error: {e}")
            # Fallback to local offline memory system
            return memory_manager.get_offline_response(prompt)

    def _process_response(self, response_text, cache_key):
        # Process memory tags
        memory_match = re.search(r'\[SAVE_MEMORY:\s*(.+?)\]', response_text, re.IGNORECASE)
        if memory_match:
            note = memory_match.group(1).strip()
            memory_manager.add_note(note)
            response_text = re.sub(r'\[SAVE_MEMORY:\s*.+?\]', '', response_text, flags=re.IGNORECASE).strip()

        # Cache the response
        self._cache[cache_key] = (time.time() + self._cache_ttl, response_text)
        if len(self._cache) > 200:
            for k in list(self._cache.keys())[:50]:
                self._cache.pop(k, None)
        return response_text

    def _stream_generator(self, response_stream, cache_key):
        full_text = ""
        sentence_buffer = ""
        
        try:
            for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_text += content
                    sentence_buffer += content
                    
                    # Yield sentence by sentence for TTS
                    if any(p in content for p in [".", "!", "?", "۔", "\n"]):
                        yield sentence_buffer.strip()
                        sentence_buffer = ""
            
            if sentence_buffer.strip():
                yield sentence_buffer.strip()
                
            self._process_response(full_text, cache_key)
        except Exception as e:
            print(f"[AI] Stream Error: {e}")
            yield "I am having trouble streaming the response."

    def generate_code(self, prompt):
        """Generates raw code from a prompt, strictly formatted as markdown blocks."""
        if not self.openrouter_key and not self.openai_key:
            print("[AI] No API key configured for code generation.")
            return None

        try:
            system_msg = (
                "You are an expert software developer. "
                "The user will give you a request to write code. "
                "You MUST return ONLY the requested code. "
                "Enclose the code in markdown code blocks. "
                "If the project requires multiple files, precede each code block with the filename enclosed in backticks, "
                "for example: `index.html`\\n```html\\n...\\n```\\n"
                "Do not include any explanations, greetings, or conversational text. ONLY output the filenames and code blocks."
            )
            
            if not self.is_legacy and self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000
                )
                return response.choices[0].message.content.strip()
            else:
                import openai
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=4000
                )
                return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[AI] Code Gen Error: {e}")
            return None

    def analyze_image(self, image_path, prompt="Describe what you see on the screen."):
        """Analyzes an image using a vision-capable model."""
        if not self.openrouter_key and not self.openai_key:
            return "API Key required for vision analysis."
            
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            system_msg = "You are a vision-capable AI assistant. Analyze the provided image and answer the user's question concisely in Urdu."
            
            # Note: Many OpenRouter models support vision (e.g. Gemini, GPT-4o)
            # We use the same model but include the image in the message payload.
            if not self.is_legacy and self.client:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                return response.choices[0].message.content.strip()
            return "Vision analysis requires a modern OpenAI SDK version."
        except Exception as e:
            print(f"[AI] Vision Error: {e}")
            return f"I couldn't analyze the screen: {e}"

# Singleton
ai_brain = AIBrain()
