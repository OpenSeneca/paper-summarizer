#!/usr/bin/env python3
"""
Paper/Article Summarizer CLI — Structured Summary Generator

Summarizes research papers and articles from URLs or arXiv IDs into structured format.

Usage:
    paper-summarizer summarize <url>
    paper-summarizer arxiv <arxiv-id>
    paper-summarizer batch <urls-file>

Examples:
    paper-summarizer summarize https://arxiv.org/abs/2301.07041
    paper-summarizer arxiv 2301.07041
    paper-summarizer batch papers.txt
"""

import argparse
import sys
import json
from typing import Dict, List, Optional
import re

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log_info(message: str) -> None:
    """Print informational message."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")


def log_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def log_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def log_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def extract_arxiv_id(text: str) -> Optional[str]:
    """Extract arXiv ID from URL or text."""
    # Match arXiv ID pattern (e.g., 2301.07041)
    pattern = r'\b(\d{4}\.\d{5})\b'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def fetch_arxiv_paper(arxiv_id: str) -> Optional[Dict]:
    """Fetch paper metadata from arXiv API."""
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET
    
    try:
        log_info(f"Fetching paper from arXiv: {arxiv_id}")
        
        # Query arXiv API
        query = f"id:{arxiv_id}"
        url = f"http://export.arxiv.org/api/query?id_list={query}&max_results=1"
        
        with urllib.request.urlopen(url) as response:
            xml_data = response.read().decode('utf-8')
        
        # Parse XML response
        root = ET.fromstring(xml_data)
        entry = root.find('{http://www.w3.org/2005/Atom}entry')
        
        if entry is None:
            log_error(f"Paper not found: {arxiv_id}")
            return None
        
        # Extract metadata
        title = entry.find('{http://www.w3.org/2005/Atom}title').text
        authors = [author.find('{http://www.w3.org/2005/Atom}name').text 
                   for author in entry.findall('{http://www.w3.org/2005/Atom}author')]
        abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text
        published = entry.find('{http://www.w3.org/2005/Atom}published').text
        arxiv_url = entry.find('{http://www.w3.org/2005/Atom}id').text
        
        # Extract PDF URL
        for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
            if link.attrib.get('type') == 'application/pdf':
                pdf_url = link.attrib.get('href')
                break
        else:
            pdf_url = None
        
        return {
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'arxiv_id': arxiv_id,
            'published': published,
            'url': arxiv_url,
            'pdf_url': pdf_url
        }
        
    except Exception as e:
        log_error(f"Error fetching arXiv paper: {e}")
        return None


def summarize_paper(arxiv_id: str) -> Optional[Dict]:
    """Generate structured summary from paper data."""
    paper_data = fetch_arxiv_paper(arxiv_id)
    if not paper_data:
        return None
    
    # Generate structured summary
    title = paper_data['title']
    abstract = paper_data['abstract']
    authors = paper_data['authors']
    
    # Extract key findings (first 3 sentences of abstract)
    key_findings = '. '.join(abstract.split('.')[:3]) + '.'
    
    # Extract methodology (look for methodology-related keywords)
    methodology_keywords = ['method', 'approach', 'technique', 'algorithm', 'framework', 'model']
    methodology = "Not explicitly stated in abstract"
    for keyword in methodology_keywords:
        if keyword.lower() in abstract.lower():
            methodology = f"Uses {keyword} (see abstract for details)"
            break
    
    # Extract implications (last sentence of abstract)
    implications = abstract.split('.')[-2] if len(abstract.split('.')) > 2 else "Review abstract for implications"
    
    return {
        'title': title,
        'authors': authors[:5],  # Limit to 5 authors
        'arxiv_id': arxiv_id,
        'url': paper_data['url'],
        'pdf_url': paper_data['pdf_url'],
        'published': paper_data['published'],
        'key_findings': key_findings,
        'methodology': methodology,
        'implications': implications,
        'full_abstract': abstract
    }


def format_summary(summary: Dict, output_format: str = 'markdown') -> str:
    """Format summary as Markdown or JSON."""
    if output_format == 'json':
        return json.dumps(summary, indent=2)
    
    # Markdown format
    output = f"""# {summary['title']}

**arXiv ID:** {summary['arxiv_id']}
**Published:** {summary['published']}
**URL:** {summary['url']}
**PDF:** {summary['pdf_url']}

---

## 📝 Abstract

{summary['full_abstract']}

---

## 🔑 Key Findings

{summary['key_findings']}

---

## 📋 Methodology

{summary['methodology']}

---

## 💡 Implications

{summary['implications']}

---

## 👥 Authors

{', '.join(summary['authors'])}

---

*Generated by paper-summarizer CLI*
*Useful for Marcus (AI papers) and Galen (biopharma papers)*
"""
    return output


def cmd_summarize(args: argparse.Namespace) -> None:
    """Summarize a URL (arXiv or generic)."""
    url = args.url
    
    # Check if it's an arXiv URL or ID
    arxiv_id = extract_arxiv_id(url)
    
    if arxiv_id:
        # Summarize arXiv paper
        summary = summarize_paper(arxiv_id)
        if summary:
            print(format_summary(summary, args.format))
        else:
            log_error(f"Failed to summarize paper: {url}")
            sys.exit(1)
    else:
        log_warning("Non-arXiv URLs not yet supported")
        log_info("Use 'paper-summarizer arxiv <arxiv-id>' for arXiv papers")
        sys.exit(1)


def cmd_arxiv(args: argparse.Namespace) -> None:
    """Summarize an arXiv paper by ID."""
    arxiv_id = args.arxiv_id
    
    # Validate arXiv ID format
    if not re.match(r'^\d{4}\.\d{5}$', arxiv_id):
        log_error("Invalid arXiv ID format. Use: YYYY.NNNNN (e.g., 2301.07041)")
        sys.exit(1)
    
    # Summarize paper
    summary = summarize_paper(arxiv_id)
    if summary:
        print(format_summary(summary, args.format))
    else:
        log_error(f"Failed to summarize arXiv paper: {arxiv_id}")
        sys.exit(1)


def cmd_batch(args: argparse.Namespace) -> None:
    """Summarize multiple papers from a file."""
    urls_file = args.urls_file
    
    # Read URLs from file
    try:
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        log_error(f"File not found: {urls_file}")
        sys.exit(1)
    
    log_info(f"Processing {len(urls)} papers...")
    
    # Summarize each paper
    for url in urls:
        print(f"\n{'='*80}\n")
        print(f"Processing: {url}\n")
        print(f"{'='*80}\n")
        
        arxiv_id = extract_arxiv_id(url)
        
        if arxiv_id:
            summary = summarize_paper(arxiv_id)
            if summary:
                print(format_summary(summary, args.format))
            else:
                log_warning(f"Failed to summarize: {url}")
        else:
            log_warning(f"Skipping non-arXiv URL: {url}")


def main():
    parser = argparse.ArgumentParser(
        description='Paper/Article Summarizer CLI — Structured summary generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  paper-summarizer summarize https://arxiv.org/abs/2301.07041
  paper-summarizer arxiv 2301.07041
  paper-summarizer batch papers.txt --json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Summarize command
    summarize_parser = subparsers.add_parser('summarize', help='Summarize a URL (arXiv or generic)')
    summarize_parser.add_argument('url', help='URL to summarize')
    summarize_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='Output format (default: markdown)')
    summarize_parser.set_defaults(func=cmd_summarize)
    
    # ArXiv command
    arxiv_parser = subparsers.add_parser('arxiv', help='Summarize an arXiv paper by ID')
    arxiv_parser.add_argument('arxiv_id', help='arXiv ID (format: YYYY.NNNNN)')
    arxiv_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='Output format (default: markdown)')
    arxiv_parser.set_defaults(func=cmd_arxiv)
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Summarize multiple papers from a file')
    batch_parser.add_argument('urls_file', help='File containing list of URLs (one per line)')
    batch_parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='Output format (default: markdown)')
    batch_parser.set_defaults(func=cmd_batch)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
