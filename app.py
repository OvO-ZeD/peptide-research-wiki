from flask import Flask, render_template, request, jsonify
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
from datetime import datetime, timezone
import os
import re

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

SNAPSHOT_LIBRARY = {
    "tesamorelin": {
        "primary_effect": "Primarily investigated to reduce excess visceral abdominal fat and improve selected metabolic markers in specific clinical populations.",
        "mechanism_pathway": "Mimics growth hormone-releasing hormone signaling and increases endogenous GH with downstream IGF-1 activity, a pathway associated with lipid mobilization and visceral fat metabolism.",
        "expected_body_outcomes": "May reduce central abdominal fat burden and support improvements in metabolic risk signals in studied groups.",
        "clinical_context": "Most established in HIV-associated lipodystrophy studies and related metabolic research settings.",
    },
    "retatrutide": {
        "primary_effect": "Investigated for clinically meaningful body-weight reduction and glycemic improvement in obesity and type 2 diabetes programs.",
        "mechanism_pathway": "Acts as a multi-receptor agonist across glucagon, GLP-1, and GIP pathways, influencing appetite signaling, energy expenditure balance, gastric dynamics, and glucose regulation.",
        "expected_body_outcomes": "Can be associated with reduced calorie intake, improved metabolic control, and substantial fat-mass reduction in responsive trial populations.",
        "clinical_context": "Large interventional programs are ongoing to define long-term efficacy and safety across metabolic phenotypes.",
    },
    "semaglutide": {
        "primary_effect": "Used for glycemic control and weight management depending on indication and formulation.",
        "mechanism_pathway": "GLP-1 receptor agonism supports glucose-dependent insulin signaling, lowers glucagon tone, delays gastric emptying, and enhances satiety signaling.",
        "expected_body_outcomes": "Often linked with improved glucose metrics and progressive weight reduction through appetite and intake modulation.",
        "clinical_context": "Supported by large randomized trial programs in diabetes, obesity, and cardiometabolic outcomes.",
    },
    "tirzepatide": {
        "primary_effect": "Used or investigated for strong glycemic improvement and weight reduction in metabolic disease care.",
        "mechanism_pathway": "Dual GIP and GLP-1 receptor agonism modulates insulin dynamics, satiety pathways, and postprandial metabolic responses.",
        "expected_body_outcomes": "Can lead to significant HbA1c reduction and body-weight decline in eligible patient populations.",
        "clinical_context": "Evidence base includes major phase programs in type 2 diabetes and obesity-related metabolic disease.",
    },
    "bpc-157": {
        "primary_effect": "Discussed mainly in experimental contexts for tissue-repair and inflammation-related hypotheses.",
        "mechanism_pathway": "Proposed pathways are still investigational and not fully established in rigorous human therapeutic frameworks.",
        "expected_body_outcomes": "Potential effects remain uncertain in high-quality human evidence contexts.",
        "clinical_context": "Human interventional evidence is comparatively limited versus approved metabolic therapeutics.",
    },
    "cjc-1295": {
        "primary_effect": "Investigated in growth-hormone-axis research and endocrine signaling contexts.",
        "mechanism_pathway": "Acts as a growth hormone-releasing hormone analog designed to prolong GH-axis stimulation.",
        "expected_body_outcomes": "May increase GH/IGF-1 signaling activity, with downstream effects dependent on dose, population, and treatment context.",
        "clinical_context": "Evidence remains more limited than established approved therapies and requires careful contextual interpretation.",
    },
}

ORDER_CATALOG = [
    {"id": "tesamorelin-5mg", "name": "Tesamorelin", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "retatrutide-10mg", "name": "Retatrutide", "variant": "10mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "semaglutide-5mg", "name": "Semaglutide", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "tirzepatide-10mg", "name": "Tirzepatide", "variant": "10mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "cjc1295-5mg", "name": "CJC-1295", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "bpc157-5mg", "name": "BPC-157", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
]


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


def source_status(wiki, trials, pubmed, fda_data):
    return {
        "wikipedia": bool(wiki and wiki.get("summary")),
        "clinicaltrials": bool(trials),
        "pubmed": bool(pubmed),
        "openfda": bool(fda_data),
    }


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
    endpoint = f"https://clinicaltrials.gov/api/v2/studies?query.term={quote(term)}&pageSize=20"
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
    query = f"({term}[Title/Abstract]) OR ({term}[MeSH Terms]) OR ({term}[All Fields])"
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=12&sort=relevance&term={quote(query)}"
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
                "authors": record.get("authors", []),
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return papers


def parse_year(pubdate):
    if not pubdate:
        return None
    match = re.search(r"(19|20)\d{2}", str(pubdate))
    if not match:
        return None
    return int(match.group(0))


def paper_strength(title, pubdate):
    score = 20
    t = (title or "").lower()
    if any(k in t for k in ["randomized", "double-blind", "placebo", "controlled", "phase 3", "phase iii"]):
        score += 28
    elif any(k in t for k in ["phase 2", "phase ii", "clinical trial"]):
        score += 20
    elif any(k in t for k in ["meta-analysis", "systematic review"]):
        score += 24
    elif any(k in t for k in ["case report", "protocol", "letter"]):
        score -= 8
    year = parse_year(pubdate)
    current_year = datetime.now(timezone.utc).year
    if year:
        age = current_year - year
        if age <= 2:
            score += 18
        elif age <= 5:
            score += 12
        elif age <= 10:
            score += 6
    return max(0, min(100, score))


def rank_pubmed(papers):
    ranked = []
    for paper in papers:
        strength = paper_strength(paper.get("title"), paper.get("pubdate"))
        copy = dict(paper)
        copy["strength"] = strength
        ranked.append(copy)
    ranked.sort(key=lambda p: p.get("strength", 0), reverse=True)
    return ranked


def build_evidence_score(trials, pubmed, fda_data, wiki):
    trial_points = min(45, len(trials) * 4)
    completed_trials = sum(1 for t in trials if (t.get("status") or "") == "COMPLETED")
    trial_points += min(20, completed_trials * 3)
    top_paper = pubmed[0].get("strength", 0) if pubmed else 0
    pubmed_points = min(25, int(top_paper * 0.25))
    fda_points = 10 if fda_data else 0
    wiki_points = 5 if wiki and wiki.get("summary") else 0
    total = min(100, trial_points + pubmed_points + fda_points + wiki_points)
    tier = "HIGH" if total >= 75 else "MEDIUM" if total >= 45 else "LOW"
    return {
        "score": total,
        "tier": tier,
        "breakdown": {
            "trials": trial_points,
            "pubmed": pubmed_points,
            "fda": fda_points,
            "encyclopedia": wiki_points,
        },
    }


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


def build_clinical_snapshot(term, trials, pubmed, fda_data, wiki_summary):
    base = SNAPSHOT_LIBRARY.get(term, {})
    primary_effect = base.get("primary_effect")
    mechanism_pathway = base.get("mechanism_pathway")
    expected_body_outcomes = base.get("expected_body_outcomes")
    clinical_context = base.get("clinical_context")

    if not primary_effect:
        if trials:
            top = trials[0]
            primary_effect = (
                f"Under clinical investigation with human-study signals, including trial {top.get('nct_id', 'N/A')} "
                f"currently listed as {top.get('status', 'Not specified').replace('_', ' ').title()}."
            )
        elif fda_data:
            primary_effect = "Linked to publicly indexed regulatory labeling context, with therapeutic use and safety text available."
        else:
            primary_effect = "Public biomedical sources indicate scientific interest, but high-quality clinical characterization may be limited."

    if not mechanism_pathway:
        if trials:
            methods = trials[0].get("methods", "")
            mechanism_pathway = f"Current mechanism context is inferred from trial design metadata: {methods}"
        else:
            mechanism_pathway = f"Mechanism details are not consistently established in available public records. Context summary: {wiki_summary}"

    if not expected_body_outcomes:
        expected_body_outcomes = "Body-level outcomes depend on indication, patient profile, dosing strategy, and duration of exposure in controlled studies."

    if not clinical_context:
        clinical_context = "Interpretation should be anchored to trial population, study design quality, and regulatory status."

    evidence_points = int(bool(trials)) + int(bool(pubmed)) + int(bool(fda_data))
    evidence_strength = "HIGH" if evidence_points >= 2 else "MODERATE" if evidence_points == 1 else "LIMITED"

    return {
        "primary_effect": primary_effect,
        "mechanism_pathway": mechanism_pathway,
        "expected_body_outcomes": expected_body_outcomes,
        "clinical_context": clinical_context,
        "evidence_strength": evidence_strength,
    }

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route('/catalog')
def catalog():
    return jsonify({"items": ORDER_CATALOG}), 200

@app.route('/search')
def search():
    raw_term = (request.args.get("term") or "").strip()
    if not raw_term:
        return jsonify({"error": "Please enter a peptide name."}), 400

    term = normalize_term(raw_term)
    wiki = fetch_wikipedia_summary(term)
    trials = fetch_clinical_trials(term)
    pubmed = rank_pubmed(fetch_pubmed(term))
    fda_data = fetch_openfda(term)
    medical_definition = build_medical_definition(wiki["title"], trials, fda_data, wiki["summary"])
    plain_summary = build_plain_summary(wiki["summary"], trials)
    benefits, cons = build_benefits_and_cons(trials, fda_data)
    timeline = build_timeline(trials)
    claims = build_evidence_claims(trials, pubmed, fda_data)
    snapshot = build_clinical_snapshot(term, trials, pubmed, fda_data, wiki["summary"])
    evidence_score = build_evidence_score(trials, pubmed, fda_data, wiki)
    source_ok = source_status(wiki, trials, pubmed, fda_data)
    healthy_sources = sum(1 for ok in source_ok.values() if ok)
    reliability = "HIGH" if healthy_sources >= 3 else ("MEDIUM" if healthy_sources >= 2 else "LOW")

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
        "top_pubmed_articles": pubmed[:5],
        "trial_timeline": timeline,
        "evidence_claims": claims,
        "evidence_score": evidence_score,
        "clinical_snapshot": snapshot,
        "source_status": source_ok,
        "reliability": reliability,
        "partial_data": healthy_sources < 4,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {"label": "Wikipedia", "url": wiki["url"]},
            {"label": "ClinicalTrials.gov search", "url": f"https://clinicaltrials.gov/search?term={quote(term)}"},
            {"label": "PubMed search", "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(term)}"},
            {"label": "OpenFDA drug labels", "url": f"https://api.fda.gov/drug/label.json?search={quote(term)}&limit=1"},
        ],
    }
    return jsonify(response)


@app.route('/order-request', methods=['POST'])
def order_request():
    payload = request.get_json(silent=True) or {}
    customer_name = (payload.get("customer_name") or "").strip()
    contact = (payload.get("contact") or "").strip()
    items = payload.get("items") or []
    notes = (payload.get("notes") or "").strip()

    if not customer_name or not contact:
        return jsonify({"error": "Customer name and contact are required."}), 400
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "At least one item is required."}), 400

    catalog_index = {item["id"]: item for item in ORDER_CATALOG}
    normalized_items = []
    total = 0.0

    for row in items:
        item_id = row.get("id")
        qty = int(row.get("qty") or 0)
        if qty <= 0 or item_id not in catalog_index:
            continue
        base = catalog_index[item_id]
        line_total = qty * float(base["price"])
        total += line_total
        normalized_items.append(
            {
                "id": base["id"],
                "name": base["name"],
                "variant": base["variant"],
                "qty": qty,
                "unit_price": base["price"],
                "line_total": round(line_total, 2),
            }
        )

    if len(normalized_items) == 0:
        return jsonify({"error": "No valid order items were submitted."}), 400

    order_record = {
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "customer_name": customer_name,
        "contact": contact,
        "notes": notes,
        "items": normalized_items,
        "total": round(total, 2),
        "currency": "USD",
        "status": "REQUEST_RECEIVED",
    }

    with open("order_requests.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(order_record) + "\n")

    return jsonify({"ok": True, "order": order_record}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
