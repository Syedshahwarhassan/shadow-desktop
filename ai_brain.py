import openai
import time
import re
import base64
from collections import OrderedDict, deque
from config_manager import config_manager
from memory_manager import memory_manager

_AI_TIMEOUT   = 8
_AI_MAX_TOKENS = 160
_CACHE_MAX    = 200
_CACHE_TTL    = 300   # seconds
_HISTORY_TURNS = 4    # keep last N user+assistant exchanges


class AIBrain:
    def __init__(self):
        self.openrouter_key = config_manager.get("api_keys.openrouter")
        self.openai_key     = config_manager.get("api_keys.openai")
        self.client         = None
        self.is_legacy      = False
        self.default_model  = "openai/gpt-4o-mini"

        # True LRU cache
        self._cache: OrderedDict[str, tuple[float, str]] = OrderedDict()

        # Conversation history deque
        self._history: deque[dict] = deque(maxlen=_HISTORY_TURNS * 2)

        # system_msg cache
        self._system_msg: str        = ""
        self._system_notes_hash: int = 0

        # Duplicate-call debounce
        self._last_prompt: str = ""

        try:
            from openai import OpenAI
            if self.openrouter_key:
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.openrouter_key,
                    timeout=_AI_TIMEOUT,
                )
                self.model = self.default_model
                print(f"[AI] OpenRouter ready — {self.model}")
            elif self.openai_key:
                self.client = OpenAI(api_key=self.openai_key, timeout=_AI_TIMEOUT)
                self.model = "gpt-4o-mini"
                print(f"[AI] OpenAI ready — {self.model}")
        except ImportError:
            self.is_legacy = True
            if self.openrouter_key:
                openai.api_key  = self.openrouter_key
                openai.api_base = "https://openrouter.ai/api/v1"
                self.model      = self.default_model
            elif self.openai_key:
                openai.api_key = self.openai_key
                self.model     = "gpt-4o-mini"

    def _get_system_msg(self) -> str:
        notes    = memory_manager.get_notes_string()
        notes_h  = hash(notes)
        if notes_h != self._system_notes_hash or not self._system_msg:
            self._system_notes_hash = notes_h
            self._system_msg = (
                "You are Shadow, a highly expressive and friendly female AI assistant. "
                "You are multilingual and can speak naturally in English and Urdu. "
                "Respond in the language the user uses. "
                "You MUST start EVERY response with one of these emotion tags: "
                "[HAPPY], [SAD], [EXCITED], [ANGRY], [CURIOUS], [CALM]. "
                "Be human-like, warm, and natural. Do not be robotic. "
                "NEVER say 'Shadow' or 'شیڈو'. "
                f"{notes}\n"
                "Append `[SAVE_MEMORY: info]` if asked to remember something."
            )
        return self._system_msg

    def _cache_get(self, key: str):
        item = self._cache.get(key)
        if item is None: return None
        expires, value = item
        if expires < time.time():
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def _cache_set(self, key: str, value: str):
        if key in self._cache: self._cache.move_to_end(key)
        self._cache[key] = (time.time() + _CACHE_TTL, value)
        if len(self._cache) > _CACHE_MAX: self._cache.popitem(last=False)

    def get_response(self, prompt: str, stream: bool = False):
        if not self.openrouter_key and not self.openai_key:
            return "Please configure your OpenRouter or OpenAI API key in config.json."
        cache_key = (prompt or "").strip().lower()
        if cache_key == self._last_prompt:
            cached = self._cache_get(cache_key)
            if cached: return cached
        self._last_prompt = cache_key
        cached = self._cache_get(cache_key)
        if cached: return cached

        try:
            system_msg = self._get_system_msg()
            messages   = [{"role": "system", "content": system_msg}]
            messages.extend(self._history)
            messages.append({"role": "user", "content": prompt})

            if not self.is_legacy and self.client:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=_AI_MAX_TOKENS,
                    timeout=_AI_TIMEOUT,
                    stream=stream,
                )
                if not stream:
                    text = resp.choices[0].message.content.strip()
                    return self._process_response(text, cache_key, prompt)
                else:
                    return self._stream_generator(resp, cache_key, prompt)
            else:
                headers = {"HTTP-Referer": "https://github.com/Antigravity-AI", "X-Title": "Shadow Assistant"}
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=_AI_MAX_TOKENS,
                    request_timeout=_AI_TIMEOUT,
                    headers=headers
                )
                text = resp.choices[0].message.content.strip()
                return self._process_response(text, cache_key, prompt)
        except Exception as e:
            error_str = str(e)
            print(f"[AI] Error: {error_str}")
            if "User not found" in error_str:
                return "[CALM] Maaf kijiye, aapka OpenRouter API key invalid hai ya expire ho chuka hai. Please config.json mein naya key check karein."
            return memory_manager.get_offline_response(prompt)

    def _process_response(self, text: str, cache_key: str, user_prompt: str) -> str:
        m = re.search(r"\[SAVE_MEMORY:\s*(.+?)\]", text, re.IGNORECASE)
        if m:
            memory_manager.add_note(m.group(1).strip())
            text = re.sub(r"\[SAVE_MEMORY:\s*.+?\]", "", text, flags=re.IGNORECASE).strip()
        self._history.append({"role": "user",      "content": user_prompt})
        self._history.append({"role": "assistant", "content": text})
        self._cache_set(cache_key, text)
        return text

    def _stream_generator(self, stream, cache_key: str, user_prompt: str):
        full, buf = "", ""
        try:
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if not content: continue
                full += content
                buf  += content
                if any(p in content for p in [".", "!", "?", "۔", "\n"]):
                    yield buf.strip()
                    buf = ""
            if buf.strip(): yield buf.strip()
            self._process_response(full, cache_key, user_prompt)
        except Exception as e:
            print(f"[AI] Stream error: {e}")
            yield "I am having trouble streaming the response."

    def generate_code(self, prompt: str):
        if not self.openrouter_key and not self.openai_key: return None
        sys_msg = "You are an expert software developer. Return ONLY code in markdown code blocks."
        try:
            if not self.is_legacy and self.client:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                    max_tokens=4000,
                )
                return r.choices[0].message.content.strip()
            else:
                r = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                    max_tokens=4000,
                )
                return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AI] Code gen error: {e}")
            return None

    def analyze_image(self, image_path: str, prompt: str = "Describe what you see.") -> str:
        if not self.openrouter_key and not self.openai_key: return "API key required."
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            if not self.is_legacy and self.client:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a vision AI. Answer in Urdu."},
                        {"role": "user", "content": [
                            {"type": "text",      "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ]},
                    ],
                    max_tokens=500,
                )
                return r.choices[0].message.content.strip()
            return "Vision analysis requires a modern SDK."
        except Exception as e:
            print(f"[AI] Vision error: {e}")
            return f"I couldn't analyze the screen: {e}"

ai_brain = AIBrain()
