import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import re

def parse_pubmed_article_xml(xml_content: str) -> Optional[Dict[str, Any]]:
    """
    Parses the XML content of a single PubMedArticle and extracts relevant details.

    Args:
        xml_content (str): The XML content for a PubMed article.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing parsed data if successful, None otherwise.
    """
    try:
        root = ET.fromstring(xml_content)

        pubmed_id_element = root.find('.//MedlineCitation/PMID')
        pubmed_id = pubmed_id_element.text if pubmed_id_element is not None else 'N/A'

        title_element = root.find('.//Article/ArticleTitle')
        title = title_element.text if title_element is not None else 'N/A'

        pub_date_element = root.find('.//Article/Journal/JournalIssue/PubDate')
        publication_date = 'N/A'
        if pub_date_element is not None:
            year_element = pub_date_element.find('Year')
            month_element = pub_date_element.find('Month')
            day_element = pub_date_element.find('Day')
            medline_date_element = pub_date_element.find('MedlineDate')
            
            if year_element is not None:
                publication_date = year_element.text
                if month_element is not None:
                    publication_date += f"-{month_element.text}"
                if day_element is not None:
                    publication_date += f"-{day_element.text}"
            elif medline_date_element is not None:
                publication_date = medline_date_element.text

        authors_data: List[Dict[str, str]] = []
        corresponding_author_email: Optional[str] = None

        author_list_element = root.find('.//AuthorList')
        if author_list_element is not None:
            for author_element in author_list_element.findall('Author'):
                last_name_element = author_element.find('LastName')
                fore_name_element = author_element.find('ForeName')
                initials_element = author_element.find('Initials')
                
                author_name = f"{fore_name_element.text} {last_name_element.text}" if fore_name_element is not None and last_name_element is not None \
                            else last_name_element.text if last_name_element is not None \
                            else initials_element.text if initials_element is not None \
                            else 'Unknown Author'

                affiliations = []
                for affiliation_element in author_element.findall('.//Affiliation'):
                    if affiliation_element is not None and affiliation_element.text:
                        affiliations.append(affiliation_element.text.strip())
                
                found_emails = []
                for aff in affiliations:
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', aff)
                    if email_match:
                        found_emails.append(email_match.group(0))

                if found_emails and corresponding_author_email is None:
                    corresponding_author_email = found_emails[0]

                authors_data.append({
                    "name": author_name,
                    "affiliations": affiliations,
                    "is_corresponding": False
                })

        return {
            "pubmed_id": pubmed_id,
            "title": title,
            "publication_date": publication_date,
            "authors": authors_data,
            "corresponding_author_email": corresponding_author_email
        }

    except ET.ParseError as e:
        print(f"Error parsing XML for a PubMed article: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during XML parsing: {e}")
        return None

def identify_company_affiliation(affiliation_text: str, debug_mode: bool = False) -> Optional[str]:
    """
    Identifies if an affiliation text belongs to a pharmaceutical or biotech company.
    """
    pharmaceutical_keywords = [
        r"\bpharmaceutical\b", r"\bpharma\b", r"\bdrug company\b", r"\bbiotech\b", r"\bbiotechnology\b",
        r"\bbiosciences\b", r"\bgenomics\b", r"\btherapeutics\b", r"\bdiagnostics\b", r"\boncology solutions\b",
        r"\binc\b", r"\bllc\b", r"\bcorp\b", r"\bco\b", r"\bag\b", r"\bgmbh\b", r"\blimited\b", r"\bs\.a\.\b", r"\bpte ltd\b",
        r"\bplc\b", r"\bs\.l\.\b", # Added common company suffixes
        r"\blaboratories\b", r"\br&d\b", r"\brnd\b", r"\bresearch & development\b",
        r"abbvie", r"pfizer", r"novartis", r"roche", r"merck", r"janssen", r"astrazeneca", # Specific company names
        r"gilead", r"amgen", r"sanofi", r"bayer", r"eli lilly", r"glaxosmithkline",
        r"regeneron", r"vertex", r"biogen", r"moderna", r"biontech", r"novo nordisk",
        r"teva", r"mylan", r"daiichi sankyo", r"takeda", r"chiesi", r"grunenthal",
        r"gyala therapeutics", # Added specific company name from debug output
        r"biosfer teslab" # Added specific company name from debug output
    ]
    
    # These are general indicators of a company or research focus
    general_company_indicators = [
        r"\bpharmaceutical\b", r"\bpharma\b", r"\bbiotech\b", r"\bbiotechnology\b",
        r"\btherapeutics\b", r"\bdiagnostics\b", r"\blaboratories\b",
        r"\br&d\b", r"\brnd\b", r"\bresearch & development\b",
    ]

    # These are common company suffixes
    company_suffixes = [
        r"\binc\b", r"\bllc\b", r"\bcorp\b", r"\bco\b", r"\bag\b", r"\bgmbh\b", r"\blimited\b",
        r"\bs\.a\.\b", r"\bpte ltd\b", r"\bplc\b", r"\bs\.l\.\b"
    ]

    # Exclude "research institute" and "research center" if explicitly part of an academic institution.
    # The regex `(?! for cancer| for disease| for clinical)` attempts to prevent matching generic academic research centers.
    academic_keywords = [
        r"\buniversity\b", r"\bcollege\b", r"\bhospital\b", r"\bschool of\b", r"\bdepartment of\b",
        r"\binstitute of\b", r"\bmedical center\b", r"\bclinic\b", r"\bacademy\b", r"\bfoundation\b",
        r"\bNIH\b", r"\bCDC\b", r"\bFDA\b", r"\bWHO\b", r"\bnhs\b", r"\bhealth system\b",
        r"\bresearch center\b(?! for cancer| for disease| for clinical|for innovation|for translational)", 
        r"\bresearch institute\b(?! for cancer| for disease| for clinical|for innovation|for translational)"
    ]

    normalized_text = affiliation_text.lower()

    if debug_mode:
        print(f"DEBUG: Analyzing affiliation: '{affiliation_text}'")

    # Check for strong academic indicators first
    is_strong_academic = any(re.search(keyword, normalized_text) for keyword in academic_keywords)
    
    # Check for strong company indicators
    found_strong_company_keywords = any(re.search(keyword, normalized_text) for keyword in general_company_indicators)
    found_company_suffix = any(re.search(keyword, normalized_text) for keyword in company_suffixes)
    # Check for specific company names (case-insensitive and without word boundaries if they are multi-word)
    found_specific_company_name = any(keyword.lower() in normalized_text for keyword in [
        kw.replace(r"\b", "") for kw in pharmaceutical_keywords if not (kw.startswith(r"\b") and kw.endswith(r"\b")) and not any(suffix in kw for suffix in ['inc', 'llc', 'corp', 'co', 'ag', 'gmbh', 'limited', 's.a.', 'pte ltd', 'plc', 's.l.'])
    ])


    # Refined Logic:
    # An affiliation is considered company-affiliated if:
    # 1. It contains a strong company keyword OR a company suffix OR a specific company name.
    # AND
    # 2. It is NOT primarily an academic institution that lacks any of the above strong company indicators.
    is_company_affiliated = found_strong_company_keywords or found_company_suffix or found_specific_company_name

    # If it is identified as a strong academic institution AND no explicit company indicators are found, then it's academic.
    if is_strong_academic and not (found_strong_company_keywords or found_company_suffix or found_specific_company_name):
        if debug_mode:
            print(f"DEBUG: Affiliation '{affiliation_text}' identified as academic/non-company (strong academic keywords found, no strong company indicators).")
        return None

    # If it has company indicators (and wasn't strongly academic only)
    if is_company_affiliated:
        if debug_mode:
            print(f"DEBUG: Affiliation '{affiliation_text}' identified as potentially company-affiliated.")
        
        # Attempt to extract a specific company name
        # Prioritize full company name matches, then suffixes.
        for kw in pharmaceutical_keywords:
            if not (kw.startswith(r"\b") and kw.endswith(r"\b")): # Specific company names like "Gyala Therapeutics"
                if kw.lower() in normalized_text:
                    return kw.strip() # Return the exact keyword
        
        # Fallback to extract common company name patterns
        match = re.search(
            r'\b((?:[A-Z][a-z0-9\s,\.&-]+?)(?:inc|llc|corp|co|gmbh|ag|ltd|s\.a\.|pte ltd|plc|s\.l\.)\.?)\b', 
            affiliation_text, re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        
        # If no specific name or common suffix pattern, but general company indicators were found,
        # return the whole affiliation or a relevant part.
        # This part ensures something is returned if it's classified as a company.
        # For affiliations like "Immunology of Infectious Diseases Research Center..." where 'research institute' matched,
        # but the specific regex didn't, we return the original affiliation text as a company.
        return affiliation_text.strip()
    
    if debug_mode:
        print(f"DEBUG: Affiliation '{affiliation_text}' identified as academic/non-company or did not match any company keywords.")
    return None

def get_non_academic_authors(parsed_article_data: Dict[str, Any], debug_mode: bool = False) -> tuple[List[str], List[str]]:
    """
    Identifies non-academic authors and their company affiliations from parsed article data.
    """
    non_academic_authors: List[str] = []
    company_affiliations: List[str] = []
    
    authors = parsed_article_data.get("authors", [])
    
    for author in authors:
        author_name = author.get("name", "Unknown Author")
        affiliations = author.get("affiliations", [])
        
        if debug_mode:
            print(f"DEBUG: Processing author '{author_name}' affiliations: {affiliations}")

        has_company_affiliation = False
        for aff_text in affiliations:
            company_name = identify_company_affiliation(aff_text, debug_mode)
            if company_name:
                company_affiliations.append(company_name)
                has_company_affiliation = True
        
        if has_company_affiliation:
            non_academic_authors.append(author_name)
    
    return list(set(non_academic_authors)), list(set(company_affiliations))


if __name__ == "__main__":
    sample_xml = """
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation Owner="NLM" Status="MEDLINE">
                <PMID Version="1">34567890</PMID>
                <Article PubModel="Print">
                    <Journal>
                        <ISSN IssnType="Print">0001-0000</ISSN>
                        <JournalIssue CitedMedium="Print">
                            <Volume>10</Volume>
                            <Issue>5</Issue>
                            <PubDate>
                                <Year>2023</Year>
                                <Month>Oct</Month>
                                <Day>15</Day>
                            </PubDate>
                        </JournalIssue>
                        <Title>Journal of Biotech Research</Title>
                        <ISOAbbreviation>J Biotech Res</ISOAbbreviation>
                    </Journal>
                    <ArticleTitle>Novel Gene Therapy for Cancer by Biotech Company</ArticleTitle>
                    <AuthorList CompleteYN="Y">
                        <Author ValidYN="Y">
                            <LastName>Smith</LastName>
                            <ForeName>John</ForeName>
                            <Initials>J</Initials>
                            <AffiliationInfoList>
                                <AffiliationInfo>
                                    <Affiliation>University of XYZ, Dept. of Biology, City, Country.</Affiliation>
                                </AffiliationInfo>
                            </AffiliationInfoList>
                        </Author>
                        <Author ValidYN="Y">
                            <LastName>Doe</LastName>
                            <ForeName>Jane</ForeName>
                            <Initials>J</Initials>
                            <AffiliationInfoList>
                                <AffiliationInfo>
                                    <Affiliation>PharmaCo Inc., R&amp;D Department, Biotech City, Country. jane.doe@pharmaco.com</Affiliation>
                                </AffiliationInfo>
                            </AffiliationInfoList>
                        </Author>
                        <Author ValidYN="Y">
                            <LastName>Wang</LastName>
                            <ForeName>Li</ForeName>
                            <Initials>L</Initials>
                            <AffiliationInfoList>
                                <AffiliationInfo>
                                    <Affiliation>Global Bio-Solutions, Inc., Research Park, City, Country.</Affiliation>
                                </AffiliationInfo>
                            </AffiliationInfoList>
                        </Author>
                         <Author ValidYN="Y">
                            <LastName>Chen</LastName>
                            <ForeName>Wei</ForeName>
                            <Initials>W</Initials>
                            <AffiliationInfoList>
                                <AffiliationInfo>
                                    <Affiliation>AbbVie Inc., Clinical Development, North Chicago, IL, USA.</Affiliation>
                                </AffiliationInfo>
                            </AffiliationInfoList>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
         <PubmedArticle>
            <MedlineCitation Owner="NLM" Status="MEDLINE">
                <PMID Version="1">34567891</PMID>
                <Article PubModel="Print">
                    <Journal>
                        <ISSN IssnType="Print">0002-0000</ISSN>
                        <JournalIssue CitedMedium="Print">
                            <Volume>5</Volume>
                            <Issue>1</Issue>
                            <PubDate>
                                <Year>2024</Year>
                                <Month>Jan</Month>
                                <Day>1</Day>
                            </PubDate>
                        </JournalIssue>
                        <Title>Breakthrough in Immunotherapy by Academic Lab</Title>
                        <ISOAbbreviation>Nat Med</ISOAbbreviation>
                    </Journal>
                    <ArticleTitle>Breakthrough in Immunotherapy by Academic Lab</ArticleTitle>
                    <AuthorList CompleteYN="Y">
                        <Author ValidYN="Y">
                            <LastName>Brown</LastName>
                            <ForeName>Alice</ForeName>
                            <Initials>A</Initials>
                            <AffiliationInfoList>
                                <AffiliationInfo>
                                    <Affiliation>Harvard Medical School, Dept. of Oncology, Boston, MA, USA.</Affiliation>
                                </AffiliationInfo>
                            </AffiliationInfoList>
                        </Author>
                         <Author ValidYN="Y">
                            <LastName>Green</LastName>
                            <ForeName>David</ForeName>
                            <Initials>D</Initials>
                            <AffiliationInfoList>
                                <AffiliationInfo>
                                    <Affiliation>Massachusetts General Hospital, Cancer Center, Boston, MA, USA. </Affiliation>
                                </AffiliationInfo>
                            </AffiliationInfoList>
                        </Author>
                    </AuthorList>
                </Article>
            </MedlineCitation>
        </PubmedArticle>
    </PubmedArticleSet>
    """
    
    print("--- Testing parse_pubmed_article_xml and get_non_academic_authors with Debug ---")
    try:
        root_set = ET.fromstring(sample_xml)
        pubmed_articles = root_set.findall('.//PubmedArticle')
        
        for i, article_element in enumerate(pubmed_articles):
            print(f"\n--- Processing Sample Article {i+1} ---")
            article_xml_string = ET.tostring(article_element, encoding='unicode')
            
            parsed_data = parse_pubmed_article_xml(article_xml_string)
            if parsed_data:
                import json
                # print(json.dumps(parsed_data, indent=2)) # Uncomment to see full parsed data
                
                non_academic_authors, company_affiliations = get_non_academic_authors(parsed_data, debug_mode=True)
                print(f"Result: Non-academic Authors: {non_academic_authors}")
                print(f"Result: Company Affiliations: {company_affiliations}")
            else:
                print("Failed to parse sample XML for this article.")
    except ET.ParseError as e:
        print(f"Error preparing sample XML for parsing: {e}")