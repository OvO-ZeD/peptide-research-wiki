"""
Local LLM integration for Peptide Research Wiki.
Uses Ollama (ministral-3:14b) to answer medical/peptide questions
when the local database doesn't have strong matches.
"""

import json
import urllib.request
import urllib.parse
import re
import time

OLLAMA_API = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "ministral-3:14b"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
TIMEOUT = 30


def fetch_json(url, timeout=TIMEOUT):
    """Fetch JSON from a URL with timeout."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PeptideDB/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_text(url, timeout=TIMEOUT):
    """Fetch plain text from a URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PeptideDB/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


def query_ollama(messages, model=DEFAULT_MODEL, max_tokens=1024):
    """Send a chat request to Ollama and return the response text."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
        }
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            OLLAMA_API,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "")
    except Exception:
        return None


def search_pubmed_general(query, retmax=6):
    """Search PubMed broadly for any medical/peptide topic.
    Returns list of {title, pubdate, source, authors, pmid, abstract}."""
    # Use a broad search — no peptide-specific filter
    search_url = (
        f"{PUBMED_SEARCH_URL}?db=pubmed&retmode=json&retmax={retmax}"
        f"&sort=relevance&term={urllib.parse.quote(query)}"
    )
    search_data = fetch_json(search_url)
    if not search_data:
        return []

    ids = search_data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    # Fetch abstracts via efetch
    fetch_url = (
        f"{PUBMED_FETCH_URL}?db=pubmed&retmode=xml&rettype=abstract"
        f"&id={','.join(ids)}"
    )
    xml_text = fetch_text(fetch_url)
    if not xml_text:
        return []

    articles = _parse_pubmed_xml(xml_text, ids)
    return articles


def _parse_pubmed_xml(xml_text, ids):
    """Minimal XML parser for PubMed abstracts — no external deps."""
    articles = []
    for pmid in ids:
        title = _extract_tag(xml_text, pmid, "ArticleTitle")
        abstract = _extract_abstract(xml_text, pmid)
        pubdate = _extract_tag(xml_text, pmid, "PubDate")
        source = _extract_tag(xml_text, pmid, "Journal")
        if not source:
            source = _extract_tag(xml_text, pmid, "Title")
        authors = _extract_authors(xml_text, pmid)

        if title:
            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract or "",
                "pubdate": pubdate or "Unknown",
                "source": source or "PubMed",
                "authors": authors,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
    return articles


def _extract_tag(xml, pmid, tag):
    """Extract first occurrence of <tag> after the PubmedArticle containing pmid."""
    idx = xml.find(f'<PubmedArticle>{pmid}')
    if idx == -1:
        idx = 0
    start = xml.find(f"<{tag}>", idx)
    if start == -1:
        return None
    end = xml.find(f"</{tag}>", start)
    if end == -1:
        return None
    return _strip_xml(xml[start + len(tag) + 2:end])


def _extract_abstract(xml, pmid):
    """Extract abstract text, handling multiple AbstractText sections."""
    idx = xml.find(f'<PubmedArticle>{pmid}')
    if idx == -1:
        idx = 0
    start = xml.find("<Abstract>", idx)
    if start == -1:
        return None
    end = xml.find("</Abstract>", start)
    if end == -1:
        return None

    abstract_xml = xml[start:end]
    parts = []
    pos = 0
    while True:
        at_start = abstract_xml.find("<AbstractText", pos)
        if at_start == -1:
            break
        label_start = abstract_xml.find('Label="', at_start)
        label = ""
        if label_start != -1 and label_start < at_start + 200:
            label_end = abstract_xml.find('"', label_start + 7)
            if label_end != -1:
                label = abstract_xml[label_start + 7:label_end] + ": "
        content_start = abstract_xml.find(">", at_start) + 1
        content_end = abstract_xml.find("</AbstractText>", content_start)
        if content_end == -1:
            break
        text = _strip_xml(abstract_xml[content_start:content_end]).strip()
        if text:
            parts.append(label + text)
        pos = content_end + 14

    return " ".join(parts) if parts else None


def _extract_authors(xml, pmid):
    """Extract author names."""
    idx = xml.find(f'<PubmedArticle>{pmid}')
    if idx == -1:
        idx = 0
    start = xml.find("<AuthorList>", idx)
    if start == -1:
        return []
    end = xml.find("</AuthorList>", start)
    if end == -1:
        return []

    authors = []
    pos = start
    while True:
        a_start = xml.find("<Author>", pos, end)
        if a_start == -1:
            break
        a_end = xml.find("</Author>", a_start)
        if a_end == -1:
            break

        last = _extract_simple_tag(xml, a_start, "LastName")
        first = _extract_simple_tag(xml, a_start, "ForeName")
        if last:
            name = f"{first or ''} {last}".strip()
            if name:
                authors.append(name)
        pos = a_end + 9

    return authors[:5]


def _extract_simple_tag(text, start_pos, tag):
    """Extract a simple XML tag value starting from start_pos."""
    s = text.find(f"<{tag}>", start_pos)
    if s == -1:
        return None
    e = text.find(f"</{tag}>", s)
    if e == -1:
        return None
    return text[s + len(tag) + 2:e]


def _strip_xml(text):
    """Remove XML/HTML tags from text."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    return text.strip()


def build_medical_prompt(question, articles):
    """Build a system + user prompt for medical/peptide Q&A."""
    system = (
        "You are a medical research assistant specializing in peptides, longevity, and biochemistry. "
        "Answer the user's question based on the PubMed research articles provided below. "
        "Be accurate, balanced, and cite specific findings when possible. "
        "If the articles don't contain enough information, say so clearly. "
        "Do NOT give medical advice — frame everything as research findings. "
        "Keep answers concise (2-4 paragraphs) and use plain language."
    )

    context = ""
    if articles:
        context = "Here are relevant PubMed articles:\n\n"
        for i, a in enumerate(articles, 1):
            context += f"[{i}] {a['title']}\n"
            if a.get("abstract"):
                context += f"    Abstract: {a['abstract'][:500]}\n"
            context += f"    Source: {a.get('source', 'PubMed')} ({a.get('pubdate', '')})\n"
            context += f"    Link: {a.get('link')}\n\n"
    else:
        context = "No specific PubMed articles were found for this query. Answer based on your general medical knowledge."

    user_prompt = f"{context}\nUser question: {question}\n\nProvide a thorough answer based on the research above:"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]


def generate_answer(question, max_tokens=512):
    """Main entry point: search PubMed, build prompt, call Ollama.
    Returns dict with {answer, citations, source} or None on failure."""
    articles = search_pubmed_general(question, retmax=6)

    messages = build_medical_prompt(question, articles)

    answer = query_ollama(messages, max_tokens=max_tokens)

    if not answer:
        return None


    # Build citations from articles
    citations = []
    for a in articles:
        citations.append({
            "pmid": a["pmid"],
            "title": a["title"][:120],
            "link": a["link"],
            "source": a.get("source", "PubMed"),
        })

    return {
        "answer": answer.strip(),
        "citations": citations,
        "source": "llm",
        "pubmed_count": len(articles),
    }


def check_ollama_available():
    """Quick check if Ollama is running."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            return models
    except Exception:
        return None
