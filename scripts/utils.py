"""
Utility functions
"""

import os
import json
import requests
from types import SimpleNamespace
from urllib.parse import urlparse


class ChatPerplexityDirect:
    """
    A class for interacting with the Perplexity API directly, similar to Chatlas but with
    citation handling. This implementation extracts and processes citations from responses.
    """

    def __init__(self, api_key=None, model="sonar-pro", system_prompt=""):
        """
        Initialize the Perplexity API client.

        Args:
            api_key (str): Perplexity API key. If None, will try to get from environment.
            model (str): The model to use. Options: "sonar", "sonar-pro", "sonar-small", "sonar-medium", "claude-3.5-sonnet", etc.
            system_prompt (str): System prompt to use for all conversations.
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Perplexity API key is required. Set it with api_key parameter or PERPLEXITY_API_KEY env variable.")

        self.model = model
        self.system_prompt = system_prompt
        self.url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _extract_citations(self, response_json):
        """
        Extract citations from a Perplexity API response.

        Args:
            response_json (dict): The JSON response from the Perplexity API.

        Returns:
            list: List of citation dictionaries.
        """
        citations = []

        # Check for top-level citations field first (as in your example)
        if 'citations' in response_json and isinstance(response_json['citations'], list):
            for url in response_json['citations']:
                citation = {
                    'url': url,
                    'title': self._extract_domain_from_url(url),
                    'text': ''  # No excerpt available in this format
                }
                citations.append(citation)
            return citations

        # If no top-level citations, check other possible locations
        if 'choices' in response_json and len(response_json['choices']) > 0:
            choice = response_json['choices'][0]

            # Extract tool calls (citations) if they exist
            if 'message' in choice and 'tool_calls' in choice['message']:
                tool_calls = choice['message']['tool_calls']
                for tool_call in tool_calls:
                    if tool_call.get('type') == 'link':
                        function = tool_call.get('function', {})
                        if function and 'arguments' in function:
                            try:
                                args = json.loads(function['arguments'])
                                if 'url' in args:
                                    citation = {
                                        'url': args['url'],
                                        'title': args.get('title', self._extract_domain_from_url(args['url'])),
                                        'text': args.get('text', '')
                                    }
                                    citations.append(citation)
                            except json.JSONDecodeError:
                                pass

            # Look for citations in special 'links' field if available
            if 'message' in choice and 'links' in choice['message']:
                for link in choice['message']['links']:
                    citation = {
                        'url': link.get('url', ''),
                        'title': link.get('title', self._extract_domain_from_url(link.get('url', ''))),
                        'text': link.get('text', '')
                    }
                    citations.append(citation)

        return citations

    def _extract_domain_from_url(self, url):
        """
        Extract a readable domain name from a URL to use as a title
        when no explicit title is available.

        Args:
            url (str): The URL to extract a domain from

        Returns:
            str: A readable domain name or the original URL if parsing fails
        """
        try:
            # Remove www. if present and return the domain
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            # If it's YouTube, try to make it more descriptive
            if 'youtube.com' in domain or 'youtu.be' in domain:
                return "YouTube Video"
            # Wikipedia articles can be more descriptive
            if 'wikipedia.org' in domain and '/wiki/' in url:
                topic = url.split('/wiki/')[1].replace('_', ' ')
                return f"Wikipedia: {topic}"
            return domain
        except:
            return url

    def _create_response_object(self, response_json):
        """
        Create a response object similar to what Chatlas would return.

        Args:
            response_json (dict): The JSON response from the Perplexity API.

        Returns:
            SimpleNamespace: A dot-accessible object with the response data.
        """
        # Extract the main response content
        content = ""
        if 'choices' in response_json and len(response_json['choices']) > 0:
            choice = response_json['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                content = choice['message']['content']

        # Extract citations
        citations = self._extract_citations(response_json)

        # Create a Chatlas-like response object
        response_obj = SimpleNamespace(
            content=content,
            raw_response=response_json,
            model=response_json.get('model', self.model),
            citations=citations,
            usage=response_json.get('usage', {})
        )

        return response_obj

    def chat(self, message, echo=None):
        """
        Send a message to the Perplexity API and get a response.

        Args:
            message (str): The user's message to send to the API.
            echo (str): If "all", print both request and response. If "response", print only response. 
                      If "none" or None, print nothing.

        Returns:
            SimpleNamespace: A response object with content, citations, and metadata.
        """
        # Prepare the messages array
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": message})

        # Build the payload
        payload = {
            "model": self.model,
            "messages": messages,
            # Add parameters to enhance citations
            "tools": [{"type": "link"}],  # Request link citations
            "tool_choice": "auto",  # Let the model decide when to add citations
            "link_history": True    # Include history of links
        }

        # Echo the request if requested
        if echo == "all":
            print("Request:")
            print(json.dumps(payload, indent=2))
            print("\n")

        # Make the API call
        response = requests.post(self.url, json=payload, headers=self.headers)
        response_json = response.json()

        # Echo the response if requested
        if echo in ["all", "response"]:
            print("Response:")
            print(json.dumps(response_json, indent=2))
            print("\n")

        # Process and return the response
        return self._create_response_object(response_json)
