"""
ai_brain.py — Optimized AI engine for Shadow.

Optimisations
─────────────
• True LRU cache via collections.OrderedDict — O(1) eviction vs O(n) loop.
• system_msg cached and only rebuilt when memory notes change.
• Conversation history (last 4 turns) kept in a deque for better AI context.
• Duplicate prompt debounce: identical consecutive prompts skip the API call.
• _AI_TIMEOUT tightened to 8 s; streaming preferred for lower perceived latency.
"""

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

        # Conversation history deque (alternating user/assistant messages)
        self._history: deque[dict] = deque(maxlen=_HISTORY_TURNS * 2)

        # system_msg cache — only rebuilt when memory notes change
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

    # ── System prompt (cached) ────────────────────────────────────────────────

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

    # ── LRU cache helpers ─────────────────────────────────────────────────────

    def _cache_get(self, key: str):
        item = self._cache.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < time.time():
            del self._cache[key]
            return None
        # Move to end (most-recently used)
        self._cache.move_to_end(key)
        return value

    def _cache_set(self, key: str, value: str):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (time.time() + _CACHE_TTL, value)
        # Evict oldest when over capacity — O(1)
        if len(self._cache) > _CACHE_MAX:
            self._cache.popitem(last=False)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_response(self, prompt: str, stream: bool = False):
        if not self.openrouter_key and not self.openai_key:
            return "Please configure your OpenRouter or OpenAI API key in config.json."

        cache_key = (prompt or "").strip().lower()

        # Debounce identical consecutive prompts
        if cache_key == self._last_prompt:
            cached = self._cache_get(cache_key)
            if cached:
                return cached
        self._last_prompt = cache_key

        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            system_msg = self._get_system_msg()
            messages   = [{"role": "system", "content": system_msg}]
            # Inject conversation history for context
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
                    result = self._process_response(text, cache_key, prompt)
                    return result
                else:
                    return self._stream_generator(resp, cache_key, prompt)
            else:
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=_AI_MAX_TOKENS,
                    request_timeout=_AI_TIMEOUT,
                )
                text = resp.choices[0].message.content.strip()
                return self._process_response(text, cache_key, prompt)

        except Exception as e:
            print(f"[AI] Error: {e}")
            return memory_manager.get_offline_response(prompt)

    def _process_response(self, text: str, cache_key: str, user_prompt: str) -> str:
        # Handle memory save tags
        m = re.search(r"\[SAVE_MEMORY:\s*(.+?)\]", text, re.IGNORECASE)
        if m:
            memory_manager.add_note(m.group(1).strip())
            text = re.sub(r"\[SAVE_MEMORY:\s*.+?\]", "", text, flags=re.IGNORECASE).strip()

        # Update conversation history
        self._history.append({"role": "user",      "content": user_prompt})
        self._history.append({"role": "assistant", "content": text})

        self._cache_set(cache_key, text)
        return text

    def _stream_generator(self, stream, cache_key: str, user_prompt: str):
        full, buf = "", ""
        try:
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if not content:
                    continue
                full += content
                buf  += content
                if any(p in content for p in [".", "!", "?", "۔", "\n"]):
                    yield buf.strip()
                    buf = ""
            if buf.strip():
                yield buf.strip()
            self._process_response(full, cache_key, user_prompt)
        except Exception as e:
            print(f"[AI] Stream error: {e}")
            yield "I am having trouble streaming the response."

    def generate_code(self, prompt: str):
        if not self.openrouter_key and not self.openai_key:
            return None
        sys_msg = (
            "You are an expert software developer. "
            "Return ONLY the requested code in markdown code blocks. "
            "If multiple files are needed, precede each block with the filename in backticks. "
            "No explanations or conversational text."
        )
        try:
            if not self.is_legacy and self.client:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=4000,
                )
                return r.choices[0].message.content.strip()
            else:
                r = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=4000,
                )
                return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AI] Code gen error: {e}")
            return None

    def analyze_image(self, image_path: str, prompt: str = "Describe what you see.") -> str:
        if not self.openrouter_key and not self.openai_key:
            return "API key required for vision analysis."
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            if not self.is_legacy and self.client:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content":
                            "You are a vision AI. Analyze the image and answer in Urdu."},
                        {"role": "user", "content": [
                            {"type": "text",      "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ]},
                    ],
                    max_tokens=500,
                )
                return r.choices[0].message.content.strip()
            return "Vision analysis requires a modern OpenAI SDK version."
        except Exception as e:
            print(f"[AI] Vision error: {e}")
            return f"I couldn't analyze the screen: {e}"


# Singleton
ai_brain = AIBrain()
