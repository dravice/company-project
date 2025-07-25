import requests
from typing import List, Dict, Any, Optional

EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def search_pubmed_ids(query: str, retmax: int = 20) -> List[str]:
    """
    Searches PubMed for papers matching the query and returns a list of PubMed IDs.

    Args:
        query (str): The search query string (PubMed's full query syntax is supported).
        retmax (int): The maximum number of UIDs to be retrieved.

    Returns:
        List[str]: A list of PubMed IDs (PMIDs).
    """
    esearch_url = f"{EUTILS_BASE_URL}esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax
    }
    print(f"Searching PubMed with query: '{query}'") # Debug print

    try:
        response = requests.get(esearch_url, params=params)
        response.raise_for_status()
        data = response.json()
        # The IDs are typically found under 'esearchresult' -> 'idlist'
        id_list = data.get("esearchresult", {}).get("idlist", [])
        print(f"Found {len(id_list)} PubMed IDs.") # Debug print
        return id_list
    except requests.exceptions.RequestException as e:
        print(f"Error during PubMed ID search: {e}")
        return []
    except ValueError as e:
        print(f"Error decoding JSON response for search: {e}")
        print(f"Response content: {response.text}") # Print raw response for debugging
        return []

def fetch_pubmed_details(pubmed_ids: List[str]) -> Optional[str]:
    """
    Fetches detailed information for a list of PubMed IDs.
    Returns the full XML content string for all articles.
    """
    if not pubmed_ids:
        return None 

    # Join IDs with commas for the efetch request
    id_string = ",".join(pubmed_ids)
    efetch_url = f"{EUTILS_BASE_URL}efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": id_string,
        "retmode": "xml",
        "rettype": "full"
    }
    print(f"Fetching details for {len(pubmed_ids)} PubMed IDs.") # Debug print

    try:
        response = requests.get(efetch_url, params=params)
        response.raise_for_status()
        return response.text 
    except requests.exceptions.RequestException as e:
        print(f"Error during PubMed details fetch: {e}")
        return None
