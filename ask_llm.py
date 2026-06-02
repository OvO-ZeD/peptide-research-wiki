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
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
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


def _extract_medical_keywords(query):
    """Extract meaningful medical keywords from a query, filtering slang/stop words."""
    stop_words = {
        "a","an","the","for","and","or","to","of","in","with","that",
        "is","it","on","at","by","i","me","my","we","our","you",
        "your","he","she","they","them","their","this","that","these",
        "those","am","are","was","were","be","been","being","have",
        "has","had","do","does","did","but","if","because","as",
        "until","while","about","between","through","during","before",
        "after","above","below","up","down","out","off","over","under",
        "again","further","then","once","here","there","when","where",
        "why","how","all","each","every","both","few","more","most",
        "other","some","such","no","nor","not","only","own","same",
        "so","than","too","very","just","get","something","need",
        "help","want","looking","good","best","can","what","any",
        "anything","tell","know","does","work","use","used","using",
        "please","try","trying","like","would","could","should",
        "gear","stack","cycle",
    }
    # Generic verbs that shouldn't be AND-required in PubMed search
    generic_verbs = {
        "prevent","prevention","reduce","reducing","reduction","stop","stopping",
        "treat","treatment","treating","improve","improving","improvement",
        "increase","increasing","decrease","decreasing","promote","promoting",
        "support","supporting","enhance","enhancing","boost","boosting",
        "fix","fixing","help","helping","avoid","avoiding","manage","managing",
    }
    slang_map = {
        "gear": "anabolic steroids",
        "juice": "anabolic steroids",
        "hairfall": "hair loss",
        "hairfalling": "hair loss",
        "hair fall": "hair loss",
        "fatburn": "fat oxidation",
        "fat burn": "fat oxidation",
        "gains": "muscle growth",
        "cutting": "weight loss",
        "bulking": "muscle hypertrophy",
    }
    q = query.lower().strip()
    for slang, medical in slang_map.items():
        if slang in q:
            q = q.replace(slang, medical)
    tokens = re.findall(r'[a-z]+', q)
    # Remove stop words AND generic verbs for PubMed query construction
    keywords = [t for t in tokens if t not in stop_words and t not in generic_verbs and len(t) > 2]
    if not keywords:
        keywords = [t for t in tokens if t not in stop_words and len(t) > 2]
    return keywords


def _build_pubmed_queries(keywords, raw_query):
    """Build multiple search query strings to try against PubMed."""
    queries = []

    # Extract common bigrams/phrases from raw query (after slang mapping)
    raw_lower = raw_query.lower()
    common_phrases = [
        "hair loss", "muscle growth", "weight loss", "fat loss",
        "anabolic steroids", "growth hormone", "insulin resistance",
        "blood pressure", "heart disease", "oxidative stress",
        "immune system", "stem cell", "wound healing", "gut health",
        "lean mass", "body composition", "joint pain", "muscle recovery",
    ]
    phrases_in_query = [f'"{p}"' for p in common_phrases if p in raw_lower]
    # Also check conjunctions of keywords (e.g. "hair"+"loss" in keywords -> use phrase)
    kw_set = set(keywords)
    phrase_conjunctions = {
        "hair": "loss", "fat": "loss", "anabolic": "steroids",
        "growth": "hormone", "insulin": "resistance", "oxidative": "stress",
        "immune": "system", "stem": "cell", "lean": "mass",
        "body": "composition", "joint": "pain", "muscle": "recovery",
        "wound": "healing", "gut": "health", "blood": "pressure",
        "heart": "disease", "weight": "loss",
    }
    for w1, w2 in phrase_conjunctions.items():
        if w1 in kw_set and w2 in kw_set:
            phrase = f'"{w1} {w2}"'
            if phrase not in phrases_in_query:
                phrases_in_query.append(phrase)

    if phrases_in_query:
        if len(phrases_in_query) >= 2:
            # Combine multiple phrases directly
            queries.append(" AND ".join(phrases_in_query[:3]))
        # Use phrase + keyword combo
        for phrase in phrases_in_query[:2]:
            extra_kw = [k for k in keywords if k not in phrase.strip('"').split()]
            if extra_kw:
                queries.append(f"{phrase} AND {extra_kw[0]}")
            else:
                queries.append(phrase)

    # Try AND with the most specific keywords
    sorted_kw = sorted(set(keywords), key=lambda x: (-len(x), x))
    if len(sorted_kw) >= 3:
        queries.append(" AND ".join(sorted_kw[:3]))
    if len(sorted_kw) >= 2:
        queries.append(" AND ".join(sorted_kw[:2]))
    # Try OR
    if len(sorted_kw) >= 2:
        queries.append(" OR ".join(sorted_kw))
    # Single best keyword
    if sorted_kw:
        queries.append(sorted_kw[0])

    return queries, sorted_kw


def search_pubmed_general(query, retmax=6):
    """Search PubMed broadly for any medical/peptide topic.
    Returns list of {title, pubdate, source, authors, pmid, abstract}."""
    keywords = _extract_medical_keywords(query)
    if not keywords:
        keywords = re.findall(r'[a-z]+', query.lower())

    # Build transformed query from keywords for phrase detection
    transformed_query = " ".join(keywords)
    search_queries, sorted_kw = _build_pubmed_queries(keywords, transformed_query)
    ids = []

    for search_term in search_queries:
        ids = _exec_pubmed_search(search_term, retmax)
        if ids:
            break

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


def _exec_pubmed_search(search_term, retmax):
    """Execute a PubMed search and return ID list."""
    search_url = (
        f"{PUBMED_SEARCH_URL}?db=pubmed&retmode=json&retmax={retmax}"
        f"&sort=relevance&term={urllib.parse.quote(search_term)}"
    )
    search_data = fetch_json(search_url)
    if not search_data:
        return []
    return search_data.get("esearchresult", {}).get("idlist", [])


def search_wikipedia(query, max_results=3):
    """Search Wikipedia for articles matching the query.
    Returns list of {title, summary, link, source}."""
    keywords = _extract_medical_keywords(query)
    if not keywords:
        keywords = re.findall(r'[a-z]+', query.lower())
    search_term = " ".join(keywords[:4])

    params = urllib.parse.urlencode({
        "action": "opensearch",
        "search": search_term,
        "limit": max_results,
        "namespace": 0,
        "format": "json",
    })
    url = f"{WIKIPEDIA_API}?{params}"
    data = fetch_json(url)
    if not data or len(data) < 2:
        return []

    titles = data[1] if len(data) > 1 else []
    links = data[3] if len(data) > 3 else []

    # Also try just the first keyword if no results
    if not titles and keywords:
        params = urllib.parse.urlencode({
            "action": "opensearch",
            "search": keywords[0],
            "limit": max_results,
            "namespace": 0,
            "format": "json",
        })
        url = f"{WIKIPEDIA_API}?{params}"
        data = fetch_json(url)
        if data and len(data) > 1:
            titles = data[1] or titles
            links = data[3] if len(data) > 3 else links

    articles = []
    for i in range(min(len(titles), max_results)):
        title = titles[i]
        link = links[i] if i < len(links) else f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
        # Fetch actual extract (opensearch summaries are often empty)
        extract = fetch_wikipedia_extract(title, max_chars=600)
        articles.append({
            "title": title,
            "summary": extract or "",
            "link": link,
            "source": "Wikipedia",
        })
    return articles


def fetch_wikipedia_extract(title, max_chars=800):
    """Fetch a longer extract from Wikipedia for a given article title."""
    params = urllib.parse.urlencode({
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "exchars": max_chars,
        "titles": title,
        "format": "json",
    })
    url = f"{WIKIPEDIA_API}?{params}"
    data = fetch_json(url)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id != "-1" and page.get("extract"):
            return page["extract"]
    return None


def _parse_pubmed_xml(xml_text, ids):
    """Parse PubMed XML — extract per-PMID article blocks then extract tags from each."""
    # Split XML into per-article blocks by PMID
    article_blocks = {}
    parts = xml_text.split("<PubmedArticle>")
    for part in parts:
        end = part.find("</PubmedArticle>")
        if end == -1:
            continue
        block = part[:end]
        pmid_s = block.find("<PMID")
        if pmid_s == -1:
            continue
        pmid_s = block.find(">", pmid_s) + 1
        pmid_e = block.find("</PMID>", pmid_s)
        if pmid_e == -1:
            continue
        pmid = block[pmid_s:pmid_e].strip()
        article_blocks[pmid] = block

    articles = []
    for pmid in ids:
        block = article_blocks.get(pmid)
        if not block:
            continue
        title = _extract_tag_from_block(block, "ArticleTitle")
        abstract = _extract_abstract_from_block(block)
        pubdate = _extract_tag_from_block(block, "PubDate")
        source = _extract_tag_from_block(block, "Journal")
        if not source:
            source = _extract_tag_from_block(block, "Title")
        authors = _extract_authors_from_block(block)

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


def _extract_tag_from_block(block, tag):
    """Extract first occurrence of <tag> within an article block."""
    start = block.find(f"<{tag}>")
    if start == -1:
        return None
    end = block.find(f"</{tag}>", start)
    if end == -1:
        return None
    return _strip_xml(block[start + len(tag) + 2:end])


def _extract_abstract_from_block(block):
    """Extract abstract text from an article block."""
    start = block.find("<Abstract>")
    if start == -1:
        return None
    end = block.find("</Abstract>", start)
    if end == -1:
        return None
    abstract_xml = block[start:end]
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


def _extract_authors_from_block(block):
    """Extract author names from an article block."""
    authors = []
    pos = 0
    while True:
        a_start = block.find("<Author>", pos)
        if a_start == -1:
            break
        a_end = block.find("</Author>", a_start)
        if a_end == -1:
            break
        author_xml = block[a_start:a_end]
        last = _extract_tag_from_block(author_xml, "LastName")
        first = _extract_tag_from_block(author_xml, "ForeName")
        if last and first:
            authors.append(f"{first} {last}")
        elif last:
            authors.append(last)
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
