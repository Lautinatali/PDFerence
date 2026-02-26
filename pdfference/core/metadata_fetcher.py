"""
Metadata fetching from multiple sources with fallback chain.
"""
import re
from typing import Optional
import requests
from bs4 import BeautifulSoup

from .models import Paper
from ..config import Config
from ..utils.logger import Logger


class MetadataFetcher:
    """
    Fetch paper metadata from multiple sources in fallback order:
    1. CrossRef (fast, reliable for basic metadata)
    2. OpenAlex (includes topics, better abstracts)
    3. PubMed (fallback for biomedical papers)
    """
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger("MetadataFetcher")
        self.config = Config()
    
    def fetch(self, doi: str) -> Optional[Paper]:
        """
        Fetch complete metadata via fallback chain.
        
        Args:
            doi: DOI identifier (with or without https://doi.org/ prefix)
        
        Returns:
            Paper object or None if all sources fail
        """
        clean_doi = doi.replace("https://doi.org/", "").strip()
        
        self.logger.debug(f"Fetching metadata for DOI: {clean_doi}")
        
        # Tier 1: CrossRef (primary source)
        paper = self._from_crossref(clean_doi)
        if paper is None:
            self.logger.warning(f"CrossRef lookup failed for {clean_doi}")
            return None
        
        # Tier 2: OpenAlex (enhance with abstract and topics)
        try:
            openales_data = self._from_openalex(clean_doi)
            if openales_data:
                # Use OpenAlex abstract if better
                if openales_data.get("abstract"):
                    paper.abstract = openales_data["abstract"]
                if openales_data.get("topics"):
                    paper.topics = openales_data["topics"]
                self.logger.debug(f"Enhanced with OpenAlex data for {clean_doi}")
        except Exception as e:
            self.logger.debug(f"OpenAlex enhancement skipped: {e}")
        
        # Tier 3: PubMed (fallback for abstract if still missing)
        if not paper.abstract or "No abstract" in paper.abstract:
            try:
                abstract = self._from_pubmed(clean_doi)
                if abstract:
                    paper.abstract = abstract
                    self.logger.debug(f"Abstract fetched from PubMed for {clean_doi}")
            except Exception as e:
                self.logger.debug(f"PubMed fallback skipped: {e}")
        
        # Ensure abstract is never empty
        if not paper.abstract:
            paper.abstract = "No abstract available."
        
        self.logger.success(f"Metadata fetched: {paper.display_authors} ({paper.year})")
        return paper
    
    def _from_crossref(self, doi: str) -> Optional[Paper]:
        """Fetch from CrossRef API."""
        try:
            url = f"https://api.crossref.org/works/{doi}"
            r = requests.get(url, timeout=self.config.CROSSREF_TIMEOUT)
            r.raise_for_status()
            
            data = r.json()["message"]
            
            return Paper(
                doi=data.get("DOI", ""),
                title=(data.get("title", []) or [""])[0],
                authors=[
                    f"{a.get('family', '')}, {a.get('given', '')}"
                    for a in data.get("author", [])
                ],
                year=(data.get("issued", {}).get("date-parts", [[None]]) or [[None]])[0][0],
                abstract=data.get("abstract", "") or "",
                journal=(data.get("container-title", []) or [""])[0],
                url=data.get("URL", f"https://doi.org/{doi}"),
            )
        except (requests.exceptions.RequestException, IndexError, KeyError, TypeError) as e:
            self.logger.debug(f"CrossRef error: {e}")
            return None
    
    def _from_openalex(self, doi: str) -> Optional[dict]:
        """Fetch from OpenAlex API."""
        try:
            url = f"https://api.openalex.org/works/https://doi.org/{doi}"
            r = requests.get(url, timeout=self.config.OPENALEX_TIMEOUT)
            r.raise_for_status()
            
            data = r.json()
            
            # Rebuild abstract from inverted index
            abstract = self._rebuild_abstract_from_index(
                data.get("abstract_inverted_index")
            )
            
            return {
                "abstract": abstract,
                "topics": [t.get("display_name") for t in data.get("topics", [])],
            }
        except Exception as e:
            self.logger.debug(f"OpenAlex error: {e}")
            return None
    
    def _from_pubmed(self, doi: str) -> Optional[str]:
        """Fetch abstract from PubMed via DOI → PMID → Abstract."""
        try:
            # Step 1: Search for PMID using DOI
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": doi,
                "retmode": "json",
                "email": self.config.PUBMED_EMAIL,
            }
            
            r = requests.get(search_url, params=params, timeout=10)
            r.raise_for_status()
            
            data = r.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                self.logger.debug(f"No PubMed results for DOI: {doi}")
                return None
            
            pmid = id_list[0]
            
            # Step 2: Fetch XML record
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml",
                "email": self.config.PUBMED_EMAIL,
            }
            
            xml_resp = requests.get(fetch_url, params=fetch_params, timeout=10)
            xml_resp.raise_for_status()
            
            # Step 3: Parse XML for abstract
            soup = BeautifulSoup(xml_resp.content, 'xml')
            abstract_elem = soup.find("AbstractText")
            
            if abstract_elem:
                return abstract_elem.get_text().strip()
            
            self.logger.debug(f"No abstract in PubMed record (PMID: {pmid})")
            return None
            
        except Exception as e:
            self.logger.debug(f"PubMed error: {e}")
            return None
    
    @staticmethod
    def _rebuild_abstract_from_index(inverted_index: Optional[dict]) -> Optional[str]:
        """Rebuild abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return None
        
        # Inverted index format: {"word": [pos1, pos2, ...], ...}
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        
        if not word_positions:
            return None
        
        # Sort by position and join
        word_positions.sort()
        return " ".join([word for _, word in word_positions])
