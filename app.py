from flask import Flask, render_template, request, jsonify
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
from datetime import datetime, timezone
import os

app = Flask(__name__, static_url_path="", static_folder=".")

ALIASES = {
    "reta": "retatrutide",
    "ret": "retatrutide",
    "tesa": "tesamorelin",
    "sema": "semaglutide",
    "tirz": "tirzepatide",
    "bpc": "bpc-157",
    "cjc": "cjc-1295",
}


def normalize_term(term):
    key = term.strip().lower()
    return ALIASES.get(key, key)


def fetch_json(url, headers=None):
    try:
        req = Request(url, headers=headers or {"User-Agent": "peptide-wiki/1.0"})
        with urlopen(req, timeout=18) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_wikipedia_summary(term):
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(term)}"
    data = fetch_json(wiki_url)
    if not data:
        return {
            "title": term,
            "summary": "No encyclopedia summary was found for this peptide.",
            "url": f"https://en.wikipedia.org/wiki/{quote(term)}",
        }
    title = data.get("title") or term
    summary = data.get("extract") or "No summary text was returned."
    wiki_page = data.get("content_urls", {}).get("desktop", {}).get("page")
    if not wiki_page:
        wiki_page = f"https://en.wikipedia.org/wiki/{quote(term)}"
    return {"title": title, "summary": summary, "url": wiki_page}


def fetch_clinical_trials(term):
    endpoint = f"https://clinicaltrials.gov/api/v2/studies?query.term={quote(term)}&pageSize=6"
    data = fetch_json(endpoint)
    if not data:
        return []
    studies = data.get("studies", [])
    results = []
    for study in studies:
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        desc = protocol.get("descriptionModule", {})
        design = protocol.get("designModule", {})
        arms = protocol.get("armsInterventionsModule", {})
        status = protocol.get("statusModule", {})

        nct_id = ident.get("nctId", "N/A")
        title = ident.get("briefTitle") or ident.get("officialTitle") or "Untitled Study"
        brief = desc.get("briefSummary") or "No brief summary available."
        phase_list = design.get("phases", [])
        phase = ", ".join(phase_list) if phase_list else "Not specified"
        model = design.get("designInfo", {}).get("interventionModelDescription") or "Not specified"
        purpose = design.get("designInfo", {}).get("primaryPurpose") or "Not specified"
        allocation = design.get("designInfo", {}).get("allocation") or "Not specified"
        status_text = status.get("overallStatus") or "Not specified"

        interventions = []
        for item in arms.get("interventions", []):
            name = item.get("name")
            int_type = item.get("type")
            if name and int_type:
                interventions.append(f"{int_type}: {name}")
            elif name:
                interventions.append(name)

        methods = (
            f"Phase: {phase}. Primary purpose: {purpose}. Allocation: {allocation}. "
            f"Intervention model: {model}. Interventions: {('; '.join(interventions) if interventions else 'Not listed')}."
        )

        results.append(
            {
                "nct_id": nct_id,
                "title": title,
                "status": status_text,
                "lay_summary": brief,
                "methods": methods,
                "link": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id != "N/A" else "https://clinicaltrials.gov",
            }
        )
    return results


def fetch_pubmed(term):
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=5&term={quote(term)}[Title/Abstract]"
    search_data = fetch_json(search_url)
    if not search_data:
        return []
    ids = search_data.get("esearchresult", {}).get("idlist", [])
    papers = []
    for pmid in ids:
        sum_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id={pmid}"
        sum_data = fetch_json(sum_url)
        if not sum_data:
            continue
        record = sum_data.get("result", {}).get(str(pmid), {})
        if not record:
            continue
        papers.append(
            {
                "pmid": str(pmid),
                "title": record.get("title", "Untitled"),
                "pubdate": record.get("pubdate", "Unknown"),
                "source": record.get("source", "PubMed"),
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return papers


def fetch_openfda(term):
    endpoint = f"https://api.fda.gov/drug/label.json?search={quote(term)}&limit=1"
    data = fetch_json(endpoint)
    if not data:
        return None
    results = data.get("results", [])
    if not results:
        return None
    item = results[0]
    indications = item.get("indications_and_usage", [""])
    warnings = item.get("warnings", [""])
    reactions = item.get("adverse_reactions", [""])
    return {
        "indications": indications[0][:500] if indications and indications[0] else "No FDA indication text available.",
        "warnings": warnings[0][:500] if warnings and warnings[0] else "No FDA warnings text available.",
        "adverse": reactions[0][:500] if reactions and reactions[0] else "No FDA adverse reaction text available.",
    }


def build_medical_definition(name, trials, fda_data, wiki_summary):
    if trials:
        phase = trials[0].get("methods", "")
        return (
            f"{name} is a bioactive peptide under clinical evaluation with evidence from interventional studies. "
            f"Current trial metadata indicates structured therapeutic investigation parameters. {phase}"
        )
    if fda_data:
        return (
            f"{name} is a peptide-associated therapeutic entity with publicly indexed regulatory labeling context. "
            f"Indications include: {fda_data['indications']}"
        )
    return f"{name} is a peptide with publicly indexed biomedical literature. Core context: {wiki_summary}"


def build_plain_summary(wiki_summary, trials):
    if trials:
        first = trials[0]
        return (
            f"In simple terms, this peptide has human studies. One key trial is '{first['title']}' ({first['nct_id']}) "
            f"with status {first['status']}. The study summary says: {first['lay_summary']}"
        )
    return f"In simple terms: {wiki_summary}"


def build_benefits_and_cons(trials, fda_data):
    benefits = []
    cons = []
    if trials:
        statuses = {t.get("status", "") for t in trials}
        if "COMPLETED" in statuses:
            benefits.append("Multiple completed clinical studies suggest meaningful evidence accumulation.")
        benefits.append("Clinical trial programs define dose, intervention model, and treatment objective.")
        cons.append("Some data may still be investigational and not yet definitive for broad real-world use.")
        cons.append("Trial populations can differ from general populations, limiting direct generalization.")
    if fda_data:
        if fda_data.get("indications"):
            benefits.append(f"Regulatory context: {fda_data['indications']}")
        if fda_data.get("warnings"):
            cons.append(f"Safety warnings: {fda_data['warnings']}")
        if fda_data.get("adverse"):
            cons.append(f"Adverse reactions noted in labeling: {fda_data['adverse']}")
    if not benefits:
        benefits.append("Public biomedical sources describe ongoing scientific interest.")
    if not cons:
        cons.append("Risk profile is not fully characterized from currently indexed sources alone.")
    return benefits[:5], cons[:5]


def build_timeline(trials):
    timeline = {"COMPLETED": 0, "RECRUITING": 0, "ACTIVE_NOT_RECRUITING": 0, "OTHER": 0}
    for trial in trials:
        status = trial.get("status", "OTHER")
        if status in timeline:
            timeline[status] += 1
        else:
            timeline["OTHER"] += 1
    return timeline


def build_evidence_claims(trials, pubmed, fda_data):
    claims = []
    if trials:
        top_trial = trials[0]
        claims.append(
            {
                "claim": f"Human interventional evidence exists, including trial {top_trial['nct_id']}.",
                "confidence": "HIGH",
                "source_label": "ClinicalTrials.gov",
                "source_url": top_trial.get("link", "https://clinicaltrials.gov"),
            }
        )
    if pubmed:
        paper = pubmed[0]
        claims.append(
            {
                "claim": "Peer-reviewed biomedical literature is indexed for this peptide.",
                "confidence": "HIGH",
                "source_label": "PubMed",
                "source_url": paper.get("link", "https://pubmed.ncbi.nlm.nih.gov/"),
            }
        )
    if fda_data:
        claims.append(
            {
                "claim": "Regulatory safety or indication text is available in drug labeling sources.",
                "confidence": "HIGH",
                "source_label": "OpenFDA",
                "source_url": "https://open.fda.gov/apis/drug/label/",
            }
        )
    return claims

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"}), 200

@app.route('/search')
def search():
    raw_term = (request.args.get("term") or "").strip()
    if not raw_term:
        return jsonify({"error": "Please enter a peptide name."}), 400

    term = normalize_term(raw_term)
    wiki = fetch_wikipedia_summary(term)
    trials = fetch_clinical_trials(term)
    pubmed = fetch_pubmed(term)
    fda_data = fetch_openfda(term)
    medical_definition = build_medical_definition(wiki["title"], trials, fda_data, wiki["summary"])
    plain_summary = build_plain_summary(wiki["summary"], trials)
    benefits, cons = build_benefits_and_cons(trials, fda_data)
    timeline = build_timeline(trials)
    claims = build_evidence_claims(trials, pubmed, fda_data)

    method_block = trials[0]["methods"] if trials else "No trial method details available."

    response = {
        "search_input": raw_term,
        "normalized_term": term,
        "peptide_name": wiki["title"],
        "medical_definition": medical_definition,
        "plain_summary": plain_summary,
        "research": plain_summary,
        "methods": method_block,
        "benefits": benefits,
        "cons": cons,
        "clinical_trials": trials,
        "pubmed_articles": pubmed,
        "trial_timeline": timeline,
        "evidence_claims": claims,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {"label": "Wikipedia", "url": wiki["url"]},
            {"label": "ClinicalTrials.gov search", "url": f"https://clinicaltrials.gov/search?term={quote(term)}"},
            {"label": "PubMed search", "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(term)}"},
            {"label": "OpenFDA drug labels", "url": f"https://api.fda.gov/drug/label.json?search={quote(term)}&limit=1"},
        ],
    }
    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
