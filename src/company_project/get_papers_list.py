import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple
from .pubmed_api_client import search_pubmed_ids, fetch_pubmed_details
from .xml_parser import parse_pubmed_article_xml, get_non_academic_authors

def main():
    parser = argparse.ArgumentParser(
        description="Fetch research papers from PubMed and identify non-academic authors from pharmaceutical/biotech companies.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "query",
        type=str,
        help="The search query for PubMed (e.g., 'cancer immunology')."
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Print debug information during execution."
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Specify the filename to save the results. If not provided, output to console."
    )

    args = parser.parse_args()

    search_query = args.query
    debug_mode = args.debug
    output_filename = args.file

    if debug_mode:
        print(f"DEBUG: Search query: '{search_query}'")
        print(f"DEBUG: Debug mode: {debug_mode}")
        print(f"DEBUG: Output filename: {output_filename if output_filename else 'console'}")

    try:
        if debug_mode:
            print("DEBUG: Fetching PubMed IDs based on query...")
        
        # Step 1: Fetch PubMed IDs using the correct function
        pubmed_ids = search_pubmed_ids(search_query)

        if not pubmed_ids:
            print("No PubMed IDs found for the given query.")
            return

        if debug_mode:
            print(f"DEBUG: Found {len(pubmed_ids)} PubMed IDs. Fetching details...")

        # Step 2: Fetch article details using the correct function
        pubmed_xml_response = fetch_pubmed_details(pubmed_ids)

        if not pubmed_xml_response:
            print("No articles found or error fetching details from PubMed API.")
            return

        # Prepare for CSV output
        csv_data: List[List[str]] = []
        csv_data.append([
            "PubmedID",
            "Title",
            "Publication Date",
            "Non-academic Author(s)",
            "Company Affiliation(s)",
            "Corresponding Author Email"
        ])

        total_articles_processed = 0
        relevant_papers_count = 0

        # PubMed API can return a single EFetchResult XML with multiple PubMedArticle elements
        root = ET.fromstring(pubmed_xml_response)
        articles = root.findall('.//PubmedArticle')

        if debug_mode:
            print(f"DEBUG: Found {len(articles)} articles in PubMed API response for details.")

        for article_element in articles:
            total_articles_processed += 1
            article_xml_string = ET.tostring(article_element, encoding='unicode')
            
            parsed_article = parse_pubmed_article_xml(article_xml_string)
            
            if parsed_article:
                non_academic_authors, company_affiliations = get_non_academic_authors(parsed_article, debug_mode)
                
                if non_academic_authors: # Check if there are any non-academic authors identified
                    relevant_papers_count += 1
                    pubmed_id = parsed_article.get("pubmed_id", "N/A")
                    title = parsed_article.get("title", "N/A")
                    pub_date = parsed_article.get("publication_date", "N/A")
                    corresponding_email = parsed_article.get("corresponding_author_email", "N/A")

                    # Join lists for CSV output
                    authors_str = "; ".join(non_academic_authors)
                    affiliations_str = "; ".join(company_affiliations)

                    csv_data.append([
                        pubmed_id,
                        title,
                        pub_date,
                        authors_str,
                        affiliations_str,
                        corresponding_email
                    ])
                    if debug_mode:
                        print(f"DEBUG: Paper '{pubmed_id}' (Title: '{title}') found relevant.")
                else:
                    if debug_mode:
                        print(f"DEBUG: Paper '{parsed_article.get('pubmed_id', 'N/A')}' (Title: '{parsed_article.get('title', 'N/A')}') has no identified non-academic authors.")
            else:
                if debug_mode:
                    print(f"DEBUG: Failed to parse an article XML.")

        if relevant_papers_count == 0:
            print(f"Found 0 relevant papers with pharmaceutical/biotech affiliations among {total_articles_processed} processed articles.")
            return

        if output_filename:
            with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerows(csv_data)
            print(f"Successfully saved {relevant_papers_count} relevant papers to '{output_filename}'")
        else:
            for row in csv_data:
                print(",".join(f'"{item}"' for item in row)) # CSV format

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        if debug_mode:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
