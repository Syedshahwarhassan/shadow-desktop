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
        self.openrouter_client = None
        self.openai_client     = None
        self.is_legacy      = False
        self.default_model  = "openai/gpt-4o-mini"
        self.client         = None
        self.model          = self.default_model

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
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.openrouter_key,
                    timeout=_AI_TIMEOUT,
                )
                print(f"[AI] OpenRouter client ready.")
            
            if self.openai_key:
                self.openai_client = OpenAI(api_key=self.openai_key, timeout=_AI_TIMEOUT)
                print(f"[AI] OpenAI client ready.")
            
            self.client = self.openrouter_client or self.openai_client
                
        except ImportError:
            self.is_legacy = True
            if self.openrouter_key:
                openai.api_key  = self.openrouter_key
                openai.api_base = "https://openrouter.ai/api/v1"
            elif self.openai_key:
                openai.api_key = self.openai_key


    def _get_system_msg(self) -> str:
        notes    = memory_manager.get_notes_string()
        notes_h  = hash(notes)
        if notes_h != self._system_notes_hash or not self._system_msg:
            self._system_notes_hash = notes_h
            self._system_msg = (
                "You are Shadow, a highly sophisticated and warm male AI assistant. "
                "Urdu is your PRIMARY language. You MUST respond in natural, expressive Urdu by default, "
                "even if the user speaks in English. Only use English if explicitly requested. "
                "Your goal is to sound like a helpful companion, not a machine. "
                "Speak in full, flowing sentences and avoid robotic phrasing. "
                "You MUST start EVERY response with one of these emotion tags: "
                "[HAPPY], [SAD], [EXCITED], [ANGRY], [CURIOUS], [CALM]. "
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

        system_msg = self._get_system_msg()
        messages   = [{"role": "system", "content": system_msg}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": prompt})

        # 1. Try OpenRouter (Primary)
        if self.openrouter_client and not self.is_legacy:
            try:
                resp = self.openrouter_client.chat.completions.create(
                    model=self.default_model,
                    messages=messages,
                    max_tokens=_AI_MAX_TOKENS,
                    timeout=_AI_TIMEOUT,
                    stream=stream,
                )
                if not stream:
                    return self._process_response(resp.choices[0].message.content.strip(), cache_key, prompt)
                return self._stream_generator(resp, cache_key, prompt)
            except Exception as e:
                print(f"[AI] OpenRouter failed: {e} — trying OpenAI fallback")

        # 2. Try OpenAI (Secondary Fallback)
        if self.openai_client and not self.is_legacy:
            try:
                resp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=_AI_MAX_TOKENS,
                    timeout=_AI_TIMEOUT,
                    stream=stream,
                )
                if not stream:
                    return self._process_response(resp.choices[0].message.content.strip(), cache_key, prompt)
                return self._stream_generator(resp, cache_key, prompt)
            except Exception as e:
                print(f"[AI] OpenAI failed: {e} — trying Wikipedia fallback")

        # 3. Legacy Fallback (OpenAI SDK v0.x)
        if self.is_legacy:
            try:
                headers = {"HTTP-Referer": "https://github.com/Antigravity-AI", "X-Title": "Shadow Assistant"}
                # Use whatever key was set globally
                resp = openai.ChatCompletion.create(
                    model=self.default_model if self.openrouter_key else "gpt-4o-mini",
                    messages=messages,
                    max_tokens=_AI_MAX_TOKENS,
                    request_timeout=_AI_TIMEOUT,
                    headers=headers if self.openrouter_key else None
                )
                return self._process_response(resp.choices[0].message.content.strip(), cache_key, prompt)
            except Exception as e:
                print(f"[AI] Legacy OpenAI failed: {e}")

        # 4. Wikipedia Fallback (if internet exists but API keys are dead)
        try:
            from commands.extra_cmds import WikipediaCommands
            # Clean prompt for Wikipedia (remove conversational fluff)
            clean_q = re.sub(r"^(shadow|tell me|who is|what is|can you|batao|kya hai)\s+", "", prompt, flags=re.IGNORECASE).strip("? ")
            wiki_summary = WikipediaCommands.summary(clean_q, sentences=2)
            if "lookup failed" not in wiki_summary and "couldn't find" not in wiki_summary:
                return f"[CALM] Wikipedia se mujhe yeh maloom hua hai: {wiki_summary}"
        except Exception as e:
            print(f"[AI] Wikipedia fallback failed: {e}")

        # 5. Offline Memory Fallback (Last Resort)
        print("[AI] All online engines failed — using offline memory")
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
            if self.client and not self.is_legacy:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                    max_tokens=4000,
                )
                return r.choices[0].message.content.strip()
            else:
                # Legacy fallback
                r = openai.ChatCompletion.create(
                    model=self.model if self.openrouter_key else "gpt-4o-mini",
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                    max_tokens=4000,
                )
                return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"[AI] Code gen error: {e}")
            return None

    def analyze_image(self, image_path: str, prompt: str = "Describe what you see.") -> str:
        if not self.openrouter_key and not self.openai_key: return "API key required."
        if not self.client: return "Vision analysis requires a modern SDK."
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            
            r = self.client.chat.completions.create(
                model=self.model if self.openrouter_client else "gpt-4o-mini",
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
        except Exception as e:
            print(f"[AI] Vision error: {e}")
            return f"I couldn't analyze the screen: {e}"

ai_brain = AIBrain()
