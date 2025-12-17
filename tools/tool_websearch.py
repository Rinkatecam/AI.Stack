"""
title: Web Search Tool
version: 2.0.0
description: Search the internet using free methods (DuckDuckGo, Wikipedia, direct URL fetch). No API keys required!
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack

# SYSTEM PROMPT FOR AI
# ====================
# Search the internet for information using free methods.
# No API keys or payments required!
#
# AVAILABLE METHODS:
#   web_search(query)     - DuckDuckGo search
#   wikipedia(topic)      - Wikipedia lookup
#   fetch_url(url)        - Fetch any URL
#   news_search(query)    - Search recent news
#   get_weather(location) - Weather lookup
"""

import os
import re
import json
import urllib.request
import urllib.parse
import urllib.error
import html
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_TIMEOUT = 15


def _make_request(url: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """Make HTTP request with proper headers."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            return response.read().decode(charset, errors='replace')
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}"
    except Exception as e:
        return f"Error: {str(e)}"


def _strip_html(html_text: str) -> str:
    """Remove HTML tags and clean up text."""
    html_text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<style[^>]*>.*?</style>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<head[^>]*>.*?</head>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<[^>]+>', ' ', html_text)
    html_text = html.unescape(html_text)
    html_text = re.sub(r'\s+', ' ', html_text)
    html_text = re.sub(r'\n\s*\n', '\n\n', html_text)
    return html_text.strip()


def _extract_text_content(html_text: str, max_chars: int = 10000) -> str:
    """Extract meaningful text content from HTML."""
    content = ""
    patterns = [
        r'<article[^>]*>(.*?)</article>',
        r'<main[^>]*>(.*?)</main>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*id="[^"]*content[^"]*"[^>]*>(.*?)</div>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
            break

    if not content:
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_text, re.DOTALL | re.IGNORECASE)
        if body_match:
            content = body_match.group(1)
        else:
            content = html_text

    text = _strip_html(content)
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


class Tools:
    class Valves(BaseModel):
        default_timeout: int = Field(
            default=15,
            description="Request timeout in seconds (5-60)"
        )
        max_results: int = Field(
            default=10,
            description="Maximum search results to return"
        )
        max_content_length: int = Field(
            default=10000,
            description="Maximum characters to extract from pages"
        )
        safe_search: bool = Field(
            default=True,
            description="Enable safe search filtering"
        )

    def __init__(self):
        self.citation = True
        self.file_handler = False
        self.valves = self.Valves()

    def _get_timeout(self) -> int:
        return max(5, min(60, getattr(self.valves, 'default_timeout', DEFAULT_TIMEOUT)))

    def _get_max_results(self) -> int:
        return getattr(self.valves, 'max_results', 10)

    def _get_max_content(self) -> int:
        return getattr(self.valves, 'max_content_length', 10000)

    def web_search(self, query: str, num_results: int = 0) -> str:
        """
        Search the web using DuckDuckGo (FREE, no API key).

        Args:
            query: Search query
            num_results: Number of results (default: from settings)

        Returns:
            Search results with titles, URLs, and snippets.
        """
        if not query or not query.strip():
            return "Error: Please provide a search query."

        num_results = num_results if num_results > 0 else self._get_max_results()
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        html_content = _make_request(url, self._get_timeout())

        if html_content and html_content.startswith(("Error:", "HTTP Error", "URL Error")):
            return f"Search failed: {html_content}"

        if not html_content:
            return "Error: Could not connect to search engine."

        results = []
        result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'
        matches = re.findall(result_pattern, html_content, re.DOTALL | re.IGNORECASE)

        if not matches:
            link_pattern = r'<a[^>]*rel="nofollow"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'
            links = re.findall(link_pattern, html_content)
            snippets = re.findall(snippet_pattern, html_content)

            for i, (url, title) in enumerate(links[:num_results]):
                snippet = snippets[i] if i < len(snippets) else ""
                if url.startswith('//duckduckgo.com/l/?'):
                    actual_url = re.search(r'uddg=([^&]+)', url)
                    if actual_url:
                        url = urllib.parse.unquote(actual_url.group(1))
                results.append({
                    'title': html.unescape(title.strip()),
                    'url': url,
                    'snippet': html.unescape(snippet.strip())
                })
        else:
            for url, title, snippet in matches[:num_results]:
                if url.startswith('//duckduckgo.com/l/?'):
                    actual_url = re.search(r'uddg=([^&]+)', url)
                    if actual_url:
                        url = urllib.parse.unquote(actual_url.group(1))
                results.append({
                    'title': html.unescape(title.strip()),
                    'url': url,
                    'snippet': html.unescape(snippet.strip())
                })

        if not results:
            return f"No results found for: {query}"

        lines = [f"Search Results for: {query}", "=" * 50, ""]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   URL: {r['url']}")
            if r['snippet']:
                lines.append(f"   {r['snippet'][:200]}")
            lines.append("")

        lines.append(f"Found {len(results)} results.")
        return "\n".join(lines)

    def wikipedia(self, topic: str, sentences: int = 5) -> str:
        """
        Search Wikipedia for information (FREE API).

        Args:
            topic: Topic to search
            sentences: Number of sentences (default: 5)

        Returns:
            Wikipedia summary with source URL.
        """
        if not topic or not topic.strip():
            return "Error: Please provide a topic."

        encoded_topic = urllib.parse.quote(topic)
        search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"

        try:
            req = urllib.request.Request(
                search_url,
                headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=self._get_timeout()) as response:
                data = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return self._wikipedia_search(topic, sentences)
            return f"Wikipedia error: {e.code} - {e.reason}"
        except Exception as e:
            return f"Error accessing Wikipedia: {str(e)}"

        title = data.get('title', topic)
        extract = data.get('extract', '')
        page_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')

        if not extract:
            return self._wikipedia_search(topic, sentences)

        if sentences > 0:
            sentence_list = re.split(r'(?<=[.!?])\s+', extract)
            extract = ' '.join(sentence_list[:sentences])

        lines = [
            f"Wikipedia: {title}",
            "=" * 50,
            "",
            extract,
            "",
            f"Source: {page_url}" if page_url else "",
        ]
        return "\n".join(lines)

    def _wikipedia_search(self, query: str, sentences: int = 5) -> str:
        """Search Wikipedia when direct lookup fails."""
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json&srlimit=5"

        try:
            req = urllib.request.Request(search_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=self._get_timeout()) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return f"Wikipedia search error: {str(e)}"

        results = data.get('query', {}).get('search', [])

        if not results:
            return f"No Wikipedia articles found for: {query}"

        first_title = results[0].get('title', '')
        if first_title:
            return self.wikipedia(first_title, sentences)

        lines = [f"Wikipedia Search Results for: {query}", "=" * 50, ""]
        for i, r in enumerate(results[:5], 1):
            title = r.get('title', '')
            snippet = _strip_html(r.get('snippet', ''))
            lines.append(f"{i}. {title}")
            lines.append(f"   {snippet[:150]}...")
            lines.append("")

        return "\n".join(lines)

    def fetch_url(self, url: str, extract_text: bool = True) -> str:
        """
        Fetch content from any URL and extract text.

        Args:
            url: The URL to fetch
            extract_text: If True, extract clean text; if False, return raw HTML

        Returns:
            Page content as text.
        """
        if not url or not url.strip():
            return "Error: Please provide a URL."

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        content = _make_request(url, self._get_timeout())

        if content and content.startswith(("Error:", "HTTP Error", "URL Error")):
            return f"Failed to fetch URL: {content}"

        if not content:
            return "Error: Could not fetch the URL."

        if extract_text:
            text = _extract_text_content(content, self._get_max_content())
        else:
            text = content[:self._get_max_content()]

        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = html.unescape(title_match.group(1).strip()) if title_match else "Web Page"

        lines = [
            f"Content from: {url}",
            f"Title: {title}",
            "=" * 50,
            "",
            text
        ]
        return "\n".join(lines)

    def news_search(self, query: str, num_results: int = 5) -> str:
        """
        Search for recent news articles.

        Args:
            query: News topic to search
            num_results: Number of results

        Returns:
            Recent news articles.
        """
        if not query or not query.strip():
            return "Error: Please provide a search query."

        return self.web_search(f"{query} news", num_results)

    def get_weather(self, location: str) -> str:
        """
        Get current weather for a location (uses wttr.in - FREE).

        Args:
            location: City name or location

        Returns:
            Current weather information.
        """
        if not location or not location.strip():
            return "Error: Please provide a location."

        encoded_location = urllib.parse.quote(location)
        url = f"https://wttr.in/{encoded_location}?format=j1"

        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=self._get_timeout()) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            try:
                text_url = f"https://wttr.in/{encoded_location}?format=3"
                req = urllib.request.Request(text_url, headers={'User-Agent': USER_AGENT})
                with urllib.request.urlopen(req, timeout=self._get_timeout()) as response:
                    return f"Weather: {response.read().decode('utf-8')}"
            except:
                return f"Error getting weather: {str(e)}"

        try:
            current = data.get('current_condition', [{}])[0]
            area = data.get('nearest_area', [{}])[0]

            city = area.get('areaName', [{}])[0].get('value', location)
            country = area.get('country', [{}])[0].get('value', '')

            temp_c = current.get('temp_C', '?')
            temp_f = current.get('temp_F', '?')
            feels_c = current.get('FeelsLikeC', '?')
            humidity = current.get('humidity', '?')
            desc = current.get('weatherDesc', [{}])[0].get('value', 'Unknown')
            wind_kmph = current.get('windspeedKmph', '?')
            wind_dir = current.get('winddir16Point', '')

            lines = [
                f"Weather for {city}, {country}",
                "=" * 40,
                f"Condition: {desc}",
                f"Temperature: {temp_c}°C / {temp_f}°F",
                f"Feels like: {feels_c}°C",
                f"Humidity: {humidity}%",
                f"Wind: {wind_kmph} km/h {wind_dir}",
            ]
            return "\n".join(lines)

        except Exception as e:
            return f"Error parsing weather data: {str(e)}"

    def quick_answer(self, question: str) -> str:
        """
        Try to get a quick answer using DuckDuckGo Instant Answers.

        Args:
            question: A question or topic

        Returns:
            Quick answer if available, otherwise search results.
        """
        if not question or not question.strip():
            return "Error: Please provide a question."

        encoded_q = urllib.parse.quote_plus(question)
        url = f"https://api.duckduckgo.com/?q={encoded_q}&format=json&no_html=1&skip_disambig=1"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=self._get_timeout()) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return self.web_search(question, 5)

        abstract = data.get('Abstract', '')
        answer = data.get('Answer', '')
        definition = data.get('Definition', '')

        if answer:
            return f"Answer: {answer}\n\nSource: DuckDuckGo"

        if abstract:
            source = data.get('AbstractSource', 'DuckDuckGo')
            source_url = data.get('AbstractURL', '')
            return f"{abstract}\n\nSource: {source}\n{source_url}"

        if definition:
            return f"Definition: {definition}\n\nSource: DuckDuckGo"

        return self.web_search(question, 5)

    def translate(self, text: str, to_lang: str = "en", from_lang: str = "auto") -> str:
        """
        Translate text using MyMemory Translation API (free, limited).

        Args:
            text: Text to translate
            to_lang: Target language code (e.g., "en", "de", "fr")
            from_lang: Source language code or "auto"

        Returns:
            Translated text.
        """
        if not text or not text.strip():
            return "Error: Please provide text to translate."

        try:
            encoded_text = urllib.parse.quote(text)
            lang_pair = f"{from_lang}|{to_lang}" if from_lang != "auto" else f"en|{to_lang}"
            url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={lang_pair}"

            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=self._get_timeout()) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data.get('responseStatus') == 200:
                translated = data.get('responseData', {}).get('translatedText', '')
                if translated:
                    return f"Translation ({from_lang} → {to_lang}):\n{translated}\n\nOriginal: {text}"
        except Exception:
            pass

        return f"Translation service temporarily unavailable. Original text: {text}"
