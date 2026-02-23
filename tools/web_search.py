import os
from typing import List
from urllib.parse import urlparse

from core.bias_detector import score_source_bias
from core.cache import make_cache_key, search_cache
from core.rate_limiter import retry_with_backoff, tavily_limiter
from schemas import DomainType, SourceMetadata


class WebSearchTool:
    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY environment variable not set. Please ensure it is defined in your .env file.")
        
        self.api_key = api_key
        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=api_key)
            self.use_official_client = True
        except ImportError:
            self.use_official_client = False

    def search(self, query: str, max_results: int = 5) -> List[SourceMetadata]:
        # Check cache first
        cache_key = make_cache_key("search", query, str(max_results))
        cached = search_cache.get(cache_key)
        if cached is not None:
            return cached

        if self.use_official_client:
            results = self._search_with_official_client(query, max_results)
        else:
            results = self._search_with_requests(query, max_results)

        # Store in cache on success
        if results:
            search_cache.put(cache_key, results)
        return results

    def _search_with_official_client(self, query: str, max_results: int) -> List[SourceMetadata]:
        response = retry_with_backoff(
            self.client.search,
            query=query,
            max_results=max_results,
            max_retries=3,
            base_delay=0.5,
            rate_limiter=tavily_limiter,
            service_name="tavily",
        )
        
        sources = []
        for result in response.get("results", []):
            title = result.get("title", "")
            url = result.get("url", "")
            content = result.get("content", "")
            published_date = result.get("published_date") or result.get("publishedDate")
            
            if not url:
                continue
            
            try:
                summary = content[:400] if content else ""
                domain_type = self._infer_domain_type(url)
                source = SourceMetadata(
                    title=title,
                    url=url,
                    summary=summary,
                    publication_date=published_date,
                    domain_type=domain_type,
                    author_present=False,
                    opinion_score=score_source_bias(summary)
                )
                sources.append(source)
            except Exception:
                continue
        
        return sources

    def _search_with_requests(self, query: str, max_results: int) -> List[SourceMetadata]:
        import requests
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results
        }
        
        try:
            response = retry_with_backoff(
                requests.post,
                url,
                json=payload,
                timeout=10,
                max_retries=3,
                base_delay=0.5,
                rate_limiter=tavily_limiter,
                service_name="tavily_requests",
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []
        
        sources = []
        for result in data.get("results", []):
            title = result.get("title", "")
            url_str = result.get("url", "")
            content = result.get("content", "")
            published_date = result.get("published_date") or result.get("publishedDate")
            
            if not url_str:
                continue
            
            try:
                summary = content[:400] if content else ""
                domain_type = self._infer_domain_type(url_str)
                source = SourceMetadata(
                    title=title,
                    url=url_str,
                    summary=summary,
                    publication_date=published_date,
                    domain_type=domain_type,
                    author_present=False,
                    opinion_score=0.5
                )
                sources.append(source)
            except Exception:
                continue
        
        return sources

    def _infer_domain_type(self, url: str) -> DomainType:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if ".edu" in domain:
            return DomainType.edu
        elif ".gov" in domain:
            return DomainType.gov
        elif any(x in domain for x in ["news", "cnn", "bbc", "reuters", "apnews", "nytimes"]):
            return DomainType.news
        elif any(x in domain for x in ["blog", "medium", "substack", "wordpress"]):
            return DomainType.blog
        else:
            return DomainType.other
