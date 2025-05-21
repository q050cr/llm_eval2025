"""
Utility functions
"""

"""
Perplexity wrapper that looks & feels like a Chatlas model
"""
from openai import OpenAI  # Added for Deepseek API access
from urllib.parse import urlparse
from types import SimpleNamespace
import requests
import os
import json


# --- small, generic wrapper that every “model” can return ------------------ #
class ResponseWrapper:
    """
    Matches what Chatlas expects:
        - .content      → final text
        - .raw_response → full provider payload
        - .citations    → optional list (empty if provider doesn't supply any)
        - .usage        → token usage etc. (empty dict by default)
    """

    def __init__(self, content, raw_response,
                 citations=None, usage=None):
        self.content = content
        self.raw_response = raw_response
        self.citations = citations or []
        self.usage = usage or {}


# --------------------------------------------------------------------------- #
class ChatPerplexityDirect:
    """
    Drop-in replacement for a Chatlas-style model.
    """

    def __init__(self,
                 api_key: str | None = None,
                 model: str = "sonar-pro",
                 system_prompt: str = ""):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("Perplexity API key missing "
                             "(param or PERPLEXITY_API_KEY env var).")

        self.model = model
        self.system_prompt = system_prompt
        self.url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json"
        }

    # ------------------------- public entry-point -------------------------- #
    def chat(self, user_input: str, echo: str | None = None) -> ResponseWrapper:
        """
        Exactly the signature Chatlas uses.
        """
        # 1) build messages
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_input})

        # 2) payload
        payload = {
            "model":        self.model,
            "messages":     messages
        }

        if echo == "all":
            print("➜ Perplexity request\n",
                  json.dumps(payload, indent=2), "\n")

        # 3) call the API
        resp = requests.post(self.url, json=payload, headers=self.headers)
        resp.raise_for_status()
        resp_json = resp.json()

        if echo in ("all", "response"):
            print("➜ Perplexity raw response\n",
                  json.dumps(resp_json, indent=2), "\n")

        # 4) unpack
        content = self._extract_content(resp_json)
        citations = self._extract_citations(resp_json)
        usage = resp_json.get("usage", {})

        # 5) return Chatlas-compatible wrapper
        return ResponseWrapper(content, resp_json, citations, usage)

    # --------------------------- helpers ----------------------------------- #
    def _extract_content(self, response_json: dict) -> str:
        if (choices := response_json.get("choices")):
            message = choices[0].get("message", {})
            return message.get("content", "")
        return ""

    def _extract_citations(self, response_json: dict) -> list[dict]:
        """
        Collapses all the little formats Perplexity can emit into one simple list:
        [{url, title, text}, …]
        """
        cites: list[dict] = []

        # simple (top-level) format
        for url in response_json.get("citations", []):
            cites.append({
                "url":   url,
                "title": self._domain_title(url),
                "text":  ""
            })

        # tools / link format
        for choice in response_json.get("choices", []):
            msg = choice.get("message", {})
            for tc in msg.get("tool_calls", []):
                if tc.get("type") != "link":
                    continue
                try:
                    args = json.loads(tc["function"]["arguments"])
                except (KeyError, json.JSONDecodeError):
                    continue
                url = args.get("url")
                if url:
                    cites.append({
                        "url":   url,
                        "title": args.get("title", self._domain_title(url)),
                        "text":  args.get("text", "")
                    })

            # legacy 'links' member
            for link in msg.get("links", []):
                url = link.get("url", "")
                cites.append({
                    "url":   url,
                    "title": link.get("title", self._domain_title(url)),
                    "text":  link.get("text", "")
                })

        return cites

    @staticmethod
    def _domain_title(url: str) -> str:
        """
        Nice human-readable domain or special-case titles (Wikipedia, YouTube).
        """
        try:
            domain = urlparse(url).netloc.removeprefix("www.")
            if "youtube.com" in domain or "youtu.be" in domain:
                return "YouTube Video"
            if "wikipedia.org" in domain and "/wiki/" in url:
                topic = url.split("/wiki/")[1].replace("_", " ")
                return f"Wikipedia: {topic}"
            return domain
        except Exception:
            return url


# DeepSeek ------------------------------------------------------------------ #

# Custom class for Deepseek API integration
# Create a response object compatible with other Chatlas models having the 'content' instance + raw_response in addition

class DeepseekChat:
    def __init__(self, model, system_prompt, api_key):
        self.model = model
        self.system_prompt = system_prompt
        self.client = OpenAI(
            api_key=api_key, base_url="https://api.deepseek.com")

    def chat(self, user_input, echo=None):
        # Create a response object similar to what Chatlas expects
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input}
            ],
            stream=False
        )
        usage = getattr(response, "usage", None)

        return ResponseWrapper(response.choices[0].message.content, response, citations=None, usage=usage)

# OpenAI ------------------------------------------------------------------ #
class OpenAIChat:
    """
    Drop-in Chatlas-style wrapper for the official OpenAI SDK.
    Works with either `responses.create` (>=1.80) or
    `chat.completions.create` (any version).
    """

    def __init__(self,
                 model: str = "gpt-4o",
                 system_prompt: str = "",
                 api_key: str | None = None):
        self.model = model
        self.system_prompt = system_prompt
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

        # Feature-detect which endpoint is available
        self._use_responses = hasattr(self.client, "responses")

    # ------------------------------------------------------------------ #
    def chat(self, user_input: str, echo: str | None = None) -> ResponseWrapper:
        if self._use_responses:                 # modern code path (responses)
            raw = self.client.responses.create(
                model=self.model,
                # 'instructions' is new https://platform.openai.com/docs/guides/text?api-mode=responses#message-roles-and-instruction-following
                instructions=self.system_prompt,
                input=user_input,
                stream=False
            )
            content = raw.output_text           # single string
        else:                                   # fallback for old SDKs (chat.completions)
            raw = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_input},
                ],
                stream=False
            )
            content = raw.choices[0].message.content

        usage = getattr(raw, "usage", None)     # guaranteed on responses API

        if echo in ("all", "response"):
            print(raw.model_dump_json(indent=2) if hasattr(
                raw, "model_dump_json") else raw)

        return ResponseWrapper(content, raw, usage=usage)
