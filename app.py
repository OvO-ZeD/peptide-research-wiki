from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import urllib.request
import urllib.error
import json
import time
from datetime import datetime, timezone
import os
import re
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()
import ask_llm
import primekg
import ckg
import sider_db
import drugbank

app = Flask(__name__, static_url_path="", static_folder=".")

ALIASES = {
    "reta": "retatrutide",
    "ret": "retatrutide",
    "tesa": "tesamorelin",
    "sema": "semaglutide",
    "tirz": "tirzepatide",
    "bpc": "bpc-157",
    "cjc": "cjc-1295",
    "lira": "liraglutide",
    "cagri": "cagrilintide",
    "aod": "aod-9604",
    "mazdu": "mazdutide",
    "survo": "survodutide",
    "ipa": "ipamorelin",
    "mk": "mk-677",
    "mk677": "mk-677",
    "ibutamoren": "mk-677",
    "serm": "sermorelin",
    "hexa": "hexarelin",
    "ghrp2": "ghrp-2",
    "ghrp6": "ghrp-6",
    "tb": "tb-500",
    "thymosin": "thymosin-alpha-1",
    "ta1": "thymosin-alpha-1",
    "ghk": "ghk-cu",
    "mots": "mots-c",
    "ss31": "ss-31",
    "epita": "epitalon",
    "humanin": "humanin",
    "pt141": "pt-141",
    "kiss": "kisspeptin-10",
    "kisspeptin": "kisspeptin-10",
    "igf1-lr3": "igf-1-lr3",
    "lr3": "igf-1-lr3",
    "igf1-des": "igf-1-des",
    "follistatin": "follistatin-344",
    "fs344": "follistatin-344",
    "dsip": "dsip",
    "pinealon": "pinealon",
    "vilon": "vilon",
    "kpv": "kpv",
    "dihexa": "dihexa",
    "selank": "selank",
    "semax": "semax",
    "thymulin": "thymulin",
    "peg-mgf": "peg-mgf",
    "humanin": "humanin",
}

EFFECT_KEYWORDS = {
    "heal": ["recovery", "healing_support", "connective_tissue_support"],
    "healing": ["recovery", "healing_support", "connective_tissue_support"],
    "recover": ["recovery", "healing_support"],
    "recovery": ["recovery", "healing_support"],
    "repair": ["healing_support", "recovery", "connective_tissue_support"],
    "injury": ["recovery", "healing_support", "inflammation_hypothesis"],
    "tissue": ["healing_support", "connective_tissue_support", "recovery"],
    "pain": ["recovery", "inflammation_hypothesis"],
    "inflammation": ["inflammation_hypothesis"],
    "chronic": ["inflammation_hypothesis", "stress_response"],
    "fat": ["fat_loss", "visceral_fat", "fat_loss_support", "metabolic_flexibility"],
    "weight": ["fat_loss", "appetite_modulation", "visceral_fat", "metabolic_flexibility"],
    "lose": ["fat_loss", "appetite_modulation"],
    "belly": ["visceral_fat"],
    "visceral": ["visceral_fat"],
    "metabolism": ["metabolic_flexibility", "gh_axis", "fat_loss_support"],
    "metabolic": ["metabolic_flexibility", "glycemic_support", "fat_loss"],
    "glucose": ["glycemic_support"],
    "sugar": ["glycemic_support", "appetite_modulation"],
    "sleep": ["sleep_support", "stress_response"],
    "insomnia": ["sleep_support"],
    "focus": ["focus"],
    "brain": ["focus", "stress_response"],
    "memory": ["focus"],
    "cognitive": ["focus"],
    "mental": ["focus", "stress_response"],
    "anxiety": ["anxiety_support", "calm", "stress_response"],
    "stress": ["stress_response", "calm", "anxiety_support"],
    "calm": ["calm", "anxiety_support"],
    "mood": ["calm", "anxiety_support", "stress_response"],
    "relax": ["calm", "anxiety_support", "sleep_support"],
    "muscle": ["lean_mass_support", "recovery", "gh_axis"],
    "lean": ["lean_mass_support", "body_composition"],
    "strength": ["lean_mass_support", "gh_axis"],
    "endurance": ["exercise_tolerance", "mitochondrial_support"],
    "stamina": ["exercise_tolerance", "mitochondrial_support"],
    "energy": ["mitochondrial_support", "exercise_tolerance", "metabolic_flexibility"],
    "fatigue": ["mitochondrial_support", "recovery", "sleep_support"],
    "workout": ["recovery", "lean_mass_support", "exercise_tolerance"],
    "aging": ["mitochondrial_support", "skin_quality", "gh_axis", "body_composition"],
    "longevity": ["mitochondrial_support"],
    "skin": ["skin_quality", "healing_support"],
    "immune": ["thymic_support", "recovery"],
    "immunity": ["thymic_support", "recovery"],
    "gut": ["recovery", "healing_support", "inflammation_hypothesis"],
    "libido": ["sexual_function"],
    "arousal": ["sexual_function"],
    "growth": ["gh_axis", "igf_signaling"],
    "hormone": ["gh_axis", "body_composition"],
    "appetite": ["appetite_modulation"],
    "wellness": ["metabolic_flexibility", "mitochondrial_support", "recovery"],
    "anti": ["mitochondrial_support", "skin_quality", "gh_axis"],
    "collagen": ["skin_quality", "healing_support"],
}

EFFECT_LABELS = {
    "fat_loss": "Fat Loss",
    "glycemic_support": "Glycemic Control",
    "appetite_modulation": "Appetite Regulation",
    "visceral_fat": "Visceral Fat Reduction",
    "gh_axis": "GH Axis Support",
    "body_composition": "Body Composition",
    "recovery": "Recovery Support",
    "lean_mass_support": "Lean Mass Preservation",
    "metabolic_flexibility": "Metabolic Flexibility",
    "exercise_tolerance": "Exercise Tolerance",
    "fat_loss_support": "Fat Loss Support",
    "focus": "Focus & Cognition",
    "stress_response": "Stress Response",
    "calm": "Calm",
    "anxiety_support": "Anxiety Support",
    "inflammation_hypothesis": "Inflammation Modulation",
    "skin_quality": "Skin Quality",
    "healing_support": "Healing Support",
    "connective_tissue_support": "Connective Tissue Support",
    "sleep_support": "Sleep Support",
    "mitochondrial_support": "Mitochondrial Support",
    "sexual_function": "Sexual Function",
    "igf_signaling": "IGF-1 Signaling",
    "myostatin_inhibition": "Myostatin Inhibition",
    "thymic_support": "Thymic / Immune Support",
    "tanning_support": "Tanning Support",
    "uv_response": "UV Response",
    "ghrelin_axis": "Ghrelin Axis",
    "healing": "Healing Support",
    "cooling": "Thermoregulation",
}

SNAPSHOT_LIBRARY = {
    "tesamorelin": {
        "primary_effect": "Tesamorelin is mainly studied to help reduce stubborn belly fat (visceral fat) that sits deep around your internal organs. It is not for general weight loss — it targets the unhealthy fat that wraps around your liver and intestines.",
        "mechanism_pathway": "Think of tesamorelin as a nudge to your brain's pituitary gland. It mimics a natural hormone called GHRH that tells your body to release more growth hormone. Higher growth hormone then signals your body to break down stored fat for energy, especially the deep belly fat.",
        "expected_body_outcomes": "People who take tesamorelin in studies often lose inches around their waist from the inside out (visceral fat). It may also improve some metabolic blood markers. Effects take weeks to months and work best alongside healthy lifestyle habits.",
        "clinical_context": "Tesamorelin is FDA-approved for reducing visceral fat in people with HIV-related lipodystrophy (a condition where fat shifts to the belly). Outside of that specific group, it is used off-label based on the same fat-burning mechanism, but the strongest evidence comes from HIV studies.",
    },
    "retatrutide": {
        "primary_effect": "Retatrutide is being studied as a powerful weight-loss and blood-sugar-lowering medication. Early results suggest it may cause more weight loss than older similar drugs, making it a next-generation metabolic treatment.",
        "mechanism_pathway": "Retatrutide is like a three-key activator. It turns on three different body signals at once: glucagon (tells your liver to release stored energy), GLP-1 (tells your brain you are full and slows stomach emptying), and GIP (helps your body handle sugar better). This triple action is what makes it potentially stronger than two-key drugs.",
        "expected_body_outcomes": "In studies, people taking retatrutide lose significant body weight — often more than with single or dual hormone mimickers. Blood sugar levels improve, appetite drops noticeably, and fat burning increases. Nausea is a common side effect, especially when starting.",
        "clinical_context": "Retatrutide is still in clinical trials (not yet FDA approved for general use). It is being tested in large Phase 2 and Phase 3 programs for obesity and type 2 diabetes. Since it is not yet publicly available, access is currently through clinical trials only.",
    },
    "semaglutide": {
        "primary_effect": "Semaglutide is used to lower blood sugar in type 2 diabetes and to help with weight loss. It is one of the most well-studied peptides in its class and is available as a prescription medication under brand names like Ozempic, Wegovy, and Rybelsus.",
        "mechanism_pathway": "Semaglutide mimics a natural hormone called GLP-1 that your gut releases when you eat. It works in three main ways: it tells your pancreas to release more insulin when blood sugar is high, it tells your liver to stop making extra sugar, and it signals your brain that you are full so you eat less.",
        "expected_body_outcomes": "Most people experience noticeably reduced appetite and eat smaller portions. Blood sugar levels improve within weeks. Weight loss is gradual but steady — often 10-15% of body weight over months. Some people feel nauseous at first, which usually improves over time.",
        "clinical_context": "Semaglutide is FDA approved and widely prescribed. Ozempic is for type 2 diabetes, Wegovy is for weight management, and Rybelsus is an oral tablet form. It has been studied in large trials with thousands of participants, giving it one of the strongest evidence bases among metabolic peptides.",
    },
    "tirzepatide": {
        "primary_effect": "Tirzepatide is used for type 2 diabetes and weight management. It is often described as stronger than semaglutide for weight loss because it targets two hormones instead of one, leading to greater appetite suppression and better blood sugar control.",
        "mechanism_pathway": "Tirzepatide activates two gut hormone receptors at once: GIP and GLP-1. Think of it as turning on two different dials. The GLP-1 part slows digestion and tells your brain you are full. The GIP part improves how your body uses sugar and may add extra fat-burning effects that single-target drugs do not have.",
        "expected_body_outcomes": "Users typically experience reduced hunger, earlier fullness when eating, and fewer food cravings. Weight loss is often substantial — many people lose 15-25% of their body weight in clinical trials. Blood sugar and HbA1c levels improve significantly. Like similar drugs, nausea and digestive issues are possible when starting.",
        "clinical_context": "Tirzepatide is FDA approved as Mounjaro for type 2 diabetes and Zepbound for weight management. It is currently one of the most effective available options for weight loss based on clinical trial results. It is a prescription medication available through healthcare providers.",
    },
    "bpc-157": {
        "primary_effect": "BPC-157 is discussed mainly in experimental and bodybuilding communities for its potential to speed up healing of injuries — tendons, ligaments, muscles, and gut lining. It is not FDA approved and has not been tested in large human trials.",
        "mechanism_pathway": "BPC-157 is thought to help the body repair itself by promoting blood vessel growth (angiogenesis) to injured areas, increasing collagen production (the building block of tendons and connective tissue), and reducing inflammation. It also activates growth hormone receptors in healing tissues. However, these effects have mostly been shown in animal and lab studies, not in large human trials.",
        "expected_body_outcomes": "Anecdotal reports from users describe faster recovery from joint and tendon injuries, reduced pain, and improved gut health. However, because high-quality human studies are missing, it is hard to predict what will happen in any specific person. Effects likely vary and expectations should be cautious.",
        "clinical_context": "BPC-157 is not approved by any major regulatory agency (FDA, EMA) for medical use. It is sold as a research chemical, not a medication. There is much less human safety data compared to approved metabolic peptides. Anyone considering it should understand that long-term safety is unknown.",
    },
    "cjc-1295": {
        "primary_effect": "CJC-1295 is studied for its ability to raise growth hormone and IGF-1 levels in the body. It is commonly discussed in anti-aging and bodybuilding circles for its potential to improve body composition, recovery, and vitality.",
        "mechanism_pathway": "CJC-1295 is a synthetic version of GHRH (growth hormone releasing hormone). It binds to the pituitary gland and stimulates it to release more growth hormone in natural pulses. Unlike natural GHRH which breaks down quickly, CJC-1295 has been modified to last much longer in the body through a technology called Drug Affinity Complex (DAC).",
        "expected_body_outcomes": "Users may experience improved sleep quality, faster recovery from exercise, and changes in body composition (more lean mass, less fat). These effects come from increased growth hormone signaling. Results develop gradually over weeks to months. Side effects may include water retention, joint pain, and numbness/tingling in hands.",
        "clinical_context": "CJC-1295 has been studied in small human trials for growth hormone deficiency but is not FDA approved for general use. It is classified as a research chemical and is not a prescription medication. The evidence base is much smaller than for approved peptides like semaglutide or tirzepatide.",
    },
    "ipamorelin": {
        "primary_effect": "Ipamorelin is a growth hormone secretagogue — meaning it triggers the body to release its own growth hormone. It is popular in anti-aging and fitness contexts for supporting recovery, lean muscle, and fat loss.",
        "mechanism_pathway": "Ipamorelin mimics ghrelin, the hunger hormone, but in a selective way. It binds to ghrelin receptors in the pituitary gland, which causes a pulse of growth hormone release. Unlike natural ghrelin, it does not strongly stimulate appetite, making it attractive for body composition goals without increased hunger.",
        "expected_body_outcomes": "Users commonly report better sleep quality, faster recovery between workouts, improved skin elasticity, and gradual fat loss. Effects are subtle compared to prescribed hormones — think of it as giving your natural growth hormone production a gentle nudge rather than a flood. Results accumulate over months of consistent use.",
        "clinical_context": "Ipamorelin has been studied for conditions like postoperative recovery and frailty in older adults, but it is not FDA approved for general use. It is widely available as a research peptide. Its safety profile for long-term, non-medical use is not well established.",
    },
    "mots-c": {
        "primary_effect": "MOTS-c is a mitochondrial peptide — it works inside your cells' energy factories (mitochondria) to regulate metabolism. It is investigated for improving metabolic flexibility (the ability to switch between burning sugar and fat for fuel).",
        "mechanism_pathway": "MOTS-c is unique because it is encoded in mitochondrial DNA, not nuclear DNA. It acts like a cellular signal that tells your body to become more efficient at using energy. It activates AMPK (a master metabolic switch) and helps skeletal muscles take up glucose more effectively, mimicking some effects of exercise at the cellular level.",
        "expected_body_outcomes": "Potential effects include better endurance, improved insulin sensitivity, and increased fat oxidation (burning fat for energy). In animal studies, it prevented age-related weight gain and improved exercise capacity. Human evidence is very early-stage, so real-world effects are less well understood.",
        "clinical_context": "MOTS-c is an early-stage research peptide with limited human studies. It was discovered relatively recently (2015). Most evidence comes from animal and cell studies. It is sold as a research chemical and has not been evaluated by the FDA for any medical use.",
    },
    "epitalon": {
        "primary_effect": "Epitalon is a synthetic peptide researched for its potential effects on aging and circadian rhythm regulation. It is thought to influence the pineal gland and restore youthful patterns of melatonin secretion.",
        "mechanism_pathway": "Epitalon (also called epithalon or Epithalamin) is made of four amino acids. It is believed to activate the telomerase enzyme, which helps maintain the protective caps (telomeres) at the ends of chromosomes. Longer telomeres are associated with slower cellular aging. It also influences the pineal gland to produce more regular nightly melatonin pulses, which helps regulate sleep-wake cycles.",
        "expected_body_outcomes": "Users and animal studies suggest improved sleep quality, more regular circadian rhythms, and potential anti-aging effects at the cellular level. Some research in older adults showed improved immune function and better daily activity rhythms. Effects are subtle and take months to develop.",
        "clinical_context": "Epitalon was developed by Russian scientists and has been studied primarily in animal models and small human trials in Russia and Ukraine. It is not FDA approved and is sold as a research chemical. The human evidence base is small compared to mainstream medications.",
    },
    "ghk-cu": {
        "primary_effect": "GHK-Cu (copper peptide) is a naturally occurring small peptide that binds copper ions. It is widely studied for skin regeneration, wound healing, and hair growth support through improved scalp angiogenesis and reduced inflammation.",
        "mechanism_pathway": "GHK-Cu is a tripeptide (glycine-histidine-lysine) with a copper ion. It signals skin and hair follicle cells to produce more collagen and elastin, reduces inflammation via NF-kB inhibition, acts as an antioxidant, and promotes angiogenesis (new blood vessel growth) which improves nutrient delivery to hair follicles. The copper ion is essential — it activates enzymes needed for collagen crosslinking and SOD antioxidant activity.",
        "expected_body_outcomes": "Topical application may improve skin firmness, reduce fine lines, and support wound healing. For hair: studies suggest improved hair follicle density, reduced shedding, and thicker hair shafts with consistent topical use over 3-6 months. Injectable forms are discussed for systemic tissue repair, though injection use has less formal study than topical.",
        "clinical_context": "GHK-Cu is widely used in cosmetic products (topical serums for anti-aging and hair thinning). PubMed-indexed studies show wound healing and collagen synthesis effects. Hair growth studies are primarily cosmetic-industry funded. Not FDA approved as a drug — classified as a cosmetic ingredient. Injectable forms are research chemicals with limited long-term safety data.",
    },
    "liraglutide": {
        "primary_effect": "Liraglutide helps lower blood sugar and supports weight loss. It is a well-established medication for type 2 diabetes (Victoza) and weight management (Saxenda), with over a decade of clinical use.",
        "mechanism_pathway": "Liraglutide mimics the natural hormone GLP-1, which your gut releases when you eat. It tells your pancreas to release more insulin when sugar is high, slows down stomach emptying so you feel full longer, and signals your brain to reduce appetite. A fatty acid chain attached to the molecule keeps it active in the body for a full day.",
        "expected_body_outcomes": "People usually eat less and feel full sooner after meals. Blood sugar levels drop steadily, and weight loss of 5-10% is typical over several months. Some people experience nausea when starting, which often fades. It is injected once daily.",
        "clinical_context": "Liraglutide is FDA approved and has been prescribed since 2010 for diabetes and since 2014 for weight management. It has been studied in large, long-term trials including cardiovascular outcome studies. It is available by prescription only.",
    },
    "sermorelin": {
        "primary_effect": "Sermorelin stimulates the pituitary gland to release more growth hormone. It is used medically to diagnose and treat growth hormone deficiency in children.",
        "mechanism_pathway": "Sermorelin is a synthetic fragment of GHRH (growth hormone releasing hormone). It binds to receptors on the pituitary gland and triggers natural pulsatile release of growth hormone. Unlike synthetic GH injections which replace the hormone directly, sermorelin stimulates the body's own production, preserving the natural feedback loop.",
        "expected_body_outcomes": "In children with growth deficiency, sermorelin can increase growth rate. In adults used off-label, it may improve body composition, energy, and recovery. Effects are gradual and require consistent use over months.",
        "clinical_context": "Sermorelin is FDA approved for pediatric growth hormone deficiency. It is used off-label in anti-aging clinics for its GH-releasing effects. Requires daily subcutaneous injections and is available by prescription.",
    },
    "mk-677": {
        "primary_effect": "MK-677 (ibutamoren) is an oral growth hormone secretagogue — a pill that stimulates the body to release more growth hormone and IGF-1.",
        "mechanism_pathway": "MK-677 mimics ghrelin, the hunger hormone, by binding to the ghrelin receptor (GHSR). This triggers the pituitary to release pulses of growth hormone. Unlike injectable GH-releasing peptides, MK-677 is orally bioavailable — a pill. It also increases appetite as a side effect of ghrelin receptor activation.",
        "expected_body_outcomes": "Users typically see IGF-1 levels comparable to mild GH therapy. Increased appetite is common, especially in the first weeks. Some report better sleep quality, improved recovery, and modest lean mass gains over months. Effects vary significantly between individuals.",
        "clinical_context": "MK-677 has been studied in human trials for frailty in the elderly, hip fracture recovery, and GH deficiency. It is not FDA approved and is sold as a research chemical. Long-term safety data beyond 12 months is limited.",
    },
    "hexarelin": {
        "primary_effect": "Hexarelin is a potent GH-releasing peptide that triggers strong pulses of growth hormone. It is one of the strongest GH secretagogues in its class.",
        "mechanism_pathway": "Hexarelin binds strongly to the ghrelin receptor (GHSR-1a) on the pituitary gland, triggering a rapid, large pulse of GH release — more potent than GHRP-2 or ipamorelin. Some research also suggests GH-independent effects on cardiovascular tissue through CD36 receptors.",
        "expected_body_outcomes": "A strong GH pulse within minutes. Potential benefits include improved recovery, fat metabolism, and lean mass. The GH spike is typically larger and shorter than from other GHRPs. This potency means desensitization (reduced response over time) may occur faster.",
        "clinical_context": "Hexarelin has been studied in human trials but is not FDA approved. It is known for its potency — the strongest GH spike of common secretagogues. Sold as a research chemical.",
    },
    "ghrp-6": {
        "primary_effect": "GHRP-6 stimulates growth hormone release and is notable for also significantly increasing appetite — useful when both GH support and hunger stimulation are desired.",
        "mechanism_pathway": "GHRP-6 binds to the ghrelin receptor (GHSR) in the pituitary and hypothalamus. This triggers GH release and also activates neuropeptide Y neurons, which strongly stimulate appetite. The hunger effect is much stronger than with GHRP-2 or ipamorelin.",
        "expected_body_outcomes": "GH pulse within 15-30 minutes. Noticeably increased appetite within minutes, lasting 30-60 minutes. Improved recovery and sleep quality with regular use.",
        "clinical_context": "GHRP-6 is not FDA approved. It is one of the older GHRPs with the strongest hunger effect. Sold as a research chemical, typically injected subcutaneously.",
    },
    "ghrp-2": {
        "primary_effect": "GHRP-2 stimulates growth hormone release with less appetite activation than GHRP-6. Commonly stacked with GHRH analogs (like CJC-1295) for a synergistic GH pulse.",
        "mechanism_pathway": "GHRP-2 binds to the ghrelin receptor (GHSR) and triggers GH release. Compared to GHRP-6, it has less effect on appetite pathways. It works synergistically with GHRH analogs — using both produces a larger GH pulse than either alone.",
        "expected_body_outcomes": "GH pulse within 15-30 minutes, milder than hexarelin but more consistent for daily use. Less appetite stimulation than GHRP-6. Better recovery and body composition when used consistently over months.",
        "clinical_context": "GHRP-2 is not FDA approved. One of the most commonly used GHRPs in research. Often stacked with a GHRH analog. Sold as a research chemical.",
    },
    "tb-500": {
        "primary_effect": "TB-500 (Thymosin Beta-4) is studied for accelerating healing of injuries — especially tendons, ligaments, and muscles.",
        "mechanism_pathway": "TB-500 is a synthetic version of Thymosin Beta-4, a protein found in all human cells. It binds to actin and promotes cell migration to injury sites, increases blood vessel growth (angiogenesis), reduces inflammation, and stimulates release of healing factors.",
        "expected_body_outcomes": "Anecdotal reports describe faster recovery from soft tissue injuries, reduced scar tissue, and improved flexibility in injured areas. Effects may take days to weeks.",
        "clinical_context": "TB-500 is not FDA approved. Studied mainly in preclinical contexts. Sold as a research chemical.",
    },
    "pt-141": {
        "primary_effect": "PT-141 (bremelanotide) is studied for sexual arousal and desire. Unlike Viagra, it works on the brain rather than blood flow.",
        "mechanism_pathway": "PT-141 activates melanocortin receptors (MC3R and MC4R) in the central nervous system, triggering increased sexual desire independently of sex hormones. Unlike PDE5 inhibitors (Viagra/Cialis), it acts on the brain's desire pathways.",
        "expected_body_outcomes": "Increased sexual desire and arousal within 30-60 minutes, lasting 6-12 hours. Spontaneous yawning is a known side effect. Nausea can occur at higher doses.",
        "clinical_context": "PT-141 (bremelanotide) is FDA approved as Vyleesi for hypoactive sexual desire disorder in premenopausal women. Studied off-label in men for ED. Self-injected subcutaneously.",
    },
    "thymosin-alpha-1": {
        "primary_effect": "Thymosin Alpha-1 helps regulate the immune system. Studied for immune support, infection response, and as an adjunct in vaccine therapy.",
        "mechanism_pathway": "Produced by the thymus gland, it acts as a biological response modifier. Activates T-cells, natural killer cells, and dendritic cells. Modulates cytokine production — helping dial the immune system to the right level.",
        "expected_body_outcomes": "Improved immune function, particularly in immunocompromised populations. Studied to reduce infections and improve vaccine responses in older adults.",
        "clinical_context": "Approved as a medication in several countries (China, Russia, parts of Europe) for immune support and hepatitis. Not FDA approved in the US. Sold as a research chemical.",
    },
    "igf-1-lr3": {
        "primary_effect": "IGF-1 LR3 is a synthetic long-acting version of insulin-like growth factor 1. Studied for potent anabolic and metabolic effects.",
        "mechanism_pathway": "Binds to IGF-1 receptors on nearly all cell types, promoting protein synthesis, inhibiting protein breakdown, and supporting cell growth. The LR3 modification prevents binding to IGF-binding proteins, keeping it active much longer than natural IGF-1.",
        "expected_body_outcomes": "Increased lean muscle mass, improved recovery, better glucose uptake in muscles, and improved skin quality with consistent use.",
        "clinical_context": "IGF-1 LR3 is not FDA approved. Sold as a research chemical. The LR3 variant is a research tool designed for longer half-life. Human safety data is limited.",
    },
    "aod-9604": {
        "primary_effect": "AOD-9604 is a fragment of human growth hormone studied for fat loss. Designed to stimulate fat breakdown without affecting blood sugar or growth.",
        "mechanism_pathway": "A 16-amino-acid fragment of the fat-burning region of GH. Activates lipolysis (fat breakdown) without binding to GH receptors that affect blood sugar and cell growth.",
        "expected_body_outcomes": "Proposed accelerated fat loss, particularly from stubborn areas. Human studies are limited and results mixed. Effects would likely be modest alongside diet and exercise.",
        "clinical_context": "Completed Phase 2 trials for obesity but development was not continued to approval. Sold as a research chemical.",
    },
    "semax": {
        "primary_effect": "Semax is a synthetic peptide used for cognitive enhancement — improving focus, memory, and mental stamina.",
        "mechanism_pathway": "Increases levels of BDNF (brain-derived neurotrophic factor), supporting neural growth and survival. Also modulates dopamine, serotonin, and acetylcholine — neurotransmitters involved in attention, mood, and memory.",
        "expected_body_outcomes": "Improved focus, mental clarity, better memory recall, reduced brain fog within hours. Some users report improved mood. Used both acutely and long-term.",
        "clinical_context": "Approved as a prescription medication in Russia for stroke recovery and cognitive impairment. Not FDA approved in the US. Administered as nasal drops.",
    },
    "selank": {
        "primary_effect": "Selank is a synthetic peptide studied for reducing anxiety without sedation or cognitive dulling.",
        "mechanism_pathway": "Increases enkephalin and serotonin levels in the brain, promoting calmness. Does not act on GABA receptors like benzodiazepines, so it is less likely to cause sedation or memory issues.",
        "expected_body_outcomes": "Calm, clear-headed state without drowsiness. Reduced anxiety and better stress handling. Often described as making things 'bother you less' rather than a strong drug effect.",
        "clinical_context": "Approved as a prescription medication in Russia for anxiety disorders. Not FDA approved in the US. Administered as nasal drops.",
    },
    "dsip": {
        "primary_effect": "DSIP (Delta Sleep-Inducing Peptide) promotes deep, restorative sleep and reduces stress.",
        "mechanism_pathway": "Promotes delta wave activity — the deepest stage of sleep. Also influences the stress axis (HPA axis) by modulating cortisol and ACTH. Not a sedative — it shifts sleep architecture toward more deep sleep.",
        "expected_body_outcomes": "Improved sleep quality, deeper and more restorative sleep. Better stress resilience. Effects may take days to develop.",
        "clinical_context": "Studied in small human trials for sleep disorders. Not FDA approved. Sold as a research chemical. Research history dating back to the 1970s.",
    },
    "ss-31": {
        "primary_effect": "SS-31 (elamipretide) targets mitochondria to improve cellular energy production and exercise tolerance.",
        "mechanism_pathway": "A small tetrapeptide that targets the inner mitochondrial membrane. Interacts with cardiolipin to optimize energy production and reduce reactive oxygen species. Helps cells' energy factories work better.",
        "expected_body_outcomes": "Improved exercise tolerance, faster recovery, better energy levels. In clinical studies, improved walking distance in mitochondrial disease patients.",
        "clinical_context": "Studied in human trials for mitochondrial disease and heart failure. Received FDA Orphan Drug designation. Not yet FDA approved. More clinical data exists than for most research peptides.",
    },
    "humanin": {
        "primary_effect": "Humanin is a naturally occurring mitochondrial peptide with proposed protective effects against aging and cellular stress.",
        "mechanism_pathway": "Encoded by mitochondrial DNA, acts as a cellular stress signal. Reduces oxidative stress, inhibits cell death, and improves insulin sensitivity. Levels naturally decline with age.",
        "expected_body_outcomes": "Proposed metabolic health and inflammation benefits. Most evidence from animal and cell studies. Human research is very early stage.",
        "clinical_context": "Discovered in 2001. Studied in animal models of Alzheimer's, heart disease, and metabolic disorders. Not approved by any regulatory agency.",
    },
    "cagrilintide": {
        "primary_effect": "Cagrilintide is an investigational peptide that mimics amylin, a hormone regulating appetite and blood sugar. Being developed for weight loss, often with semaglutide.",
        "mechanism_pathway": "A long-acting analog of amylin, a hormone released by the pancreas after meals. Slows gastric emptying, promotes satiety signals, and suppresses glucagon. Works through a different mechanism than GLP-1 drugs.",
        "expected_body_outcomes": "Reduced appetite, slower digestion, earlier fullness, weight loss. In trials, combination with semaglutide (CagriSema) produced greater weight loss than either alone.",
        "clinical_context": "Developed by Novo Nordisk, completed Phase 2 trials. Not yet FDA approved. Being studied in combination with semaglutide for obesity.",
    },
}

REGULATORY_STATUS = {
    "tesamorelin": "fda_approved",
    "retatrutide": "investigational",
    "semaglutide": "fda_approved",
    "tirzepatide": "fda_approved",
    "bpc-157": "research_chemical",
    "cjc-1295": "research_chemical",
    "ipamorelin": "research_chemical",
    "mots-c": "research_chemical",
    "epitalon": "research_chemical",
    "ghk-cu": "research_chemical",
    "liraglutide": "fda_approved",
    "sermorelin": "fda_approved",
    "mk-677": "research_chemical",
    "hexarelin": "research_chemical",
    "ghrp-6": "research_chemical",
    "ghrp-2": "research_chemical",
    "tb-500": "research_chemical",
    "pt-141": "fda_approved",
    "thymosin-alpha-1": "research_chemical",
    "igf-1-lr3": "research_chemical",
    "aod-9604": "investigational",
    "semax": "research_chemical",
    "selank": "research_chemical",
    "dsip": "research_chemical",
    "ss-31": "investigational",
    "humanin": "research_chemical",
    "cagrilintide": "investigational",
    "mazdutide": "investigational",
    "survodutide": "investigational",
    "melanotan-2": "research_chemical",
    "peg-mgf": "research_chemical",
    "thymulin": "research_chemical",
    "dihexa": "research_chemical",
    "follistatin-344": "research_chemical",
    "pinealon": "research_chemical",
    "vilon": "research_chemical",
    "kpv": "research_chemical",
    "igf-1-des": "research_chemical",
    "kisspeptin-10": "research_chemical",
}

ORDER_CATALOG = [
    {"id": "tesamorelin-5mg", "name": "Tesamorelin", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "retatrutide-10mg", "name": "Retatrutide", "variant": "10mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "semaglutide-5mg", "name": "Semaglutide", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "tirzepatide-10mg", "name": "Tirzepatide", "variant": "10mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "cjc1295-5mg", "name": "CJC-1295", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "bpc157-5mg", "name": "BPC-157", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
]

INTERACTION_MATRIX = {
    ("bpc-157", "tb-500"): {
        "type": "synergistic",
        "note": "Commonly stacked for healing; both promote angiogenesis and tissue repair.",
        "evidence": "Anecdotal community reports, limited formal study.",
    },
    ("ghk-cu", "bpc-157"): {
        "type": "synergistic",
        "note": "Both support tissue repair through different mechanisms.",
        "evidence": "Theoretical synergy based on complementary mechanisms.",
    },
    ("ghk-cu", "tb-500"): {
        "type": "synergistic",
        "note": "Collagen synthesis + angiogenesis for comprehensive tissue repair.",
        "evidence": "Anecdotal community reports.",
    },
    ("cjc-1295", "ipamorelin"): {
        "type": "synergistic",
        "note": "Standard GHRH + GHRP stack for synergistic GH pulse.",
        "evidence": "Well-documented in research peptide community.",
    },
    ("cjc-1295", "ghrp-2"): {
        "type": "synergistic",
        "note": "GHRH + GHRP stack with stronger GH pulse.",
        "evidence": "Common research protocol.",
    },
    ("cjc-1295", "ghrp-6"): {
        "type": "synergistic",
        "note": "GHRH + GHRP stack with appetite increase from GHRP-6.",
        "evidence": "Common research protocol.",
    },
    ("tesamorelin", "ipamorelin"): {
        "type": "synergistic",
        "note": "GHRH + GHRP produces synergistic GH pulse larger than either alone.",
        "evidence": "Clinical data supports tesamorelin alone; combo is standard practice.",
    },
    ("semaglutide", "tirzepatide"): {
        "type": "contraindicated",
        "note": "Both are incretin mimetics. Stacking increases side effect risk with no benefit.",
        "evidence": "Clinical guidelines recommend monotherapy only.",
    },
    ("semaglutide", "retatrutide"): {
        "type": "contraindicated",
        "note": "Overlapping metabolic pathways. Retatrutide already includes GLP-1 agonism.",
        "evidence": "Theoretical contraindication based on overlapping mechanisms.",
    },
    ("semaglutide", "ghrp-6"): {
        "type": "caution",
        "note": "Opposing appetite signals may reduce efficacy of either.",
        "evidence": "Theoretical, based on opposing mechanisms.",
    },
    ("semax", "selank"): {
        "type": "synergistic",
        "note": "Focus + calm pairing. Semax enhances cognition, Selank reduces anxiety.",
        "evidence": "Anecdotal community reports.",
    },
    ("dsip", "selank"): {
        "type": "synergistic",
        "note": "DSIP for deep sleep, Selank for anxiety reduction.",
        "evidence": "Anecdotal, based on compatible mechanisms.",
    },
    ("melanotan-2", "ghk-cu"): {
        "type": "synergistic",
        "note": "Skin quality pairing: melanotan-2 for pigmentation, GHK-Cu for collagen.",
        "evidence": "Anecdotal community reports.",
    },
    ("ss-31", "mots-c"): {
        "type": "synergistic",
        "note": "Both target mitochondria through different pathways.",
        "evidence": "Theoretical synergy based on complementary mechanisms.",
    },
    ("thymosin-alpha-1", "ghk-cu"): {
        "type": "synergistic",
        "note": "Immune support + tissue repair for comprehensive recovery.",
        "evidence": "Anecdotal, based on compatible mechanisms.",
    },
    ("semaglutide", "cagrilintide"): {
        "type": "synergistic",
        "note": "CagriSema — under active clinical investigation for weight loss.",
        "evidence": "Phase 2 trials show greater weight loss than either alone.",
    },
}

DOSAGE_REFERENCE = {
    "retatrutide": {"typical_dose": "1-12 mg weekly (titrated)", "route": "SubQ injection", "half_life": "~6 days", "notes": "Titrate over weeks. Starting 1-2 mg. Still in trials.", "max_safe": "12 mg/week"},
    "tesamorelin": {"typical_dose": "1-2 mg daily", "route": "SubQ injection", "half_life": "~30 min", "notes": "Evening, empty stomach. 5 on, 2 off cycling.", "max_safe": "2 mg/day"},
    "semaglutide": {"typical_dose": "0.25-2.4 mg weekly (titrated)", "route": "SubQ injection", "half_life": "~7 days", "notes": "Start 0.25 mg/wk x4. Wegovy max 2.4 mg, Ozempic max 1.0 mg.", "max_safe": "2.4 mg/week"},
    "tirzepatide": {"typical_dose": "2.5-15 mg weekly (titrated)", "route": "SubQ injection", "half_life": "~5 days", "notes": "Start 2.5 mg x4 wk, +2.5 mg every 4 wk.", "max_safe": "15 mg/week"},
    "liraglutide": {"typical_dose": "0.6-3.0 mg daily (titrated)", "route": "SubQ injection", "half_life": "~13 hours", "notes": "Victoza max 1.8 mg. Saxenda max 3.0 mg.", "max_safe": "3.0 mg/day"},
    "cagrilintide": {"typical_dose": "0.3-2.4 mg weekly", "route": "SubQ injection", "half_life": "~8 days", "notes": "Investigational. Dosing in trials.", "max_safe": "2.4 mg/week"},
    "sermorelin": {"typical_dose": "0.5-2.0 mg daily", "route": "SubQ injection", "half_life": "~15 min", "notes": "Evening, empty stomach.", "max_safe": "2 mg/day"},
    "ipamorelin": {"typical_dose": "200-300 mcg daily", "route": "SubQ injection", "half_life": "~2 hours", "notes": "Evening. Can combine with GHRH in same syringe.", "max_safe": "300 mcg/day"},
    "cjc-1295": {"typical_dose": "1-2 mg 2x/week (DAC) or 100 mcg daily", "route": "SubQ injection", "half_life": "~6-8 days (DAC)", "notes": "DAC 2x/week. Non-DAC daily.", "max_safe": "2 mg 2x/week"},
    "ghrp-2": {"typical_dose": "100-200 mcg 2-3x daily", "route": "SubQ injection", "half_life": "~30 min", "notes": "Stronger GH pulse than ipamorelin.", "max_safe": "200 mcg/dose"},
    "ghrp-6": {"typical_dose": "100-200 mcg 2-3x daily", "route": "SubQ injection", "half_life": "~30 min", "notes": "Strong appetite effect.", "max_safe": "200 mcg/dose"},
    "hexarelin": {"typical_dose": "100-200 mcg daily", "route": "SubQ injection", "half_life": "~30 min", "notes": "Most potent GHRP, fastest desensitization.", "max_safe": "200 mcg/day"},
    "mk-677": {"typical_dose": "10-25 mg daily", "route": "Oral", "half_life": "~24 hours", "notes": "Oral. Before bed. Monitor glucose.", "max_safe": "25 mg/day"},
    "bpc-157": {"typical_dose": "200-500 mcg daily", "route": "SubQ injection or oral", "half_life": "~4 hours", "notes": "Local or systemic injection. Oral for gut.", "max_safe": "500 mcg/day"},
    "tb-500": {"typical_dose": "2.5-5 mg 2x/week (loading)", "route": "SubQ injection", "half_life": "~4-6 hours", "notes": "Loading 2-4 weeks.", "max_safe": "10 mg/week"},
    "ghk-cu": {"typical_dose": "1-5 mg daily or topical", "route": "SubQ injection or topical", "half_life": "~3 hours", "notes": "Cycle to avoid copper buildup.", "max_safe": "5 mg/day"},
    "aod-9604": {"typical_dose": "300-600 mcg daily", "route": "SubQ injection", "half_life": "~1 hour", "notes": "Empty stomach. Mixed trial results.", "max_safe": "600 mcg/day"},
    "semax": {"typical_dose": "400-1200 mcg daily", "route": "Intranasal", "half_life": "~20 min", "notes": "Intranasal drops/spray. Effects 4-6 hr.", "max_safe": "1200 mcg/day"},
    "selank": {"typical_dose": "400-900 mcg daily", "route": "Intranasal", "half_life": "~20 min", "notes": "Calming within 15-30 min. Up to 3x daily.", "max_safe": "900 mcg/day"},
    "dsip": {"typical_dose": "100-400 mcg daily", "route": "SubQ or intranasal", "half_life": "~30 min", "notes": "Before bed. Effects may take days.", "max_safe": "400 mcg/day"},
    "ss-31": {"typical_dose": "10-40 mg daily", "route": "SubQ injection", "half_life": "~2 hours", "notes": "Investigational. Mitochondrial support.", "max_safe": "40 mg/day"},
    "mots-c": {"typical_dose": "10-20 mg daily or EOD", "route": "SubQ injection", "half_life": "~1 hour", "notes": "Early-stage. Cycle 5 on, 2 off.", "max_safe": "20 mg/day"},
    "pt-141": {"typical_dose": "0.75-1.75 mg as needed", "route": "SubQ injection", "half_life": "~2 hours", "notes": "Max 1 injection per 24 hr. Nausea common.", "max_safe": "1.75 mg/24hr"},
    "thymosin-alpha-1": {"typical_dose": "1.5-6 mg twice weekly", "route": "SubQ injection", "half_life": "~2 hours", "notes": "2x/week dosing.", "max_safe": "6 mg 2x/week"},
    "igf-1-lr3": {"typical_dose": "20-60 mcg daily or post-workout", "route": "SubQ injection", "half_life": "~20-30 hours", "notes": "Long half-life. Risk of hypoglycemia.", "max_safe": "60 mcg/day"},
    "melanotan-2": {"typical_dose": "0.25-1.0 mg daily or EOD", "route": "SubQ injection", "half_life": "~36 hours", "notes": "Start 0.25 mg. Nausea common.", "max_safe": "1 mg/day"},
}

SAFETY_NOTES = {
    "general": {
        "title": "General Safety Considerations",
        "points": [
            "Peptides discussed on this site are for educational research purposes only.",
            "Always consult a qualified healthcare provider before starting any peptide protocol.",
            "Research chemical peptides are not regulated — purity, sterility, and accurate dosing are not guaranteed.",
            "Start with the lowest effective dose and titrate slowly.",
        ],
    },
    "bpc-157": {
        "title": "BPC-157 Safety",
        "points": [
            "No long-term human safety data available.",
            "Theoretical concern: angiogenesis could promote cancer cell growth.",
            "Research-grade vials may not be sterile — filter before injection.",
            "Not FDA approved for any medical use.",
        ],
    },
    "semaglutide": {
        "title": "Semaglutide Safety",
        "points": [
            "Prescription medication — use only under medical supervision.",
            "Common: nausea, vomiting, diarrhea, constipation.",
            "Risk of gallbladder disease, pancreatitis, thyroid C-cell tumors.",
            "Do not use with family history of medullary thyroid carcinoma.",
        ],
    },
    "tirzepatide": {
        "title": "Tirzepatide Safety",
        "points": [
            "Prescription medication — medical supervision required.",
            "Black box warning for thyroid C-cell tumors in rodents.",
            "Do not combine with other GLP-1 or GIP receptor agonists.",
        ],
    },
    "retatrutide": {
        "title": "Retatrutide Safety",
        "points": [
            "Investigational — only available through clinical trials.",
            "Heart rate increase observed in some participants.",
            "Long-term safety beyond 12 months not established.",
        ],
    },
    "gh-secretagogues": {
        "title": "GH Secretagogue Safety (GHRPs + GHRHs)",
        "points": [
            "Not FDA approved — all are research chemicals.",
            "Long-term GH/IGF-1 elevation may accelerate aging processes.",
            "Potential pituitary desensitization — cycle on/off required.",
            "MK-677 can cause insulin resistance — monitor glucose.",
        ],
    },
    "melanotan-2": {
        "title": "Melanotan-2 Safety",
        "points": [
            "Not FDA approved — research chemical.",
            "Nausea very common at higher doses.",
            "May darken existing moles — monitor for changes.",
            "Long-term skin cancer risk not adequately studied.",
        ],
    },
    "ghk-cu": {
        "title": "GHK-Cu Safety",
        "points": [
            "Topical use is well-studied in cosmetics.",
            "Injectable form is a research chemical.",
            "Copper accumulation with prolonged high-dose use.",
        ],
    },
    "pt-141": {
        "title": "PT-141 (Bremelanotide) Safety",
        "points": [
            "FDA approved as Vyleesi for HSDD.",
            "Nausea in ~40% of users, flushing, headache.",
            "May increase blood pressure — avoid if uncontrolled hypertension.",
        ],
    },
}


STACK_KNOWLEDGE = {
    "retatrutide": {
        "effects": ["fat_loss", "glycemic_support", "appetite_modulation"],
        "tier": "A",
        "summary": "Multi-receptor incretin agonist with strong obesity and metabolic trial signals.",
    },
    "tesamorelin": {
        "effects": ["visceral_fat", "gh_axis", "body_composition"],
        "tier": "A",
        "summary": "GHRH analog with established data in visceral fat-focused populations.",
    },
    "ipamorelin": {
        "effects": ["gh_axis", "recovery", "lean_mass_support"],
        "tier": "C",
        "summary": "GH-axis support signal is mostly mechanistic and smaller-study weighted.",
    },
    "mots-c": {
        "effects": ["metabolic_flexibility", "exercise_tolerance", "fat_loss_support"],
        "tier": "C",
        "summary": "Early-stage metabolic signaling peptide with limited human evidence depth.",
    },
    "semaglutide": {
        "effects": ["fat_loss", "glycemic_support", "appetite_modulation"],
        "tier": "A",
        "summary": "GLP-1 agonist with extensive high-quality obesity and diabetes evidence.",
    },
    "tirzepatide": {
        "effects": ["fat_loss", "glycemic_support", "appetite_modulation"],
        "tier": "A",
        "summary": "Dual GIP/GLP-1 agonist with strong outcomes in weight and glycemic endpoints.",
    },
    "cjc-1295": {
        "effects": ["gh_axis", "recovery", "lean_mass_support"],
        "tier": "C",
        "summary": "Long-acting GHRH analog context with limited high-quality human outcomes.",
    },
    "bpc-157": {
        "effects": ["recovery", "inflammation_hypothesis"],
        "tier": "D",
        "summary": "Evidence is mostly preclinical or anecdotal and should be treated as uncertain.",
    },
    "semax": {
        "effects": ["focus", "stress_response"],
        "tier": "C",
        "summary": "Neurocognitive-related signals are present but broad clinical evidence is limited.",
    },
    "selank": {
        "effects": ["calm", "anxiety_support", "focus"],
        "tier": "C",
        "summary": "Anxiolytic/focus hypotheses exist with limited large-trial evidence depth.",
    },
    "melanotan-2": {
        "effects": ["tanning_support", "uv_response"],
        "tier": "D",
        "summary": "Primarily discussed in aesthetic tanning contexts with limited controlled human evidence depth.",
    },
    "ghk-cu": {
        "effects": ["skin_quality", "recovery", "healing_support"],
        "tier": "C",
        "summary": "Skin and repair related signals are mostly early-stage or mixed-evidence in human settings.",
    },
    "tb-500": {
        "effects": ["recovery", "healing_support", "connective_tissue_support"],
        "tier": "D",
        "summary": "Often discussed for repair/recovery protocols, but controlled human evidence remains limited.",
    },
    "aod-9604": {
        "effects": ["fat_loss_support", "metabolic_flexibility"],
        "tier": "C",
        "summary": "Fat-metabolism focused peptide with narrower and less mature human evidence than incretin agents.",
    },
    "dsip": {
        "effects": ["sleep_support", "stress_response"],
        "tier": "D",
        "summary": "Sleep-focused discussions are common, though high-quality contemporary clinical evidence is limited.",
    },
    "ss-31": {
        "effects": ["mitochondrial_support", "exercise_tolerance", "recovery"],
        "tier": "C",
        "summary": "Mitochondrial-targeted candidate with translational potential and evolving human evidence.",
    },
    "liraglutide": {
        "effects": ["fat_loss", "glycemic_support", "appetite_modulation"],
        "tier": "A",
        "summary": "GLP-1 agonist with long clinical track record in type 2 diabetes and weight management.",
    },
    "cagrilintide": {
        "effects": ["fat_loss", "appetite_modulation"],
        "tier": "C",
        "summary": "Amylin analog under investigation as adjunct to GLP-1 agonists for enhanced weight loss.",
    },
    "mazdutide": {
        "effects": ["fat_loss", "glycemic_support", "appetite_modulation"],
        "tier": "C",
        "summary": "Dual GLP-1/glucagon receptor agonist in clinical development for metabolic disease.",
    },
    "survodutide": {
        "effects": ["fat_loss", "appetite_modulation"],
        "tier": "C",
        "summary": "Dual GLP-1/glucagon agonist with emerging Phase 2 data in obesity and MASH.",
    },
    "mk-677": {
        "effects": ["gh_axis", "recovery", "lean_mass_support"],
        "tier": "C",
        "summary": "Oral ghrelin mimetic that stimulates GH release; studied in frailty and recovery contexts.",
    },
    "sermorelin": {
        "effects": ["gh_axis", "body_composition"],
        "tier": "B",
        "summary": "Synthetic GHRH analog FDA-approved for growth hormone deficiency diagnosis and treatment.",
    },
    "hexarelin": {
        "effects": ["gh_axis", "recovery"],
        "tier": "C",
        "summary": "GH-releasing peptide with potent GH pulse stimulation; limited long-term human safety data.",
    },
    "ghrp-2": {
        "effects": ["gh_axis", "recovery", "lean_mass_support"],
        "tier": "C",
        "summary": "Synthetic ghrelin mimetic that strongly stimulates GH release; commonly stacked with GHRH analogs.",
    },
    "ghrp-6": {
        "effects": ["gh_axis", "recovery", "appetite_modulation"],
        "tier": "C",
        "summary": "GH secretagogue with notable appetite-stimulating effect in addition to GH pulse signaling.",
    },
    "peg-mgf": {
        "effects": ["recovery", "lean_mass_support"],
        "tier": "D",
        "summary": "PEGylated mechano-growth factor with proposed localized repair signaling; evidence mostly preclinical.",
    },
    "humanin": {
        "effects": ["mitochondrial_support", "metabolic_flexibility"],
        "tier": "D",
        "summary": "Mitochondrial-derived peptide with proposed cytoprotective and metabolic signaling roles.",
    },
    "thymosin-alpha-1": {
        "effects": ["thymic_support", "recovery"],
        "tier": "C",
        "summary": "Thymic peptide with immunomodulatory properties studied in immune function and infection contexts.",
    },
    "thymulin": {
        "effects": ["thymic_support"],
        "tier": "D",
        "summary": "Thymic hormone peptide with proposed immune-regulatory effects; limited human trial data.",
    },
    "dihexa": {
        "effects": ["focus"],
        "tier": "D",
        "summary": "Angiotensin IV analog with proposed cognitive enhancement signals; minimal human data.",
    },
    "pt-141": {
        "effects": ["sexual_function"],
        "tier": "C",
        "summary": "Melanocortin receptor agonist studied for sexual arousal and desire; intranasal route.",
    },
    "kisspeptin-10": {
        "effects": ["sexual_function", "gh_axis"],
        "tier": "C",
        "summary": "Kisspeptin receptor agonist involved in reproductive hormone signaling and GH pulse modulation.",
    },
    "igf-1-lr3": {
        "effects": ["igf_signaling", "lean_mass_support"],
        "tier": "C",
        "summary": "Long-acting IGF-1 analog with potent anabolic signaling; limited controlled human data.",
    },
    "igf-1-des": {
        "effects": ["igf_signaling"],
        "tier": "D",
        "summary": "Truncated IGF-1 variant with high receptor affinity; mostly discussed in research contexts.",
    },
    "follistatin-344": {
        "effects": ["myostatin_inhibition", "lean_mass_support"],
        "tier": "D",
        "summary": "Follistatin isoform that binds myostatin; preclinical muscle-growth signals without human trial confirmation.",
    },
    "pinealon": {
        "effects": ["sleep_support", "recovery"],
        "tier": "D",
        "summary": "Synthetic pineal peptide proposed for circadian support; very limited human evidence.",
    },
    "vilon": {
        "effects": ["thymic_support"],
        "tier": "D",
        "summary": "Short dipeptide with proposed immune-support effects; primarily discussed in Eastern European research.",
    },
    "kpv": {
        "effects": ["inflammation_hypothesis", "healing_support"],
        "tier": "D",
        "summary": "Short peptide fragment of alpha-melanocyte stimulating hormone with proposed anti-inflammatory signaling.",
    },
}

STACK_PROTOCOLS = {
    "tesamorelin+ipamorelin": {
        "name": "Tesamorelin + Ipamorelin",
        "goal": "Fat loss with muscle preservation",
        "cycle_weeks": 16,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-6",
                "protocol": "Tesamorelin 2mg subQ daily (evening preferred, empty stomach). Ipamorelin not yet introduced — allow tesamorelin to establish GH-axis priming.",
                "dosing_details": "Tesamorelin 2mg — reconstitute with 1mL bacteriostatic water, draw to 10-unit mark on insulin syringe. Inject subcutaneously in abdomen, 2 inches from belly button. Rotate sites.",
                "timing": "Evening, just before bed or at least 2 hours after last meal (to avoid glucose interference with GH pulse).",
            },
            {
                "phase": 2,
                "weeks": "7-16",
                "protocol": "Tesamorelin 2mg subQ daily + Ipamorelin 200-300mcg subQ daily. Administer both in same syringe (tested and found compatible). Continue evening dosing on empty stomach.",
                "dosing_details": "Draw 0.5mL (2mg tesamorelin) + 0.2mL (200mcg ipamorelin) into same insulin syringe for single injection. Total volume ~0.7mL. Rotate injection sites across abdomen.",
                "timing": "Same evening window, empty stomach (no food 2h before, 15min after).",
            },
        ],
        "post_cycle": "4 weeks off completely to reset receptor sensitivity and allow natural GH axis to normalize. No GH secretagogues during off-period.",
        "sources": [
            "Clinical trials show tesamorelin 2mg daily reduces visceral fat by ~15-20% over 26 weeks in HIV populations.",
            "Ipamorelin 200-300mcg produces reliable GH pulse with minimal cortisol or prolactin elevation.",
            "Combination GHRH+GHRP produces synergistic GH pulse — 2-3x larger than either alone.",
        ],
        "evidence_summary": "Tesamorelin has Phase 3 data for visceral fat reduction. Ipamorelin has Phase 1/2 data for GH pulse stimulation. The combination is common in research protocols but lacks dedicated randomized controlled trials as a fixed combination.",
    },
    "retatrutide": {
        "name": "Retatrutide (Monotherapy)",
        "goal": "Weight loss, glycemic control",
        "cycle_weeks": 48,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Retatrutide 2mg subQ once weekly. Dose escalation phase — low starting dose to assess tolerance.",
                "dosing_details": "Inject subcutaneously once weekly. Rotate sites (abdomen, thigh, upper arm).",
                "timing": "Same day each week, any time of day. Can be taken with or without food.",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Retatrutide 4mg subQ once weekly. Step-up dose per trial protocols.",
                "dosing_details": "Double the dose. Continue weekly subQ injection.",
                "timing": "Same weekly schedule.",
            },
            {
                "phase": 3,
                "weeks": "9-48",
                "protocol": "Retatrutide 6-8mg (or max tolerated dose) subQ once weekly. Maintenance phase. Dose adjustments based on tolerance and response.",
                "dosing_details": "Titrate up to 8mg weekly as tolerated. Most clinical data uses 4-8mg range.",
                "timing": "Same weekly schedule.",
            },
        ],
        "post_cycle": "No required off-cycle — retatrutide is designed for continuous use. If discontinuing, taper dose over 2-4 weeks to minimize appetite rebound.",
        "sources": [
            "Phase 2 trial: 24-week retatrutide produced up to 17.1% weight loss at 8mg dose.",
            "Triple agonism (GLP-1/GIP/glucagon) distinguishes it from dual-agonist tirzepatide.",
        ],
        "evidence_summary": "Retatrutide is in Phase 3 trials with strong Phase 2 data showing superior weight loss to existing incretin therapies. Not yet FDA approved.",
    },
    "retatrutide+tesamorelin+ipamorelin": {
        "name": "Retatrutide + Tesamorelin + Ipamorelin",
        "goal": "Maximum fat loss with muscle preservation",
        "cycle_weeks": 16,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Retatrutide 2mg weekly + Tesamorelin 2mg daily. Start with incretin + GHRH to establish metabolic and GH-axis priming before adding GHRP.",
                "dosing_details": "Retatrutide weekly subQ. Tesamorelin 2mg subQ daily in evening. Separate injection sites.",
                "timing": "Retatrutide any time. Tesamorelin evening empty stomach.",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Retatrutide 4mg weekly + Tesamorelin 2mg daily + Ipamorelin 200mcg daily. Introduce GHRP after GHRH is established for synergistic GH pulse.",
                "dosing_details": "Tesamorelin + Ipamorelin can be mixed in same syringe. Retatrutide in separate injection.",
                "timing": "Tesamorelin+Ipamorelin together in evening empty stomach. Retatrutide on separate day.",
            },
            {
                "phase": 3,
                "weeks": "9-16",
                "protocol": "Retatrutide 6-8mg weekly + Tesamorelin 2mg daily + Ipamorelin 200-300mcg daily. Full dose triple protocol.",
                "dosing_details": "Maintain all three. Monitor appetite, glucose, and tolerance closely.",
                "timing": "Same timing as phase 2.",
            },
        ],
        "post_cycle": "4 weeks off GH-axis peptides (tesamorelin, ipamorelin). Retatrutide can continue as maintenance if desired.",
        "sources": [
            "Triple agonist Phase 2 data shows significant weight loss.",
            "GHRH+GHRP synergy established in GH literature.",
        ],
        "evidence_summary": "This is an advanced research protocol combining FDA-reviewed and investigational peptides. Each component has evidence individually; the triple combination lacks dedicated trials.",
    },
    "semaglutide+tirzepatide": {
        "name": "Semaglutide + Tirzepatide",
        "goal": "Weight loss",
        "cycle_weeks": 0,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "All",
                "protocol": "Medical guidance: These are FDA-approved medications. Do NOT combine without physician supervision. Choose one agent and follow prescribed titration. Semaglutide start 0.25mg weekly, titrate to 2.4mg (Wegovy). Tirzepatide start 2.5mg weekly, titrate to 15mg (Zepbound).",
                "dosing_details": "Follow approved prescribing information. Do not stack GLP-1/GIP agonists together unless under clinical trial conditions.",
                "timing": "Once weekly injection per prescribing guidelines.",
            },
        ],
        "post_cycle": "Taper off over 4 weeks to minimize appetite rebound and blood sugar fluctuations.",
        "sources": ["FDA prescribing information for Ozempic/Wegovy and Mounjaro/Zepbound."],
        "evidence_summary": "Both have extensive FDA-reviewed trial data. Combining them lacks safety data and is not recommended outside clinical trials.",
    },
    "cjc1295+ghrp2": {
        "name": "CJC-1295 + GHRP-2",
        "goal": "GH pulse amplification, recovery, body composition",
        "cycle_weeks": 12,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-12",
                "protocol": "CJC-1295 (without DAC) 100mcg subQ + GHRP-2 200mcg subQ, 2-3x daily. Classic GHRH+GHRP synergy protocol. Morning and evening dosing captures natural GH pulse windows.",
                "dosing_details": "Mix in same syringe. Morning dose upon waking (empty stomach, wait 20min before eating). Evening dose before bed (2h after last meal).",
                "timing": "2x daily: upon waking + before bed. Optional 3rd dose pre-workout.",
            },
        ],
        "post_cycle": "4 weeks off. Monitor for GH-axis desensitization with prolonged use.",
        "sources": [
            "GHRH+GHRP synergy established in Johnston et al. 2000 and subsequent GH research.",
            "CJC-1295 with DAC studied in Phase 1 trials for GH deficiency.",
        ],
        "evidence_summary": "Well-characterized GH pulse synergy mechanism. Individual components studied in human trials. Long-term safety of repeated pulsing less established.",
    },
    "bpc157+tb500": {
        "name": "BPC-157 + TB-500",
        "goal": "Injury recovery, tendon/ligament healing",
        "cycle_weeks": 6,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-2",
                "protocol": "BPC-157 250mcg 2x daily (morning/evening) subQ near injury site + TB-500 2.5mg 2x weekly subQ. Loading phase for faster onset.",
                "dosing_details": "BPC-157: dose near injury site if accessible. TB-500: systemic, can inject abdomen or thigh.",
                "timing": "BPC-157 morning + evening. TB-500 every 3-4 days.",
            },
            {
                "phase": 2,
                "weeks": "3-6",
                "protocol": "BPC-157 250mcg 1x daily (maintenance) + TB-500 2.5mg 1x weekly. Reduce frequency once healing response established.",
                "dosing_details": "Continue as above at reduced frequency.",
                "timing": "BPC-157 daily evening. TB-500 once weekly.",
            },
        ],
        "post_cycle": "2 weeks off minimum. Can repeat after 2-week break if needed.",
        "sources": [
            "BPC-157: preclinical studies show accelerated tendon/ligament healing in rat models.",
            "TB-500: preclinical studies show increased angiogenesis and cell migration.",
        ],
        "evidence_summary": "Both have strong preclinical evidence but limited human trial data. Most evidence is from animal studies and anecdotal reports.",
    },
    "mk677+ipamorelin": {
        "name": "MK-677 + Ipamorelin",
        "goal": "GH-axis support, recovery, lean mass",
        "cycle_weeks": 12,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-12",
                "protocol": "MK-677 10-25mg orally once daily (evening) + Ipamorelin 200-300mcg subQ daily (evening). Oral+injectable GH secretagogue combination for sustained GH pulse elevation.",
                "dosing_details": "MK-677: oral capsule/tablet, take before bed. Ipamorelin: subQ injection in abdomen evening empty stomach.",
                "timing": "Both in evening window. MK-677 before bed (may cause hunger — sleep through it). Ipamorelin 2h after last meal.",
            },
        ],
        "post_cycle": "4 weeks off. MK-677 may cause insulin sensitivity changes — monitor glucose during cycle and off-period.",
        "sources": [
            "MK-677: human trials show increased IGF-1 in elderly and hip fracture patients.",
            "Ipamorelin: Phase 1/2 data for post-op recovery.",
        ],
        "evidence_summary": "MK-677 has human trial data but is not FDA approved. Combination lacks controlled trials. Monitor glucose closely — MK-677 can reduce insulin sensitivity.",
    },
    "semax+selank": {
        "name": "Semax + Selank",
        "goal": "Focus, calm, cognitive performance",
        "cycle_weeks": 4,
        "off_weeks": 1,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Semax 400-800mcg intranasal daily (morning) + Selank 400-800mcg intranasal daily (morning or split AM/PM). Administer separately, 5-10 minutes apart.",
                "dosing_details": "Standard nasal dropper or spray. Lean head back slightly, administer, hold position for 30 seconds. Avoid blowing nose for 10 minutes.",
                "timing": "Semax in the morning for cognitive activation. Selank morning or split AM+PM for all-day calm.",
            },
        ],
        "post_cycle": "1 week off. Can cycle on as needed. Some users run 8 weeks with 2 weeks off.",
        "sources": [
            "Semax: approved in Russia for stroke recovery. Studies show increased BDNF.",
            "Selank: approved in Russia for anxiety disorders. Modulates serotonin and enkephalin.",
        ],
        "evidence_summary": "Both have regional regulatory approval (Russia) and human studies. US FDA approval not obtained. Intranasal bioavailability well established.",
    },
    "pt141": {
        "name": "PT-141 (Bremelanotide)",
        "goal": "Sexual arousal and desire",
        "cycle_weeks": 0,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "PRN",
                "protocol": "PT-141 0.75-1.75mg subQ as needed. Onset ~30-60 minutes, effects last 6-12 hours. Start at lowest dose to assess tolerance and nausea response.",
                "dosing_details": "Inject subcutaneously in abdomen. Nausea is dose-dependent — starting at 0.75mg reduces this risk.",
                "timing": "As needed, 30-60 minutes before desired effect. Do not exceed 2 doses per 24 hours. Max 8 doses per month per FDA labeling.",
            },
        ],
        "post_cycle": "No cycling required — used as needed per FDA guidelines. Monitor for blood pressure changes.",
        "sources": [
            "FDA approved as Vyleesi for hypoactive sexual desire disorder in premenopausal women.",
            "Clinical trials show improved desire scores vs placebo.",
        ],
        "evidence_summary": "FDA approved with clinical trial data. Better studied in women than men. Used off-label in men for ED and desire enhancement.",
    },
    "ss31+mots-c": {
        "name": "SS-31 (Elamipretide) + MOTS-c",
        "goal": "Mitochondrial support, endurance, metabolic flexibility",
        "cycle_weeks": 8,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-8",
                "protocol": "SS-31 20-40mg subQ daily (evening) + MOTS-c 5-10mg subQ 2-3x weekly. Mitochondrial-targeted stack for cellular energy optimization.",
                "dosing_details": "SS-31: daily subQ injection. MOTS-c: subQ injection every other day. Separate injection sites.",
                "timing": "SS-31 in evening. MOTS-c morning or pre-workout.",
            },
        ],
        "post_cycle": "2 weeks off. Mitochondrial adaptation requires cycling to maintain sensitivity.",
        "sources": [
            "SS-31: FDA Orphan Drug designation for mitochondrial disease. Multiple human trials.",
            "MOTS-c: discovered 2015. Animal studies show improved metabolic parameters. Limited human data.",
        ],
        "evidence_summary": "SS-31 has the strongest evidence among mitochondrial peptides with FDA Orphan status and human trials. MOTS-c is much earlier stage.",
    },
    "ghk-cu": {
        "name": "GHK-Cu (Copper Peptide)",
        "goal": "Skin health, wound healing, anti-aging",
        "cycle_weeks": 8,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-8",
                "protocol": "GHK-Cu 1-5mg subQ daily (systemic) or topical 2x daily. For systemic effects (collagen, hair, tissue repair): 2-5mg daily subQ. For cosmetic/skin: topical 1-2x daily.",
                "dosing_details": "SubQ: standard injection in abdomen. Topical: apply to clean skin after cleansing.",
                "timing": "SubQ: evening. Topical: morning and evening.",
            },
        ],
        "post_cycle": "2 weeks off. Can cycle on/off 8 weeks on, 2 weeks off.",
        "sources": [
            "Well-studied in wound healing literature. Multiple clinical studies for topical use.",
            "GHK-Cu naturally decreases with age — supplementation restores youthful levels.",
        ],
        "evidence_summary": "GHK-Cu has strong evidence for topical wound healing and skin health. Injectable systemic use has less formal study but is common in research protocols.",
    },
    "aod9604+mk677": {
        "name": "AOD-9604 + MK-677",
        "goal": "Fat loss support",
        "cycle_weeks": 12,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-12",
                "protocol": "AOD-9604 300-500mcg subQ 1-2x daily (morning + pre-bed) + MK-677 10-25mg orally daily (evening). AOD targets lipolysis directly while MK-677 supports GH-mediated metabolic effects.",
                "dosing_details": "AOD-9604: subQ injection. MK-677: oral capsule. Can take concurrently in evening window.",
                "timing": "AOD split dose: morning + evening. MK-677 with evening dose or before bed.",
            },
        ],
        "post_cycle": "4 weeks off. Monitor appetite normalization during off-period.",
        "sources": [
            "AOD-9604: completed Phase 2 obesity trials. Modest fat loss effect.",
            "MK-677: increases IGF-1, may support metabolic rate.",
        ],
        "evidence_summary": "Both have limited human data. AOD-9604 Phase 2 data showed modest fat loss but development was discontinued. Combination lacks trials.",
    },
    "thymosin-alpha1+ghk-cu": {
        "name": "Thymosin Alpha-1 + GHK-Cu",
        "goal": "Immune support + tissue repair",
        "cycle_weeks": 6,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-6",
                "protocol": "Thymosin Alpha-1 750-1500mcg subQ 1-2x weekly + GHK-Cu 2-5mg subQ daily. Immune modulation + systemic repair protocol.",
                "dosing_details": "Thymosin Alpha-1: inject subQ, fewer injections per week (long-acting effect). GHK-Cu: daily subQ. Separate sites.",
                "timing": "Thymosin Alpha-1: morning (may cause mild warmth/flush — normal). GHK-Cu: evening.",
            },
        ],
        "post_cycle": "2 weeks off. Immune peptides are typically cycled 6-8 weeks on, 2-4 weeks off.",
        "sources": [
            "Thymosin Alpha-1: approved in several countries for immune support. Multiple human studies in hepatitis and vaccine response.",
            "GHK-Cu: wound healing literature. Systemic effects less studied.",
        ],
        "evidence_summary": "Thymosin Alpha-1 has human clinical data in immune contexts (hepatitis, vaccine response). GHK-Cu adds repair support. Combination is extrapolated from individual evidence.",
    },
    "selank+dsip": {
        "name": "Selank + DSIP",
        "goal": "Sleep quality, stress reduction, calm",
        "cycle_weeks": 4,
        "off_weeks": 1,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Selank 400-800mcg intranasal daily (morning/afternoon) + DSIP 50-100mcg subQ daily (evening). Selank for daytime calm, DSIP for deep sleep architecture.",
                "dosing_details": "Selank: intranasal spray. DSIP: subQ injection in abdomen evening. DSIP is light-sensitive — protect from light during reconstitution and storage.",
                "timing": "Selank morning + afternoon as needed. DSIP 30-60 minutes before bed.",
            },
        ],
        "post_cycle": "1 week off. Can repeat 4-week cycles as needed.",
        "sources": [
            "DSIP: discovered 1970s, studied in small human sleep trials.",
            "Selank: approved in Russia for anxiety. Modulates serotonin without sedation.",
        ],
        "evidence_summary": "Both have modest human data. DSIP research is older (1970s-90s). Selank has more recent clinical data from Russian research programs.",
    },
    "retatrutide+tesamorelin": {
        "name": "Retatrutide + Tesamorelin",
        "goal": "Weight loss with visceral fat targeting",
        "cycle_weeks": 24,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Retatrutide 2mg subQ once weekly + Tesamorelin 2mg subQ daily. Incretin priming phase — low retatrutide dose to assess tolerance before escalation.",
                "dosing_details": "Retatrutide weekly subQ injection. Tesamorelin daily subQ in evening. Separate injection sites — minimum 2 inches apart.",
                "timing": "Retatrutide same day weekly (any time). Tesamorelin evening empty stomach (2h+ after last meal).",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Retatrutide 4mg subQ weekly + Tesamorelin 2mg daily. Mid-dose escalation. Monitor appetite, nausea, and injection site tolerance.",
                "dosing_details": "Double retatrutide dose. Continue tesamorelin at 2mg daily. Both subQ.",
                "timing": "Same timing windows as phase 1.",
            },
            {
                "phase": 3,
                "weeks": "9-24",
                "protocol": "Retatrutide 6-8mg subQ weekly + Tesamorelin 2mg daily. Full maintenance dose. Dual mechanism — triple agonist incretin + GHRH-driven fat loss.",
                "dosing_details": "Retatrutide at max tolerated dose (6-8mg) weekly. Tesamorelin 2mg daily.",
                "timing": "Same timing windows.",
            },
        ],
        "post_cycle": "Retatrutide can continue as maintenance if desired. If discontinuing, taper retatrutide over 2-4 weeks to minimize appetite rebound. Tesamorelin can be stopped without taper.",
        "sources": [
            "Retatrutide Phase 2: up to 17.1% weight loss at 24 weeks (Jastreboff et al., 2023).",
            "Tesamorelin Phase 3: ~15-20% visceral fat reduction in HIV lipodystrophy (Falutz et al., 2007).",
        ],
        "evidence_summary": "Retatrutide has strong Phase 2 obesity data. Tesamorelin has Phase 3 data for visceral fat. The combination is logical but lacks dedicated trials — each targets different fat-loss pathways (incretin vs GH-axis), suggesting additive potential.",
    },
    "retatrutide+tesamorelin+mots-c": {
        "name": "Retatrutide + Tesamorelin + MOTS-c",
        "goal": "Weight loss with metabolic optimization",
        "cycle_weeks": 16,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Retatrutide 2mg weekly + Tesamorelin 2mg daily. Establish incretin and GH-axis baseline before adding mitochondrial support.",
                "dosing_details": "Retatrutide weekly subQ. Tesamorelin daily subQ evening.",
                "timing": "Retatrutide any day. Tesamorelin evening empty stomach.",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Retatrutide 4mg weekly + Tesamorelin 2mg daily + MOTS-c 5mg 3x weekly. Introduce mitochondrial peptide after metabolic baseline is established.",
                "dosing_details": "MOTS-c subQ injection. Separate from other injection sites. Can be taken pre-workout or morning.",
                "timing": "MOTS-c morning or pre-workout on training days. Retatrutide separate day. Tesamorelin evening.",
            },
            {
                "phase": 3,
                "weeks": "9-16",
                "protocol": "Retatrutide 6-8mg weekly + Tesamorelin 2mg daily + MOTS-c 10mg 3x weekly. Full dose triple protocol targeting weight loss, visceral fat, and metabolic flexibility.",
                "dosing_details": "MOTS-c increased to 10mg. All three peptides maintained at full dose.",
                "timing": "Same timing as phase 2.",
            },
        ],
        "post_cycle": "4 weeks off MOTS-c. Retatrutide and tesamorelin may continue as maintenance. MOTS-c cycling follows mitochondrial adaptation principles.",
        "sources": [
            "Retatrutide: Phase 2 obesity data, triple agonist mechanism.",
            "Tesamorelin: Phase 3 visceral fat reduction data.",
            "MOTS-c: Discovered 2015, animal studies show improved metabolic flexibility and exercise capacity.",
        ],
        "evidence_summary": "The first two components have strong evidence. MOTS-c is early-stage (animal/limited human). The triple combination lacks any controlled data.",
    },
    "semaglutide+tesamorelin": {
        "name": "Semaglutide + Tesamorelin",
        "goal": "Weight loss with visceral fat reduction",
        "cycle_weeks": 24,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Semaglutide 0.25mg subQ weekly + Tesamorelin 2mg subQ daily. Standard semaglutide titration start with GHRH support.",
                "dosing_details": "Semaglutide weekly subQ (abdomen, thigh, arm). Tesamorelin daily subQ. Different injection sites.",
                "timing": "Semaglutide same day weekly, morning preferred. Tesamorelin evening empty stomach.",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Semaglutide 0.5mg weekly + Tesamorelin 2mg daily. Continue standard semaglutide escalation per prescribing guidelines.",
                "dosing_details": "Semaglutide dose doubled to 0.5mg weekly. Tesamorelin unchanged.",
                "timing": "Same timing windows.",
            },
            {
                "phase": 3,
                "weeks": "9-24",
                "protocol": "Semaglutide titrated to therapeutic dose (1.0-2.4mg weekly) + Tesamorelin 2mg daily. Full dose maintenance. Wegovy target dose is 2.4mg weekly.",
                "dosing_details": "Escalate semaglutide every 4 weeks per FDA protocol: 1.0mg, 1.7mg, 2.4mg. Continue tesamorelin 2mg daily.",
                "timing": "Same timing.",
            },
        ],
        "post_cycle": "If discontinuing semaglutide, taper over 4 weeks to minimize appetite rebound and blood sugar fluctuation. Tesamorelin can be stopped without taper.",
        "sources": [
            "Semaglutide: FDA approved (Wegovy). STEP trials show ~15% weight loss at 68 weeks.",
            "Tesamorelin: FDA approved (Egrifta) for HIV lipodystrophy. Phase 3 data for visceral fat.",
        ],
        "evidence_summary": "Both FDA approved individually. The combination has strong rationale (GLP-1 + GHRH) but lacks dedicated combination trials. Each has large-trial evidence in their respective indications.",
    },
    "tirzepatide+tesamorelin": {
        "name": "Tirzepatide + Tesamorelin",
        "goal": "Weight loss with visceral fat reduction",
        "cycle_weeks": 24,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Tirzepatide 2.5mg subQ weekly + Tesamorelin 2mg subQ daily. Standard tirzepatide initiation dose with concurrent GHRH analog.",
                "dosing_details": "Tirzepatide weekly subQ (separate from tesamorelin site). Tesamorelin daily subQ evening.",
                "timing": "Tirzepatide same day weekly (any time). Tesamorelin evening empty stomach.",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Tirzepatide 5mg weekly + Tesamorelin 2mg daily. First dose escalation following standard Mounjaro/Zepbound titration.",
                "dosing_details": "Tirzepatide increased to 5mg weekly. Tesamorelin unchanged.",
                "timing": "Same timing.",
            },
            {
                "phase": 3,
                "weeks": "9-24",
                "protocol": "Tirzepatide escalated to 10-15mg weekly + Tesamorelin 2mg daily. Full dual maintenance dose — dual GIP/GLP-1 agonist plus GHRH analog.",
                "dosing_details": "Escalate tirzepatide every 4 weeks: 7.5mg, 10mg, 12.5mg, 15mg. Tesamorelin 2mg daily.",
                "timing": "Same timing.",
            },
        ],
        "post_cycle": "Taper tirzepatide over 4 weeks if discontinuing. Tesamorelin can stop without taper. Monitor appetite and glucose during transition.",
        "sources": [
            "Tirzepatide: FDA approved (Mounjaro/Zepbound). SURMOUNT trials show 15-22% weight loss.",
            "Tesamorelin: FDA approved (Egrifta). Phase 3 visceral fat data.",
        ],
        "evidence_summary": "Both FDA approved individually. Tirzepatide has the strongest weight loss data among approved GLP-1/GIP drugs. Combination with tesamorelin is a common research protocol but lacks formal combination trials.",
    },
    "melanotan2+ghk-cu": {
        "name": "Melanotan II + GHK-Cu",
        "goal": "Tanning with skin quality support",
        "cycle_weeks": 6,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-2",
                "protocol": "Melanotan II 0.25-0.5mg subQ daily or every other day (loading phase) + GHK-Cu 2mg subQ daily. Low-start melanotan to assess nausea tolerance before escalating.",
                "dosing_details": "Melanotan II: subQ abdomen. Start low, titrate up. GHK-Cu: subQ separate site, evening preferred.",
                "timing": "Melanotan II: morning (nausea less disruptive if asleep — consider evening). GHK-Cu: evening.",
            },
            {
                "phase": 2,
                "weeks": "3-6",
                "protocol": "Melanotan II 0.5-1mg daily or EOD (maintenance) + GHK-Cu 2-5mg daily. Reduce melanotan frequency once desired pigmentation approaches. GHK-Cu supports skin health during melanogenesis.",
                "dosing_details": "Maintain or reduce melanotan frequency. GHK-Cu maintained for skin remodeling support.",
                "timing": "Same timing as phase 1.",
            },
        ],
        "post_cycle": "2 weeks off. Melanotan II effects on pigmentation persist for weeks to months after cessation — re-dose only when fading becomes noticeable.",
        "sources": [
            "Melanotan II: Studied in Phase 1/2 for erythropoietic protoporphyria. Pigmentation effects well characterized.",
            "GHK-Cu: Multiple clinical studies for wound healing and skin regeneration.",
        ],
        "evidence_summary": "Melanotan II has limited clinical trials but well-documented melanogenesis. GHK-Cu has solid wound-healing data. Combination is anecdotal — each addresses different aspects of skin aesthetics.",
    },
    "ghk-cu+tb500": {
        "name": "GHK-Cu + TB-500",
        "goal": "Systemic tissue repair and recovery",
        "cycle_weeks": 6,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-2",
                "protocol": "GHK-Cu 5mg subQ daily + TB-500 2.5mg subQ 2x weekly. Loading phase — higher GHK-Cu dose for systemic copper peptide saturation.",
                "dosing_details": "GHK-Cu daily subQ injection. TB-500 systemic subQ (abdomen/thigh). Separate injection sites.",
                "timing": "GHK-Cu: evening. TB-500: spaced 3-4 days apart (e.g., Monday/Thursday).",
            },
            {
                "phase": 2,
                "weeks": "3-6",
                "protocol": "GHK-Cu 2-3mg subQ daily + TB-500 2.5mg 1x weekly. Maintenance phase — reduced frequency after initial loading.",
                "dosing_details": "GHK-Cu dose reduced. TB-500 reduced to once weekly.",
                "timing": "Same timing as phase 1.",
            },
        ],
        "post_cycle": "2 weeks off minimum. Can repeat cycle if needed. GHK-Cu for skin/connective tissue, TB-500 for systemic healing — complementary mechanisms.",
        "sources": [
            "GHK-Cu: clinical wound healing data, collagen synthesis stimulation.",
            "TB-500: preclinical angiogenesis and cell migration data. Limited human trials.",
        ],
        "evidence_summary": "GHK-Cu has stronger human evidence (topical wound healing). TB-500 has strong preclinical but limited human data. The combination is common in recovery protocols but lacks controlled trials.",
    },
    "semaglutide+aod9604": {
        "name": "Semaglutide + AOD-9604",
        "goal": "Weight loss with targeted fat metabolism support",
        "cycle_weeks": 24,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Semaglutide 0.25mg subQ weekly + AOD-9604 300mcg subQ daily. Standard semaglutide start with low-dose AOD for lipolysis support.",
                "dosing_details": "Semaglutide weekly subQ. AOD-9604 daily subQ (morning and/or pre-bed). Different injection sites.",
                "timing": "Semaglutide weekly. AOD-9604 morning and evening for twice-daily dosing option.",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Semaglutide 0.5mg weekly + AOD-9604 500mcg daily. Both increased to mid-range doses.",
                "dosing_details": "Semaglutide dose doubled. AOD-9604 increased to 500mcg daily.",
                "timing": "Same timing.",
            },
            {
                "phase": 3,
                "weeks": "9-24",
                "protocol": "Semaglutide titrated to 1.0-2.4mg weekly + AOD-9604 500mcg 1-2x daily. Full dose maintenance. AOD adds GH-fragment lipolysis signaling to GLP-1 appetite suppression.",
                "dosing_details": "Escalate semaglutide per FDA protocol. AOD-9604 maintained at full dose.",
                "timing": "Same timing.",
            },
        ],
        "post_cycle": "Taper semaglutide over 4 weeks if discontinuing. AOD-9604 can stop without taper.",
        "sources": [
            "Semaglutide: FDA approved. STEP trials data.",
            "AOD-9604: Completed Phase 2 for obesity. Modest fat loss observed. Program not continued to Phase 3.",
        ],
        "evidence_summary": "Semaglutide has strong FDA-reviewed evidence. AOD-9604 has Phase 2 data showing modest fat loss. AOD's mechanism (GH fragment 177-191) is distinct from GLP-1, suggesting additive potential. The combination lacks trials.",
    },
    "tirzepatide+mots-c+ss-31": {
        "name": "Tirzepatide + MOTS-c + SS-31",
        "goal": "Metabolic optimization with mitochondrial support",
        "cycle_weeks": 16,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Tirzepatide 2.5mg subQ weekly + SS-31 20mg subQ daily. Establish incretin baseline and mitochondrial priming before adding MOTS-c.",
                "dosing_details": "Tirzepatide weekly subQ. SS-31 daily subQ (evening). Separate sites.",
                "timing": "Tirzepatide weekly any time. SS-31 evening.",
            },
            {
                "phase": 2,
                "weeks": "5-8",
                "protocol": "Tirzepatide 5mg weekly + SS-31 40mg daily + MOTS-c 5mg 3x weekly. Introduce MOTS-c after 4-week baseline. Dose escalation of tirzepatide and SS-31.",
                "dosing_details": "MOTS-c subQ morning or pre-workout. SS-31 increased to 40mg. Tirzepatide at 5mg.",
                "timing": "MOTS-c pre-workout or morning. SS-31 evening. Tirzepatide separate day.",
            },
            {
                "phase": 3,
                "weeks": "9-16",
                "protocol": "Tirzepatide 10-15mg weekly + SS-31 40mg daily + MOTS-c 10mg 3x weekly. Full maintenance — dual incretin agonist + dual mitochondrial support.",
                "dosing_details": "Tirzepatide at max tolerated dose (10-15mg). SS-31 and MOTS-c at full dose.",
                "timing": "Same timing as phase 2.",
            },
        ],
        "post_cycle": "2 weeks off SS-31 and MOTS-c. Tirzepatide can continue as maintenance. Mitochondrial peptides are typically cycled.",
        "sources": [
            "Tirzepatide: FDA approved, SURMOUNT trials.",
            "SS-31: FDA Orphan Drug for mitochondrial disease. Phase 2 heart failure data.",
            "MOTS-c: Discovered 2015, animal studies only, very limited human data.",
        ],
        "evidence_summary": "Tirzepatide has the strongest evidence. SS-31 has FDA Orphan status and human trials in mitochondrial disease. MOTS-c is early-stage. The triple combination is speculative and lacks any clinical data.",
    },
    "retatrutide+cagrilintide": {
        "name": "Retatrutide + Cagrilintide",
        "goal": "Maximum metabolic weight loss",
        "cycle_weeks": 48,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Retatrutide 2mg subQ weekly + Cagrilintide 0.3mg subQ weekly. Low starting doses for both to assess GI tolerance. Triple agonist + amylin analog.",
                "dosing_details": "Both weekly subQ injections on separate days to minimize injection site reactions.",
                "timing": "Stagger injections 2-3 days apart (e.g., retatrutide Monday, cagrilintide Thursday).",
            },
            {
                "phase": 2,
                "weeks": "5-12",
                "protocol": "Retatrutide 4mg weekly + Cagrilintide 0.6mg weekly. Mid-level dose escalation. Monitor appetite, nausea, and tolerance closely.",
                "dosing_details": "Both doses increased. Continue staggered injection schedule.",
                "timing": "Same staggered schedule.",
            },
            {
                "phase": 3,
                "weeks": "13-48",
                "protocol": "Retatrutide 6-8mg weekly + Cagrilintide 1.2-2.4mg weekly. Full maintenance dose. Triple GLP-1/GIP/glucagon agonist + long-acting amylin analog for additive weight loss.",
                "dosing_details": "Titrate cagrilintide to max tolerated dose (up to 2.4mg). Retatrutide at 6-8mg.",
                "timing": "Same staggered schedule.",
            },
        ],
        "post_cycle": "If discontinuing, taper both agents over 4 weeks. Appetite rebound can be significant with dual withdrawal of incretin + amylin signaling.",
        "sources": [
            "Retatrutide: Phase 2 data showing superior weight loss to existing incretins.",
            "Cagrilintide: Phase 2 CagriSema trials with semaglutide showing additive weight loss.",
        ],
        "evidence_summary": "Both are investigational with Phase 2 data. Novo Nordisk is developing cagrilintide + semaglutide (CagriSema) — the retatrutide pairing is a research extrapolation. Phase 3 data pending for both agents.",
    },
    "semaglutide+cagrilintide": {
        "name": "Semaglutide + Cagrilintide (CagriSema protocol)",
        "goal": "Weight loss — dual GLP-1 + amylin",
        "cycle_weeks": 68,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Semaglutide 0.25mg subQ weekly + Cagrilintide 0.3mg subQ weekly. Standard dual start per CagriSema trial protocol. Low doses to establish GI tolerance.",
                "dosing_details": "Separate weekly injections. Stagger 2-3 days apart. Both subQ in abdomen or thigh.",
                "timing": "Stagger injection days (e.g., semaglutide Monday, cagrilintide Thursday).",
            },
            {
                "phase": 2,
                "weeks": "5-16",
                "protocol": "Semaglutide titrated up by 0.25-0.5mg every 4 weeks + Cagrilintide titrated up by 0.3mg every 4 weeks. Parallel dose escalation following CagriSema trial design.",
                "dosing_details": "Systematic escalation every 4 weeks. Monitor GI side effects closely.",
                "timing": "Same staggered schedule.",
            },
            {
                "phase": 3,
                "weeks": "17-68",
                "protocol": "Semaglutide 2.4mg weekly + Cagrilintide 2.4mg weekly. Full maintenance dose. GLP-1 + amylin dual agonist at therapeutic levels.",
                "dosing_details": "Both at max dose. Continue staggered injection schedule for tolerance.",
                "timing": "Same staggered schedule.",
            },
        ],
        "post_cycle": "Taper both over 4-8 weeks. CagriSema trial design includes extended follow-up post-treatment. Monitor for appetite rebound and weight regain.",
        "sources": [
            "CagriSema Phase 2: Semaglutide 2.4mg + cagrilintide 2.4mg produced ~15.6% weight loss at 32 weeks.",
            "Semaglutide: FDA approved, STEP trials.",
        ],
        "evidence_summary": "This combination has the strongest evidence of any dual-incretin stack — CagriSema is an active clinical development program with published Phase 2 data. Phase 3 trials ongoing.",
    },
    "tesamorelin+mk677": {
        "name": "Tesamorelin + MK-677",
        "goal": "GH-axis amplification (injectable + oral)",
        "cycle_weeks": 12,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-12",
                "protocol": "Tesamorelin 2mg subQ daily (evening) + MK-677 10-25mg orally daily (before bed). Dual GH-axis activation — GHRH analog (injectable) + ghrelin mimetic (oral) for amplified GH pulse.",
                "dosing_details": "Tesamorelin: standard subQ injection, empty stomach. MK-677: oral capsule, take before bed to sleep through hunger side effect.",
                "timing": "Both in evening window. MK-677 before bed (hunger peak passes during sleep). Tesamorelin 2h+ after last meal.",
            },
        ],
        "post_cycle": "4 weeks off minimum. GH-axis desensitization is a real concern with dual activation. Monitor IGF-1 levels and glucose during cycle.",
        "sources": [
            "Tesamorelin: Phase 3 data, FDA approved for HIV lipodystrophy.",
            "MK-677: Human trials in elderly and frailty populations. Increases IGF-1 dose-dependently.",
        ],
        "evidence_summary": "Both have human trial data. Tesamorelin is FDA approved, MK-677 has Phase 2 human data. The combination is logical (GHRH + ghrelin agonist) but lacks dedicated trials. Monitor glucose — both can affect insulin sensitivity.",
    },
    "pt141+kisspeptin10": {
        "name": "PT-141 + Kisspeptin-10",
        "goal": "Sexual function and arousal",
        "cycle_weeks": 0,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "PRN",
                "protocol": "PT-141 0.75-1.75mg subQ as needed + Kisspeptin-10 0.5-2mcg/kg subQ as needed. PT-141 addresses desire via melanocortin pathway. Kisspeptin-10 targets reproductive hormone signaling via GnRH.",
                "dosing_details": "Both subQ injection. Administer separately. PT-141 has ~30-60min onset. Kisspeptin-10 has rapid GnRH pulse within minutes.",
                "timing": "As needed before sexual activity. PT-141 effects last 6-12 hours. Kisspeptin-10 effects shorter (~2-4 hours).",
            },
        ],
        "post_cycle": "No cycling required for either agent. Used on as-needed basis. PT-141 max 8 doses/month per FDA labeling.",
        "sources": [
            "PT-141 (bremelanotide): FDA approved as Vyleesi for HSDD.",
            "Kisspeptin-10: Phase 1/2 human trials for reproductive health. Stimulates LH and FSH release.",
        ],
        "evidence_summary": "PT-141 is FDA approved with clinical trial data. Kisspeptin-10 has Phase 1/2 human data showing GnRH stimulation. The combination targets both desire (melanocortin) and hormonal signaling (kisspeptin/GnRH) — distinct mechanisms that may complement each other.",
    },
    "igf1-lr3+peg-mgf": {
        "name": "IGF-1 LR3 + PEG-MGF",
        "goal": "Direct anabolic signaling",
        "cycle_weeks": 6,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "IGF-1 LR3 20-40mcg subQ daily (post-workout or morning) + PEG-MGF 200-400mcg subQ 2-3x weekly. Direct IGF-1 receptor activation (LR3) + mechano-growth factor satellite cell signaling (MGF).",
                "dosing_details": "IGF-1 LR3: daily subQ, close to target muscle group if desired. PEG-MGF: subQ, spaced every other day.",
                "timing": "IGF-1 LR3 post-workout or morning. PEG-MGF on non-consecutive days.",
            },
            {
                "phase": 2,
                "weeks": "5-6",
                "protocol": "Reduce frequency — IGF-1 LR3 EOD + PEG-MGF 1x weekly. Taper phase before off-cycle.",
                "dosing_details": "Reduced frequency to taper off.",
                "timing": "Same timing windows.",
            },
        ],
        "post_cycle": "4 weeks off minimum. IGF-1 LR3 has strong anabolic signaling — cycling is critical to avoid receptor desensitization and allow natural IGF-1 axis to normalize.",
        "sources": [
            "IGF-1 LR3: Modified from natural IGF-1 for extended half-life. Preclinical anabolic data.",
            "PEG-MGF: PEGylated MGF for extended half-life. Preclinical muscle repair signaling data.",
        ],
        "evidence_summary": "Both are research tools with preclinical evidence. IGF-1 LR3 has strong mechanistic rationale (IGF-1 receptor agonist). PEG-MGF is derived from the IGF-1 gene splice variant MGF. Neither has meaningful human clinical trial data. Long-term safety unknown.",
    },
    "semax+dihexa": {
        "name": "Semax + Dihexa",
        "goal": "Cognitive enhancement and neuroplasticity",
        "cycle_weeks": 4,
        "off_weeks": 1,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-4",
                "protocol": "Semax 400-800mcg intranasal daily (morning) + Dihexa 10-20mg orally daily (morning). Semax provides BDNF-driven cognitive boost while Dihexa crosses blood-brain barrier and promotes synaptogenesis.",
                "dosing_details": "Semax: intranasal spray/drops. Dihexa: oral capsule, can take with or without food.",
                "timing": "Both in morning for daytime cognitive effects. Semax may cause mild stimulation — avoid late-day dosing.",
            },
        ],
        "post_cycle": "1 week off minimum. Neuroplasticity peptides benefit from cycling to maintain sensitivity.",
        "sources": [
            "Semax: Russian-approved medication for stroke recovery. Human studies show increased BDNF.",
            "Dihexa: Preclinical studies show synaptogenesis and cognitive improvement in animal models. Minimal human data.",
        ],
        "evidence_summary": "Semax has regional regulatory approval and human clinical data. Dihexa is preclinical with impressive animal data (improved cognition in rodent models) but almost no human studies. The combination is speculative — one has human evidence, the other is purely preclinical.",
    },
    "ghrp6+sermorelin": {
        "name": "GHRP-6 + Sermorelin",
        "goal": "GH pulse stimulation with appetite increase",
        "cycle_weeks": 12,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-12",
                "protocol": "GHRP-6 200-300mcg subQ + Sermorelin 200-300mcg subQ, 1-2x daily (morning and/or evening). GHRH (sermorelin) + GHRP (GHRP-6) synergistic GH pulse. GHRP-6 adds notable appetite stimulation.",
                "dosing_details": "Mix in same syringe for single injection. Morning upon waking (empty stomach, wait 20 min to eat). Evening 2h+ after last meal.",
                "timing": "1-2x daily. Morning + pre-bed for twice-daily protocol. Pre-workout is also an option.",
            },
        ],
        "post_cycle": "4 weeks off minimum. GH-axis desensitization possible with prolonged use. Sermorelin is shorter-acting than modified GHRH analogs (like CJC-1295-DAC).",
        "sources": [
            "Sermorelin: FDA approved for pediatric GH deficiency diagnosis.",
            "GHRP-6: Preclinical and some human GH pulse data. Strong hunger effect documented.",
        ],
        "evidence_summary": "Sermorelin has FDA approval for diagnostic use — the strongest regulatory standing among GHRH analogs. GHRP-6 has mechanistic data. The GHRH+GHRP synergy is well-established in GH literature.",
    },
    "liraglutide+tirzepatide": {
        "name": "Liraglutide + Tirzepatide",
        "goal": "Weight loss — dual GLP-1 approach",
        "cycle_weeks": 0,
        "off_weeks": 0,
        "phases": [
            {
                "phase": 1,
                "weeks": "All",
                "protocol": "Medical guidance: These are FDA-approved GLP-1/GIP medications. Do NOT combine without physician supervision. Both act on incretin pathways with overlapping mechanisms — combining them increases side effect risk (nausea, vomiting, hypoglycemia) without proven additive benefit over standard monotherapy titration.",
                "dosing_details": "Follow approved prescribing information for one agent. Choose tirzepatide (stronger weight loss) or liraglutide (shorter half-life, daily dosing).",
                "timing": "Tirzepatide: once weekly. Liraglutide: once daily.",
            },
        ],
        "post_cycle": "Taper whichever agent is used over 4 weeks. Do not combine incretin-based drugs outside clinical trials.",
        "sources": [
            "Liraglutide: FDA approved as Victoza (diabetes) and Saxenda (weight).",
            "Tirzepatide: FDA approved as Mounjaro (diabetes) and Zepbound (weight).",
        ],
        "evidence_summary": "Both are FDA approved individually with extensive trial data. Combining GLP-1-class drugs is not recommended due to overlapping mechanisms and increased side effect risk. Choose one agent and titrate to effective dose.",
    },
    "ss31+humanin": {
        "name": "SS-31 (Elamipretide) + Humanin",
        "goal": "Mitochondrial protection and longevity signaling",
        "cycle_weeks": 8,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-8",
                "protocol": "SS-31 20-40mg subQ daily (evening) + Humanin 2-4mg subQ daily (morning). SS-31 targets mitochondrial cardiolipin for energy optimization. Humanin provides cellular stress protection and insulin sensitivity signaling.",
                "dosing_details": "SS-31 daily subQ. Humanin daily subQ (separate site). Both water-soluble peptides requiring proper reconstitution and refrigeration.",
                "timing": "SS-31 evening for mitochondrial repair during rest. Humanin morning for metabolic signaling throughout the day.",
            },
        ],
        "post_cycle": "2 weeks off. Mitochondrial peptides require cycling to maintain cellular sensitivity to their signaling effects.",
        "sources": [
            "SS-31: FDA Orphan Drug designation. Phase 2 trials in mitochondrial disease and heart failure.",
            "Humanin: Discovered 2001. Extensive preclinical data for cytoprotection. Very limited human studies.",
        ],
        "evidence_summary": "SS-31 has the strongest evidence of any mitochondrial peptide with FDA Orphan status and human clinical trials. Humanin has broad preclinical data but minimal human evidence. The combination lacks any controlled data.",
    },
    "thymosin-alpha1+thymulin": {
        "name": "Thymosin Alpha-1 + Thymulin",
        "goal": "Immune modulation and thymic support",
        "cycle_weeks": 6,
        "off_weeks": 3,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-6",
                "protocol": "Thymosin Alpha-1 750-1500mcg subQ 1-2x weekly + Thymulin 100-500mcg subQ daily or EOD. Dual thymic peptide protocol — TA1 for T-cell activation and immunomodulation, thymulin for T-cell differentiation and maturation.",
                "dosing_details": "TA1: subQ injection, fewer weekly injections. Thymulin: more frequent (daily or every other day) subQ. Separate injection sites.",
                "timing": "TA1: morning (may cause mild transient warmth/flush). Thymulin: morning, separate from TA1.",
            },
        ],
        "post_cycle": "3 weeks off minimum. Thymic peptides are immunomodulatory — cycling is important to avoid immune system adaptation.",
        "sources": [
            "Thymosin Alpha-1: Approved in multiple countries for hepatitis B/C and immune support. Published human trials.",
            "Thymulin: Zinc-dependent thymic hormone. Preclinical and some human studies for immune regulation.",
        ],
        "evidence_summary": "Thymosin Alpha-1 has the strongest evidence with human clinical data and international regulatory approvals. Thymulin has more limited human data. Both target different aspects of T-cell biology — combination is mechanistically logical but lacks controlled trials.",
    },
    "dsip+pinealon": {
        "name": "DSIP + Pinealon",
        "goal": "Deep sleep and circadian rhythm support",
        "cycle_weeks": 8,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-8",
                "protocol": "DSIP 100-400mcg subQ or intranasal 30-60 min before bed, nightly. Pinealon 500-1000mcg subQ or intranasal 1-2x daily. DSIP targets delta-wave sleep architecture; Pinealon supports circadian regulation and pineal function.",
                "dosing_details": "DSIP: subQ or intranasal, best absorbed before sleep. Start at 100mcg and titrate up. Pinealon: subQ or intranasal, can be taken morning and/or evening.",
                "timing": "DSIP: 30-60 min before bedtime. Pinealon: morning and/or evening — avoid late-night dosing that could interfere with DSIP sleep architecture effects.",
            },
        ],
        "post_cycle": "2 weeks off. DSIP may have carry-over sleep benefits post-cycle. Monitor sleep quality changes.",
        "sources": [
            "DSIP: Identified as sleep-promoting peptide in animal and limited human studies.",
            "Pinealon: Synthetic pineal peptide, studied for circadian rhythm support primarily in Eastern European research.",
        ],
        "evidence_summary": "DSIP has modest human data for sleep architecture improvement. Pinealon evidence is predominantly preclinical. Both target sleep via complementary mechanisms — delta-wave promotion (DSIP) and circadian regulation (Pinealon).",
    },
    "pinealon+selank": {
        "name": "Pinealon + Selank",
        "goal": "Sleep quality with anxiety support",
        "cycle_weeks": 8,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-8",
                "protocol": "Pinealon 500-1000mcg subQ or intranasal 1-2x daily. Selank 500-1000mcg subQ or intranasal 1-2x daily. Pinealon for circadian/sleep support, Selank for daytime calm and anxiety reduction — complementary approach targeting both sleep quality and stress.",
                "dosing_details": "Both can be administered subQ or intranasal. Pinealon can be split morning and evening. Selank is best taken in morning and early afternoon to avoid sedation overlap with sleep.",
                "timing": "Pinealon: morning and/or early evening. Selank: morning and early afternoon. Avoid Selank late in the day to prevent interference with natural sleep drive.",
            },
        ],
        "post_cycle": "2 weeks off. Monitor for rebound anxiety or sleep changes during washout.",
        "sources": [
            "Selank: Anxiolytic peptide with limited human efficacy trials.",
            "Pinealon: Synthetic pineal peptide, limited published human data.",
        ],
        "evidence_summary": "Selank has some human clinical data for anxiety reduction. Pinealon evidence is preclinical. Combination is mechanistically plausible (sleep + anxiety) but evidence certainty is low for both peptides.",
    },
    "bpc-157+ghk-cu": {
        "name": "BPC-157 + GHK-Cu",
        "goal": "Systemic healing and tissue repair",
        "cycle_weeks": 8,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-8",
                "protocol": "BPC-157 250-500mcg subQ 1-2x daily. GHK-Cu 1-5mg subQ daily or EOD. BPC-157 for systemic healing and angiogenesis support; GHK-Cu for wound healing, tissue regeneration, and skin quality. Both target repair via different signaling pathways.",
                "dosing_details": "BPC-157: best dosed twice daily due to short half-life. GHK-Cu: once daily subQ is typical. Can be combined in same injection if pH-compatible.",
                "timing": "BPC-157: morning and evening. GHK-Cu: morning preferred. Separate injection sites for best absorption.",
            },
        ],
        "post_cycle": "4 weeks minimum off. Healing peptides should be cycled to prevent adaptation.",
        "sources": [
            "BPC-157: Extensive preclinical GI and soft tissue healing data; minimal human trials.",
            "GHK-Cu: Some human data for wound healing and skin regeneration.",
        ],
        "evidence_summary": "BPC-157 has robust preclinical evidence for healing but very limited human trial data. GHK-Cu has modest human evidence particularly for topical wound healing. Combination logic is strong but controlled human data is limited.",
    },
    "tb-500+bpc-157": {
        "name": "TB-500 + BPC-157",
        "goal": "Advanced recovery and connective tissue healing",
        "cycle_weeks": 6,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-6",
                "protocol": "TB-500 (Thymosin Beta-4) 2.5-5mg subQ 2x weekly for first 2 weeks, then 2.5mg weekly for maintenance. BPC-157 250-500mcg subQ 1-2x daily throughout. TB-500 for actin binding, cell migration, and systemic repair signaling; BPC-157 for localized angiogenesis and healing.",
                "dosing_details": "TB-500: loading phase (2x/week) then maintenance (1x/week). BPC-157: consistent twice-daily dosing for steady-state levels.",
                "timing": "TB-500: any time of day, consistent schedule. BPC-157: morning and evening. Separate injection sites.",
            },
        ],
        "post_cycle": "4 weeks minimum. This is a heavy healing stack — adequate off-time is critical.",
        "sources": [
            "TB-500: Preclinical for wound healing and actin regulation; limited human data.",
            "BPC-157: Broad preclinical healing evidence across multiple tissue types.",
        ],
        "evidence_summary": "Both peptides have robust preclinical but very limited human evidence. Widely combined in anecdotal recovery protocols. The mechanistic rationale (actin remodeling + angiogenesis) is biologically plausible but unvalidated in controlled human trials.",
    },
    "mots-c+humanin": {
        "name": "MOTS-c + Humanin",
        "goal": "Mitochondrial support and metabolic endurance",
        "cycle_weeks": 12,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-12",
                "protocol": "MOTS-c 5-10mg subQ 3-5x weekly. Humanin 2-4mg subQ daily or EOD. Both are mitochondrial-derived peptides (MDPs) — MOTS-c for metabolic flexibility and exercise tolerance, Humanin for cytoprotective and metabolic signaling.",
                "dosing_details": "MOTS-c: higher dose range, fewer weekly injections. Humanin: lower dose, can be taken daily. Both subQ.",
                "timing": "MOTS-c: morning or pre-exercise. Humanin: morning, can be combined in same injection session.",
            },
        ],
        "post_cycle": "2 weeks off. Mitochondrial peptide cycling is not well-studied — standard precaution.",
        "sources": [
            "MOTS-c: Identified as mitochondrial peptide with metabolic regulatory functions; early human studies.",
            "Humanin: Cytoprotective MDP with some cell and animal data for metabolic health.",
        ],
        "evidence_summary": "Both are mitochondrial-derived peptides with emerging but still early human evidence. MOTS-c has some human exercise trial data. Humanin is more preclinical. Their combined mitochondrial targeting is mechanistically logical.",
    },
    "ipamorelin+cjc-1295": {
        "name": "Ipamorelin + CJC-1295",
        "goal": "GH pulse support and lean mass",
        "cycle_weeks": 12,
        "off_weeks": 4,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-12",
                "protocol": "CJC-1295 500-1000mcg subQ 2x weekly (morning). Ipamorelin 200-500mcg subQ 1-2x daily. CJC-1295 provides sustained GHRH analog signaling with extended half-life; Ipamorelin provides GH pulse stimulation — synergistic GH-axis activation without exogenous GH.",
                "dosing_details": "CJC-1295: twice weekly subQ due to DAC (Drug Affinity Complex) extended half-life. Ipamorelin: split into two daily doses if possible for consistent GH pulse signaling.",
                "timing": "CJC-1295: morning of dosing days (e.g., Mon/Thu). Ipamorelin: first dose upon waking (fasted), second dose early afternoon or post-workout if applicable. Avoid late-night dosing.",
            },
        ],
        "post_cycle": "4 weeks minimum. GH-axis peptides require adequate off-time for hypothalamic sensitivity recovery.",
        "sources": [
            "CJC-1295: GHRH analog with DAC technology; studied for GH deficiency and body composition.",
            "Ipamorelin: Selective GH secretagogue with better safety profile than earlier GHRPs.",
        ],
        "evidence_summary": "CJC-1295 has some human data for GH elevation. Ipamorelin is well-tolerated with GH pulse data. The GHRH + GHRP synergy is mechanistically well-established from endocrine literature.",
    },
    "semax+selank+dsip": {
        "name": "Semax + Selank + DSIP",
        "goal": "Cognitive focus with stress modulation and sleep support",
        "cycle_weeks": 6,
        "off_weeks": 2,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-6",
                "protocol": "Semax 400-1200mcg intranasal 1-2x daily. Selank 500-1000mcg intranasal 1-2x daily. DSIP 100-400mcg intranasal or subQ 30-60 min before bed. Semax for focus and cognitive enhancement, Selank for daytime anxiety modulation, DSIP for sleep architecture optimization. Full-spectrum cognitive stack.",
                "dosing_details": "All three can be administered intranasal. Semax and Selank during daytime hours. DSIP exclusively before sleep.",
                "timing": "Semax: morning and early afternoon. Selank: morning and early afternoon (avoid evening). DSIP: 30-60 min before bedtime. Note: DSIP may cause drowsiness if taken during the day.",
            },
        ],
        "post_cycle": "2-4 weeks off. Cognitive peptides benefit from cycling to maintain sensitivity.",
        "sources": [
            "Semax: Russian nootropic with some human cognitive data.",
            "Selank: Anxiolytic peptide with limited human trials.",
            "DSIP: Sleep peptide with modest human sleep architecture data.",
        ],
        "evidence_summary": "Semax has the strongest human cognitive data of the three. Selank has some human anxiety data. DSIP evidence is weaker. The triple combination covers cognition, mood, and sleep but no controlled studies exist for this specific stack.",
    },
}

GOAL_BLUEPRINTS = {
    "fat_loss": {
        "label": "Fat Loss",
        "primary_targets": ["fat_loss", "appetite_modulation", "visceral_fat", "glycemic_support"],
        "optional_support": ["gh_axis", "metabolic_flexibility"],
        "default_priority": ["retatrutide", "tesamorelin"],
        "phase_note": "Research scenario: prioritize core metabolic/weight peptide first, then consider adjunct support signals in later phase if rationale remains strong.",
    },
    "lean_mass": {
        "label": "Lean Mass Support",
        "primary_targets": ["lean_mass_support", "gh_axis", "recovery"],
        "optional_support": ["glycemic_support"],
        "default_priority": ["tesamorelin", "ipamorelin"],
        "phase_note": "Research scenario: start with strongest GH-axis signal, then evaluate additive recovery-related candidates where evidence supports complementarity.",
    },
    "focus_calm": {
        "label": "Focus / Calm",
        "primary_targets": ["focus", "calm", "stress_response", "anxiety_support"],
        "optional_support": [],
        "default_priority": ["semax", "selank"],
        "phase_note": "Research scenario: prioritize cognitive/anxiolytic objective alignment and avoid over-stacking when evidence certainty is limited.",
    },
    "tanning": {
        "label": "Tanning / UV Response",
        "primary_targets": ["tanning_support", "uv_response", "skin_quality"],
        "optional_support": ["recovery"],
        "default_priority": ["melanotan-2", "ghk-cu"],
        "phase_note": "Research scenario: center on pigmentation-focused signal first, then consider skin-repair support as secondary context.",
    },
    "recovery_healing": {
        "label": "Recovery / Healing Support",
        "primary_targets": ["recovery", "healing_support", "connective_tissue_support"],
        "optional_support": ["gh_axis", "inflammation_hypothesis"],
        "default_priority": ["ghk-cu", "tb-500"],
        "phase_note": "Research scenario: prioritize direct recovery/healing signal candidates and treat broader inflammation claims as lower-certainty adjuncts.",
    },
    "sleep_stress": {
        "label": "Sleep / Stress Regulation",
        "primary_targets": ["sleep_support", "stress_response", "calm"],
        "optional_support": ["anxiety_support"],
        "default_priority": ["dsip", "selank"],
        "phase_note": "Research scenario: limit stack complexity and prioritize clear sleep or stress endpoints over broad mixed-goal combinations.",
    },
    "endurance_performance": {
        "label": "Endurance / Performance",
        "primary_targets": ["exercise_tolerance", "mitochondrial_support", "metabolic_flexibility"],
        "optional_support": ["recovery", "lean_mass_support"],
        "default_priority": ["ss-31", "mots-c"],
        "phase_note": "Research scenario: prioritize exercise and mitochondrial objective fit, then test recovery adjuncts if rationale remains coherent.",
    },
    "metabolic_health": {
        "label": "Metabolic Health",
        "primary_targets": ["glycemic_support", "appetite_modulation", "metabolic_flexibility"],
        "optional_support": ["visceral_fat", "fat_loss_support"],
        "default_priority": ["retatrutide", "semaglutide"],
        "phase_note": "Research scenario: prioritize strongest glycemic and appetite evidence first, then evaluate narrower metabolic adjuncts.",
    },
}

SYMPTOM_CONDITION_MAP = {
    # ─── Metabolic / Weight Management ───
    "obesity": {
        "peptides": ["retatrutide", "semaglutide", "tirzepatide", "liraglutide", "cagrilintide"],
        "description": "Excess body fat accumulation. Incretin-based peptides (GLP-1/GIP/glucagon agonists) are the most studied class for significant weight reduction.",
        "category": "Metabolic/Weight Management",
    },
    "weight loss": {
        "peptides": ["retatrutide", "semaglutide", "tirzepatide", "liraglutide", "cagrilintide", "aod-9604", "mazdutide", "survodutide"],
        "description": "Reducing overall body weight through appetite suppression, metabolic acceleration, or fat breakdown signaling.",
        "category": "Metabolic/Weight Management",
    },
    "fat loss": {
        "peptides": ["retatrutide", "semaglutide", "tirzepatide", "tesamorelin", "aod-9604", "liraglutide", "mazdutide", "survodutide", "cagrilintide"],
        "description": "Reducing body fat stores. Multiple peptide classes target fat loss through distinct mechanisms including incretin signaling, GH-axis activation, and lipolysis.",
        "category": "Metabolic/Weight Management",
    },
    "belly fat": {
        "peptides": ["tesamorelin", "retatrutide", "semaglutide", "tirzepatide"],
        "description": "Visceral (deep belly) fat surrounding internal organs. Tesamorelin specifically targets visceral fat reduction through GH-axis signaling.",
        "category": "Metabolic/Weight Management",
    },
    "visceral fat": {
        "peptides": ["tesamorelin", "retatrutide"],
        "description": "Deep abdominal fat surrounding internal organs linked to metabolic disease. Tesamorelin has the most targeted evidence for visceral fat reduction.",
        "category": "Metabolic/Weight Management",
    },
    "diabetes": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "mazdutide"],
        "description": "Type 2 diabetes involves insulin resistance and elevated blood sugar. GLP-1 and dual GIP/GLP-1 agonists are FDA-approved for glycemic control.",
        "category": "Metabolic/Weight Management",
    },
    "type 2 diabetes": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "mazdutide"],
        "description": "Characterized by insulin resistance and relative insulin deficiency. Incretin-based therapies are first-line treatments in many guidelines.",
        "category": "Metabolic/Weight Management",
    },
    "insulin resistance": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "humanin"],
        "description": "Reduced cellular sensitivity to insulin leading to high blood sugar. Incretin therapies improve glycemic control; humanin has proposed insulin-sensitizing effects.",
        "category": "Metabolic/Weight Management",
    },
    "high blood sugar": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide"],
        "description": "Elevated glucose levels. GLP-1 agonists and dual/triple incretins improve glycemic control through insulin secretion and reduced glucagon.",
        "category": "Metabolic/Weight Management",
    },
    "prediabetes": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "aod-9604"],
        "description": "Blood sugar levels higher than normal but not yet diabetic. Early intervention with incretin therapies can prevent progression to type 2 diabetes.",
        "category": "Metabolic/Weight Management",
    },
    "metabolic syndrome": {
        "peptides": ["retatrutide", "semaglutide", "tirzepatide", "tesamorelin", "liraglutide", "mots-c", "mazdutide"],
        "description": "Cluster of conditions including high blood pressure, high blood sugar, excess body fat, and abnormal cholesterol. Multiple peptide classes address different components.",
        "category": "Metabolic/Weight Management",
    },
    "high cholesterol": {
        "peptides": ["retatrutide", "semaglutide", "tirzepatide"],
        "description": "Elevated lipid levels. GLP-1 and dual agonists show modest improvements in lipid profiles in clinical trials, though not their primary indication.",
        "category": "Metabolic/Weight Management",
    },
    "fatty liver": {
        "peptides": ["retatrutide", "survodutide", "mazdutide", "semaglutide", "tirzepatide"],
        "description": "NAFLD and MASH involve fat accumulation in the liver. Dual GLP-1/glucagon agonists like survodutide show particular promise for liver fat reduction.",
        "category": "Metabolic/Weight Management",
    },
    "nafld": {
        "peptides": ["retatrutide", "survodutide", "mazdutide", "semaglutide", "tirzepatide"],
        "description": "Non-alcoholic fatty liver disease. Glucagon-containing dual agonists target hepatic fat metabolism directly.",
        "category": "Metabolic/Weight Management",
    },
    "weight gain": {
        "peptides": ["retatrutide", "semaglutide", "tirzepatide", "liraglutide", "cagrilintide", "aod-9604"],
        "description": "Unwanted increase in body weight. Incretin therapies address appetite and metabolic rate for weight reduction.",
        "category": "Metabolic/Weight Management",
    },
    "overweight": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "cagrilintide"],
        "description": "BMI above healthy range. GLP-1 and dual/triple agonists are indicated for weight management in overweight individuals with related conditions.",
        "category": "Metabolic/Weight Management",
    },
    "appetite control": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "cagrilintide", "ghrp-6", "aod-9604"],
        "description": "Managing hunger and food intake. GLP-1 agonists slow gastric emptying and signal fullness to the brain. GHRP-6 notably increases appetite.",
        "category": "Metabolic/Weight Management",
    },
    "overeating": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "cagrilintide"],
        "description": "Excessive food consumption. Incretin-based therapies reduce appetite through multiple signaling pathways.",
        "category": "Metabolic/Weight Management",
    },
    "food cravings": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide"],
        "description": "Intense desires for specific foods. GLP-1 agonists reduce reward-driven eating by acting on brain reward centers.",
        "category": "Metabolic/Weight Management",
    },
    "slow metabolism": {
        "peptides": ["tesamorelin", "ipamorelin", "mk-677", "sermorelin", "mots-c", "aod-9604"],
        "description": "Reduced metabolic rate. GH-axis peptides and mitochondrial support peptides may help optimize metabolic function.",
        "category": "Metabolic/Weight Management",
    },
    "pcos": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "tesamorelin"],
        "description": "Polycystic ovary syndrome involves insulin resistance, metabolic dysfunction, and hormonal imbalance. Incretin therapies address the metabolic component.",
        "category": "Metabolic/Weight Management",
    },
    "stubborn fat": {
        "peptides": ["tesamorelin", "aod-9604", "retatrutide"],
        "description": "Fat deposits resistant to diet and exercise. Targeted GH-axis and lipolysis signaling may help mobilize stubborn fat stores.",
        "category": "Metabolic/Weight Management",
    },
    "abdominal obesity": {
        "peptides": ["tesamorelin", "retatrutide", "semaglutide", "tirzepatide"],
        "description": "Excess fat concentrated in the abdominal area. Tesamorelin specifically targets visceral adipose tissue.",
        "category": "Metabolic/Weight Management",
    },
    "hyperglycemia": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "mazdutide"],
        "description": "High blood glucose levels. Incretin therapies enhance insulin secretion and reduce glucagon release.",
        "category": "Metabolic/Weight Management",
    },
    "glycemic control": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "mazdutide"],
        "description": "Managing blood sugar levels within healthy range. Multiple incretin-based peptides are proven for glycemic management.",
        "category": "Metabolic/Weight Management",
    },
    "glucose intolerance": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "liraglutide", "mots-c"],
        "description": "Impaired ability to process glucose. Incretin therapies and mitochondrial peptides may improve glucose handling.",
        "category": "Metabolic/Weight Management",
    },
    "diabesity": {
        "peptides": ["retatrutide", "semaglutide", "tirzepatide", "liraglutide", "cagrilintide"],
        "description": "Co-occurring obesity and type 2 diabetes. Triple and dual incretin agonists address both conditions simultaneously through shared metabolic pathways.",
        "category": "Metabolic/Weight Management",
    },
    "lipodystrophy": {
        "peptides": ["tesamorelin", "ghk-cu"],
        "description": "Abnormal fat distribution or loss. Tesamorelin is FDA-approved for HIV-associated lipodystrophy to reduce visceral fat.",
        "category": "Metabolic/Weight Management",
    },
    "postpartum weight": {
        "peptides": ["aod-9604", "tesamorelin", "ipamorelin"],
        "description": "Weight retention after pregnancy. GH-axis peptides may support metabolic recovery, though safety during breastfeeding is not established.",
        "category": "Metabolic/Weight Management",
    },
    "menopause weight gain": {
        "peptides": ["tesamorelin", "retatrutide", "semaglutide", "tirzepatide", "aod-9604"],
        "description": "Weight gain associated with hormonal changes during menopause. Metabolic and GH-axis peptides may help counteract age-related metabolic slowing.",
        "category": "Metabolic/Weight Management",
    },
    # ─── Muscle / Performance ───
    "muscle gain": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "mk-677", "ghrp-2", "sermorelin", "igf-1-lr3", "igf-1-des", "follistatin-344", "peg-mgf", "hexarelin", "ghrp-6", "mots-c"],
        "description": "Building skeletal muscle mass. GH-axis peptides increase IGF-1 and protein synthesis signaling. IGF-1 analogs and myostatin inhibitors target anabolic pathways directly.",
        "category": "Muscle/Performance",
    },
    "lean mass": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "mk-677", "ghrp-2", "sermorelin", "igf-1-lr3", "follistatin-344", "peg-mgf"],
        "description": "Increasing lean body mass while minimizing fat gain. GH-axis peptides and anabolic signaling peptides support muscle protein synthesis.",
        "category": "Muscle/Performance",
    },
    "muscle mass": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "mk-677", "igf-1-lr3", "follistatin-344", "ghrp-2", "sermorelin"],
        "description": "Total body muscle tissue. Multiple peptide pathways can influence muscle protein balance through GH-IGF axis and myostatin regulation.",
        "category": "Muscle/Performance",
    },
    "strength": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "mk-677", "igf-1-lr3", "follistatin-344", "ghrp-2"],
        "description": "Muscular strength and power output. GH-axis peptides support the hormonal environment for strength gains from resistance training.",
        "category": "Muscle/Performance",
    },
    "muscle recovery": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "ipamorelin", "cjc-1295", "tesamorelin", "ss-31", "mk-677", "ghrp-2", "peg-mgf"],
        "description": "Post-exercise muscle repair and regeneration. Recovery peptides support tissue healing through multiple mechanisms including blood flow, collagen synthesis, and GH signaling.",
        "category": "Muscle/Performance",
    },
    "workout recovery": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "ss-31", "ipamorelin", "cjc-1295"],
        "description": "Faster return to baseline after exercise. Mitochondrial and tissue repair peptides support cellular recovery processes.",
        "category": "Muscle/Performance",
    },
    "muscle loss": {
        "peptides": ["tesamorelin", "ipamorelin", "mk-677", "cjc-1295", "follistatin-344", "sermorelin", "ghrp-2"],
        "description": "Preventing or treating sarcopenia and muscle wasting. GH-axis and myostatin-inhibiting peptides address age-related and pathological muscle loss.",
        "category": "Muscle/Performance",
    },
    "sarcopenia": {
        "peptides": ["mk-677", "tesamorelin", "ipamorelin", "sermorelin", "follistatin-344"],
        "description": "Age-related muscle loss. MK-677 has been studied specifically in elderly populations for muscle preservation and IGF-1 elevation.",
        "category": "Muscle/Performance",
    },
    "muscle wasting": {
        "peptides": ["tesamorelin", "ipamorelin", "mk-677", "follistatin-344", "sermorelin", "igf-1-lr3"],
        "description": "Pathological loss of muscle tissue from disease or disuse. Anabolic and anti-myostatin peptides may help preserve muscle mass.",
        "category": "Muscle/Performance",
    },
    "athletic performance": {
        "peptides": ["ss-31", "mots-c", "ipamorelin", "tesamorelin", "cjc-1295", "ghrp-2"],
        "description": "Sports and exercise performance enhancement. Mitochondrial peptides target energy production; GH-axis peptides support recovery and body composition.",
        "category": "Muscle/Performance",
    },
    "exercise performance": {
        "peptides": ["ss-31", "mots-c", "ipamorelin", "cjc-1295", "ghrp-2"],
        "description": "Capacity for physical exercise. Mitochondrial support peptides improve cellular energy production and exercise tolerance.",
        "category": "Muscle/Performance",
    },
    "endurance": {
        "peptides": ["ss-31", "mots-c", "aod-9604", "ipamorelin"],
        "description": "Sustained physical performance over time. Mitochondrial-targeted peptides support ATP production and metabolic efficiency.",
        "category": "Muscle/Performance",
    },
    "stamina": {
        "peptides": ["ss-31", "mots-c", "aod-9604"],
        "description": "Physical and mental energy reserves. Mitochondrial peptides improve cellular energy metabolism.",
        "category": "Muscle/Performance",
    },
    "bodybuilding": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "ghrp-2", "mk-677", "igf-1-lr3", "follistatin-344", "sermorelin", "hexarelin"],
        "description": "Muscle growth for physique development. GH-axis peptides are commonly used in bodybuilding for their anabolic and fat-burning effects.",
        "category": "Muscle/Performance",
    },
    "muscle preservation": {
        "peptides": ["tesamorelin", "ipamorelin", "mk-677", "follistatin-344", "sermorelin", "ghrp-2"],
        "description": "Maintaining existing muscle mass during caloric deficit or periods of inactivity. GH-axis peptides help offset catabolic states.",
        "category": "Muscle/Performance",
    },
    "protein synthesis": {
        "peptides": ["igf-1-lr3", "igf-1-des", "tesamorelin", "ipamorelin", "mk-677", "follistatin-344"],
        "description": "Cellular process of building proteins. IGF-1 analogs directly activate anabolic signaling pathways. GH-axis peptides increase endogenous IGF-1.",
        "category": "Muscle/Performance",
    },
    "myostatin inhibition": {
        "peptides": ["follistatin-344"],
        "description": "Blocking myostatin, a negative regulator of muscle growth. Follistatin binds myostatin, potentially allowing increased muscle development.",
        "category": "Muscle/Performance",
    },
    "muscle growth": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "mk-677", "igf-1-lr3", "follistatin-344", "ghrp-2", "sermorelin", "hexarelin", "peg-mgf"],
        "description": "Hypertrophy and hyperplasia of muscle tissue. Multiple signaling pathways including GH-IGF axis and myostatin regulation influence muscle growth.",
        "category": "Muscle/Performance",
    },
    "fitness": {
        "peptides": ["ss-31", "mots-c", "tesamorelin", "ipamorelin", "aod-9604"],
        "description": "General physical fitness and conditioning. Mitochondrial and metabolic peptides support energy, recovery, and body composition.",
        "category": "Muscle/Performance",
    },
    # ─── Anti-Aging / Longevity ───
    "anti-aging": {
        "peptides": ["ghk-cu", "epitalon", "humanin", "ss-31", "mots-c", "pinealon", "thymalin", "dsip", "tesamorelin", "ipamorelin", "mk-677", "aod-9604"],
        "description": "Reducing or slowing visible and physiological signs of aging. Multiple peptide classes target different aging hallmarks including mitochondrial decline, GH-axis attenuation, and cellular senescence.",
        "category": "Anti-Aging/Longevity",
    },
    "longevity": {
        "peptides": ["humanin", "ss-31", "epitalon", "mots-c", "ghk-cu"],
        "description": "Extending healthspan and lifespan. Mitochondrial and cytoprotective peptides target fundamental aging processes at the cellular level.",
        "category": "Anti-Aging/Longevity",
    },
    "aging": {
        "peptides": ["humanin", "ghk-cu", "ss-31", "epitalon", "mots-c", "tesamorelin", "pinealon"],
        "description": "Biological aging processes. Peptides targeting mitochondrial function, GH decline, and cellular repair may modulate age-related changes.",
        "category": "Anti-Aging/Longevity",
    },
    "cellular aging": {
        "peptides": ["humanin", "ss-31", "mots-c", "ghk-cu", "epitalon"],
        "description": "Age-related decline at the cellular level. Mitochondrial-derived peptides and repair peptides address cellular energy decline and oxidative stress.",
        "category": "Anti-Aging/Longevity",
    },
    "frailty": {
        "peptides": ["mk-677", "tesamorelin", "sermorelin", "ipamorelin", "ss-31", "mots-c"],
        "description": "Age-related physical vulnerability. GH-axis peptides have been studied in elderly populations for improving muscle mass and function.",
        "category": "Anti-Aging/Longevity",
    },
    "vitality": {
        "peptides": ["ss-31", "mots-c", "tesamorelin", "ipamorelin", "ghk-cu", "humanin", "dsip"],
        "description": "Overall energy, health, and well-being. Mitochondrial support and GH-axis peptides address fundamental drivers of vitality.",
        "category": "Anti-Aging/Longevity",
    },
    "energy decline": {
        "peptides": ["ss-31", "mots-c", "humanin", "aod-9604", "ghk-cu"],
        "description": "Age-related reduction in energy levels. Mitochondrial peptides support cellular energy production.",
        "category": "Anti-Aging/Longevity",
    },
    "age-related decline": {
        "peptides": ["mk-677", "tesamorelin", "ss-31", "humanin", "ghk-cu", "epitalon", "mots-c", "sermorelin"],
        "description": "General functional decline associated with aging. Multiple peptide classes address different aspects of age-related deterioration.",
        "category": "Anti-Aging/Longevity",
    },
    "healthy aging": {
        "peptides": ["humanin", "ss-31", "mots-c", "ghk-cu", "epitalon", "tesamorelin", "pinealon"],
        "description": "Promoting wellness and function in later years. Combination approaches targeting mitochondria, GH axis, and cellular repair show the broadest potential.",
        "category": "Anti-Aging/Longevity",
    },
    "healthspan": {
        "peptides": ["humanin", "ss-31", "mots-c", "epitalon", "ghk-cu"],
        "description": "The period of life spent in good health. Mitochondrial and cytoprotective peptides target fundamental aging mechanisms to extend healthspan.",
        "category": "Anti-Aging/Longevity",
    },
    "skin aging": {
        "peptides": ["ghk-cu", "melanotan-2", "bpc-157"],
        "description": "Age-related changes in skin including wrinkles, thinning, and loss of elasticity. GHK-Cu is the most studied peptide for skin anti-aging.",
        "category": "Anti-Aging/Longevity",
    },
    # ─── Cognitive / Neurological ───
    "focus": {
        "peptides": ["semax", "selank", "dihexa", "noopept"],
        "description": "Sustained attention and concentration. Semax increases BDNF, selank modulates anxiety for improved focus, dihexa promotes synaptogenesis.",
        "category": "Cognitive/Neurological",
    },
    "concentration": {
        "peptides": ["semax", "selank", "dihexa"],
        "description": "Ability to maintain attention on a task. Neurocognitive peptides support different aspects of concentration through BDNF and neurotransmitter modulation.",
        "category": "Cognitive/Neurological",
    },
    "brain fog": {
        "peptides": ["semax", "selank", "dihexa", "noopept", "bpc-157"],
        "description": "Mental cloudiness, lack of clarity, and cognitive sluggishness. Neurotropic peptides and anti-inflammatory peptides may help clear brain fog.",
        "category": "Cognitive/Neurological",
    },
    "memory": {
        "peptides": ["semax", "dihexa", "noopept", "selank"],
        "description": "Recall and retention of information. Semax and dihexa have shown memory-enhancing effects through BDNF and synaptic plasticity mechanisms.",
        "category": "Cognitive/Neurological",
    },
    "mental clarity": {
        "peptides": ["semax", "selank", "dihexa"],
        "description": "Clear thinking and sharp mental function. Peptide nootropics support cognitive function through neurotrophic and neuroplasticity mechanisms.",
        "category": "Cognitive/Neurological",
    },
    "cognitive function": {
        "peptides": ["semax", "selank", "dihexa", "noopept", "bpc-157", "epitalon"],
        "description": "General cognitive performance including thinking, learning, and memory. Multiple peptide classes support different cognitive domains.",
        "category": "Cognitive/Neurological",
    },
    "cognitive decline": {
        "peptides": ["semax", "dihexa", "noopept", "epitalon", "humanin", "bpc-157"],
        "description": "Age-related reduction in cognitive abilities. Neuroprotective and neuroplasticity-promoting peptides may help slow cognitive decline.",
        "category": "Cognitive/Neurological",
    },
    "adhd": {
        "peptides": ["semax", "selank", "noopept"],
        "description": "Attention deficit hyperactivity disorder. Focus-enhancing and anxiety-modulating peptides may help manage ADHD symptoms, though they are not FDA-approved for this indication.",
        "category": "Cognitive/Neurological",
    },
    "attention": {
        "peptides": ["semax", "selank", "dihexa"],
        "description": "Ability to selectively focus on relevant stimuli. Neuropeptides that modulate BDNF and neurotransmitter levels can support attention.",
        "category": "Cognitive/Neurological",
    },
    "mental performance": {
        "peptides": ["semax", "selank", "dihexa", "noopept", "bpc-157"],
        "description": "Peak cognitive output. Nootropic peptides support multiple cognitive domains through distinct mechanisms.",
        "category": "Cognitive/Neurological",
    },
    "learning": {
        "peptides": ["semax", "dihexa", "noopept", "selank"],
        "description": "Acquisition of new knowledge and skills. BDNF-enhancing peptides support neuroplasticity and learning capacity.",
        "category": "Cognitive/Neurological",
    },
    "neuroprotection": {
        "peptides": ["semax", "dihexa", "bpc-157", "epitalon", "humanin", "noopept"],
        "description": "Protection of neural tissue from damage. Multiple peptides have demonstrated neuroprotective properties through different mechanisms.",
        "category": "Cognitive/Neurological",
    },
    "alzheimer's": {
        "peptides": ["humanin", "semax", "dihexa", "epitalon", "bpc-157"],
        "description": "Progressive neurodegenerative disease. Humanin was discovered for its protective effect against Alzheimer's-related cell death. Other peptides may offer neuroprotective support.",
        "category": "Cognitive/Neurological",
    },
    "alzheimers": {
        "peptides": ["humanin", "semax", "dihexa", "epitalon", "bpc-157"],
        "description": "Progressive neurodegenerative condition. Research peptides are being investigated for neuroprotective and cognitive-supportive properties.",
        "category": "Cognitive/Neurological",
    },
    "dementia": {
        "peptides": ["humanin", "semax", "dihexa", "epitalon"],
        "description": "Cognitive decline severe enough to interfere with daily life. Neuroprotective peptides may support cognitive function in degenerative conditions.",
        "category": "Cognitive/Neurological",
    },
    "brain health": {
        "peptides": ["semax", "selank", "dihexa", "bpc-157", "epitalon", "humanin", "noopept"],
        "description": "Overall cognitive wellness and neurological function. Multiple peptides support different aspects of brain health through complementary mechanisms.",
        "category": "Cognitive/Neurological",
    },
    "neuroplasticity": {
        "peptides": ["semax", "dihexa", "noopept", "bpc-157"],
        "description": "The brain's ability to form new neural connections. Dihexa specifically promotes synaptogenesis; semax increases BDNF for enhanced plasticity.",
        "category": "Cognitive/Neurological",
    },
    "cognitive enhancement": {
        "peptides": ["semax", "selank", "dihexa", "noopept"],
        "description": "Improving cognitive abilities beyond baseline. Nootropic peptides target different cognitive domains through neurotrophic and neuromodulatory mechanisms.",
        "category": "Cognitive/Neurological",
    },
    "nootropic": {
        "peptides": ["semax", "selank", "dihexa", "noopept"],
        "description": "Cognitive-enhancing substances. These peptides are classified as nootropics based on their effects on memory, focus, and mental performance.",
        "category": "Cognitive/Neurological",
    },
    # ─── Anxiety / Calm / Sleep ───
    "anxiety": {
        "peptides": ["selank", "semax", "dsip", "ghk-cu", "kpv"],
        "description": "Feelings of worry, nervousness, or unease. Selank modulates serotonin and enkephalin systems for anxiolytic effects without sedation.",
        "category": "Anxiety/Calm/Sleep",
    },
    "stress": {
        "peptides": ["selank", "dsip", "semax", "kpv", "bpc-157", "ghk-cu"],
        "description": "Physical or mental tension from demanding circumstances. Peptides targeting HPA axis regulation and neurotransmitter balance can support stress resilience.",
        "category": "Anxiety/Calm/Sleep",
    },
    "calm": {
        "peptides": ["selank", "dsip", "kpv", "ghk-cu"],
        "description": "State of mental and physical relaxation. Selank provides calm without sedation through anxiolytic peptide mechanisms.",
        "category": "Anxiety/Calm/Sleep",
    },
    "relaxation": {
        "peptides": ["selank", "dsip", "ghk-cu", "kpv"],
        "description": "Mental and physical unwinding. Calming peptides support relaxation without the sedation associated with conventional anxiolytics.",
        "category": "Anxiety/Calm/Sleep",
    },
    "sleep": {
        "peptides": ["dsip", "pinealon", "selank", "ghk-cu", "kpv", "bpc-157"],
        "description": "Restorative sleep. DSIP specifically promotes delta wave activity for deep sleep. Pinealon supports circadian rhythm regulation.",
        "category": "Anxiety/Calm/Sleep",
    },
    "insomnia": {
        "peptides": ["dsip", "pinealon", "selank", "ghk-cu"],
        "description": "Difficulty falling or staying asleep. DSIP targets sleep architecture for deeper, more restorative rest without acting as a sedative.",
        "category": "Anxiety/Calm/Sleep",
    },
    "sleep quality": {
        "peptides": ["dsip", "pinealon", "selank", "kpv"],
        "description": "Depth and restorative nature of sleep. DSIP increases delta wave activity for more restorative deep sleep stages.",
        "category": "Anxiety/Calm/Sleep",
    },
    "deep sleep": {
        "peptides": ["dsip", "pinealon"],
        "description": "The most restorative stage of sleep. DSIP specifically promotes delta wave activity, the deepest stage of non-REM sleep.",
        "category": "Anxiety/Calm/Sleep",
    },
    "circadian rhythm": {
        "peptides": ["dsip", "pinealon", "epitalon"],
        "description": "The body's internal 24-hour clock. Pinealon and epitalon are proposed to support circadian regulation through pineal peptide signaling.",
        "category": "Anxiety/Calm/Sleep",
    },
    "mood": {
        "peptides": ["selank", "semax", "ghk-cu", "kpv", "bpc-157"],
        "description": "Emotional state and affect regulation. Neuropeptide modulators can influence mood through neurotransmitter and neurotrophic pathways.",
        "category": "Anxiety/Calm/Sleep",
    },
    "stress response": {
        "peptides": ["selank", "dsip", "semax", "kpv"],
        "description": "The body's reaction to stressors. Peptides targeting HPA axis function and neurotransmitter balance help modulate stress responses.",
        "category": "Anxiety/Calm/Sleep",
    },
    "cortisol": {
        "peptides": ["dsip", "selank", "kpv"],
        "description": "The primary stress hormone. DSIP has been shown to modulate cortisol and ACTH levels in research settings.",
        "category": "Anxiety/Calm/Sleep",
    },
    "sleep onset": {
        "peptides": ["dsip", "pinealon", "selank"],
        "description": "The ability to fall asleep. Calming peptides help facilitate the transition from wakefulness to sleep.",
        "category": "Anxiety/Calm/Sleep",
    },
    "nervousness": {
        "peptides": ["selank", "dsip", "kpv"],
        "description": "Feelings of apprehension or unease. Anxiolytic peptides provide calming effects without typical sedative side effects.",
        "category": "Anxiety/Calm/Sleep",
    },
    # ─── Injury / Healing / Recovery ───
    "injury recovery": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv", "thymosin-alpha-1", "aod-9604"],
        "description": "Healing from physical injuries. BPC-157 and TB-500 are the most discussed peptides for accelerating tissue repair through angiogenesis and collagen synthesis.",
        "category": "Injury/Healing/Recovery",
    },
    "tendon injury": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Damage to tendons connecting muscle to bone. BPC-157 has strong preclinical evidence for tendon healing through increased collagen production.",
        "category": "Injury/Healing/Recovery",
    },
    "ligament injury": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Damage to ligaments connecting bone to bone. Healing peptides support ligament repair through angiogenesis and extracellular matrix remodeling.",
        "category": "Injury/Healing/Recovery",
    },
    "muscle tear": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv", "igf-1-lr3", "peg-mgf"],
        "description": "Torn or strained muscle tissue. Repair peptides and growth factor analogs support muscle regeneration after injury.",
        "category": "Injury/Healing/Recovery",
    },
    "wound healing": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv", "thymosin-alpha-1"],
        "description": "Repair of skin and soft tissue wounds. GHK-Cu has strong clinical evidence for wound healing through collagen synthesis and angiogenesis.",
        "category": "Injury/Healing/Recovery",
    },
    "joint injury": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Damage to joint structures including cartilage, ligaments, and tendons. Healing peptides support the repair of multiple joint tissue types.",
        "category": "Injury/Healing/Recovery",
    },
    "back pain": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv", "selank"],
        "description": "Pain in the back often related to muscle, ligament, or disc issues. Healing peptides support tissue repair; selank offers anxiolytic pain modulation.",
        "category": "Injury/Healing/Recovery",
    },
    "sports injury": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv", "igf-1-lr3", "peg-mgf"],
        "description": "Athletic-related tissue damage. Recovery peptides are commonly used in research settings for accelerated return from sports injuries.",
        "category": "Injury/Healing/Recovery",
    },
    "post-surgery": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv", "thymosin-alpha-1", "ipamorelin"],
        "description": "Recovery after surgical procedures. Healing and immune-supporting peptides may help accelerate post-surgical tissue repair and reduce recovery time.",
        "category": "Injury/Healing/Recovery",
    },
    "surgical recovery": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "thymosin-alpha-1", "ipamorelin"],
        "description": "Healing and recuperation after surgery. Multiple peptide classes support different aspects of post-surgical recovery.",
        "category": "Injury/Healing/Recovery",
    },
    "soft tissue injury": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Damage to muscles, tendons, or ligaments. Healing peptides promote angiogenesis and collagen deposition in damaged soft tissues.",
        "category": "Injury/Healing/Recovery",
    },
    "tendonitis": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu"],
        "description": "Inflammation of a tendon. BPC-157 and TB-500 target both the inflammatory component and the tissue repair process.",
        "category": "Injury/Healing/Recovery",
    },
    "fracture healing": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Bone repair after fracture. Angiogenesis-promoting peptides support blood vessel growth into healing bone tissue.",
        "category": "Injury/Healing/Recovery",
    },
    "connective tissue": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Supporting and repairing connective tissues throughout the body. GHK-Cu and BPC-157 promote collagen synthesis and tissue integrity.",
        "category": "Injury/Healing/Recovery",
    },
    "collagen": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500"],
        "description": "The primary structural protein in connective tissue. GHK-Cu is well-documented to stimulate collagen production in skin and connective tissues.",
        "category": "Injury/Healing/Recovery",
    },
    "scar tissue": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500"],
        "description": "Fibrous tissue replacing normal tissue after injury. Remodeling peptides may help improve scar quality through collagen modulation.",
        "category": "Injury/Healing/Recovery",
    },
    "chronic pain": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "selank", "kpv"],
        "description": "Persistent pain lasting beyond normal healing time. Anti-inflammatory and tissue-repair peptides address underlying causes of chronic pain.",
        "category": "Injury/Healing/Recovery",
    },
    "joint pain": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Pain in articular joints. Healing peptides target tissue repair and inflammation in joint structures.",
        "category": "Injury/Healing/Recovery",
    },
    "arthritis": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Joint inflammation and degeneration. Peptides with anti-inflammatory and tissue-repair properties may support joint health in arthritic conditions.",
        "category": "Injury/Healing/Recovery",
    },
    # ─── Immune / Inflammation ───
    "immune support": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon", "kpv", "ghk-cu", "bpc-157"],
        "description": "Supporting the body's immune defense system. Thymic peptides modulate immune function through T-cell maturation and activity.",
        "category": "Immune/Inflammation",
    },
    "immune system": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon", "kpv", "ghk-cu"],
        "description": "The body's defense network against pathogens. Thymic peptides support immune cell development and function.",
        "category": "Immune/Inflammation",
    },
    "autoimmune": {
        "peptides": ["kpv", "thymosin-alpha-1", "selank", "bpc-157"],
        "description": "Conditions where the immune system attacks the body's own tissues. Immunomodulatory peptides may help regulate immune responses.",
        "category": "Immune/Inflammation",
    },
    "chronic inflammation": {
        "peptides": ["kpv", "bpc-157", "ghk-cu", "tb-500", "selank"],
        "description": "Persistent low-grade inflammation throughout the body. Anti-inflammatory peptides target different inflammatory pathways.",
        "category": "Immune/Inflammation",
    },
    "infection": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon"],
        "description": "Invasion of the body by pathogens. Thymic peptides support immune cell activity against infections, studied in hepatitis and vaccine response contexts.",
        "category": "Immune/Inflammation",
    },
    "immune modulation": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon", "kpv", "ghk-cu"],
        "description": "Regulating immune system activity. Thymic peptides and anti-inflammatory peptides modulate rather than simply stimulate immune function.",
        "category": "Immune/Inflammation",
    },
    "t-cells": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon"],
        "description": "Critical immune cells responsible for adaptive immunity. Thymic peptides support T-cell maturation, differentiation, and activity.",
        "category": "Immune/Inflammation",
    },
    "thymus": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon"],
        "description": "The gland responsible for T-cell maturation. Thymic peptides support thymus function and are named for their thymus-derived origins.",
        "category": "Immune/Inflammation",
    },
    "immunity": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon", "kpv", "ghk-cu"],
        "description": "Resistance to infection and disease. Thymic peptides and immunomodulatory peptides support overall immune competence.",
        "category": "Immune/Inflammation",
    },
    "frequent colds": {
        "peptides": ["thymosin-alpha-1", "thymulin", "vilon"],
        "description": "Recurrent upper respiratory infections. Immune-supporting thymic peptides may help reduce infection frequency.",
        "category": "Immune/Inflammation",
    },
    "inflammatory": {
        "peptides": ["kpv", "bpc-157", "ghk-cu", "tb-500", "selank"],
        "description": "Conditions involving inflammation. Multiple peptides with anti-inflammatory properties can target different inflammatory mediators.",
        "category": "Immune/Inflammation",
    },
    # ─── GI / Gut Repair ───
    "gut health": {
        "peptides": ["bpc-157", "kpv", "ghk-cu", "thymosin-alpha-1"],
        "description": "Digestive system wellness and function. BPC-157 has the strongest preclinical evidence for gastrointestinal healing and gut barrier repair.",
        "category": "GI/Gut Repair",
    },
    "leaky gut": {
        "peptides": ["bpc-157", "kpv", "ghk-cu"],
        "description": "Increased intestinal permeability. BPC-157 promotes gut barrier integrity through angiogenesis and tight junction regulation in the intestinal lining.",
        "category": "GI/Gut Repair",
    },
    "ibs": {
        "peptides": ["bpc-157", "kpv", "ghk-cu"],
        "description": "Irritable bowel syndrome. BPC-157 has been studied in animal models for reducing intestinal inflammation and normalizing gut motility.",
        "category": "GI/Gut Repair",
    },
    "irritable bowel": {
        "peptides": ["bpc-157", "kpv"],
        "description": "Functional bowel disorder with abdominal pain and altered bowel habits. Gut-healing peptides may support intestinal barrier function.",
        "category": "GI/Gut Repair",
    },
    "crohn's": {
        "peptides": ["bpc-157", "kpv", "thymosin-alpha-1"],
        "description": "Inflammatory bowel disease affecting the digestive tract. BPC-157 has shown protective effects in animal models of intestinal inflammation.",
        "category": "GI/Gut Repair",
    },
    "crohns": {
        "peptides": ["bpc-157", "kpv", "thymosin-alpha-1"],
        "description": "Chronic inflammatory bowel condition. Gut-healing and immunomodulatory peptides may support intestinal health in inflammatory conditions.",
        "category": "GI/Gut Repair",
    },
    "ulcerative colitis": {
        "peptides": ["bpc-157", "kpv", "thymosin-alpha-1"],
        "description": "Inflammatory bowel disease of the colon. BPC-157 has demonstrated protective effects in colitis animal models.",
        "category": "GI/Gut Repair",
    },
    "ibd": {
        "peptides": ["bpc-157", "kpv", "thymosin-alpha-1"],
        "description": "Inflammatory bowel disease. Gut-healing and immunomodulatory peptides target both the inflammatory and tissue-repair aspects of IBD.",
        "category": "GI/Gut Repair",
    },
    "gut healing": {
        "peptides": ["bpc-157", "kpv", "ghk-cu"],
        "description": "Repair of the gastrointestinal lining. BPC-157 is the most studied peptide for gastrointestinal tissue repair and barrier function.",
        "category": "GI/Gut Repair",
    },
    "intestinal permeability": {
        "peptides": ["bpc-157", "kpv"],
        "description": "Increased leakiness of the gut barrier. BPC-157 promotes tight junction integrity and mucosal healing in the intestinal wall.",
        "category": "GI/Gut Repair",
    },
    "stomach ulcer": {
        "peptides": ["bpc-157"],
        "description": "Open sores in the stomach lining. BPC-157 has strong preclinical evidence for accelerating gastric ulcer healing through angiogenesis and growth factor upregulation.",
        "category": "GI/Gut Repair",
    },
    "digestive health": {
        "peptides": ["bpc-157", "kpv", "ghk-cu"],
        "description": "Overall digestive system function. Gut-healing peptides support intestinal integrity and digestive wellness.",
        "category": "GI/Gut Repair",
    },
    "gastritis": {
        "peptides": ["bpc-157", "kpv"],
        "description": "Inflammation of the stomach lining. BPC-157 has shown gastroprotective and anti-inflammatory effects in the gastric mucosa.",
        "category": "GI/Gut Repair",
    },
    # ─── Skin / Hair ───
    "skin health": {
        "peptides": ["ghk-cu", "melanotan-2", "bpc-157", "tb-500", "ghk-cu"],
        "description": "Overall skin condition and appearance. GHK-Cu is well-documented for skin rejuvenation, collagen synthesis, and wound healing.",
        "category": "Skin/Hair",
    },
    "wrinkles": {
        "peptides": ["ghk-cu", "ghk-cu"],
        "description": "Skin folds and creases from aging. GHK-Cu stimulates collagen production and skin remodeling to reduce wrinkle depth.",
        "category": "Skin/Hair",
    },
    "collagen production": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500"],
        "description": "Synthesis of collagen, the main structural skin protein. GHK-Cu is one of the most studied peptides for stimulating collagen production.",
        "category": "Skin/Hair",
    },
    "skin elasticity": {
        "peptides": ["ghk-cu", "ghk-cu"],
        "description": "The skin's ability to stretch and return to shape. GHK-Cu supports skin matrix remodeling for improved firmness and elasticity.",
        "category": "Skin/Hair",
    },
    "hair growth": {
        "peptides": ["ghk-cu", "bpc-157", "melanotan-2"],
        "description": "Stimulation of hair follicle activity. GHK-Cu is studied for hair growth through improved blood flow and follicle health.",
        "category": "Skin/Hair",
    },
    "hair fall": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500", "melanotan-2"],
        "description": "Thinning or loss of hair (alopecia). GHK-Cu, BPC-157, and TB-500 have been studied for hair follicle angiogenesis and regeneration support.",
        "category": "Skin/Hair",
    },
    "hair loss": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500", "melanotan-2"],
        "description": "Thinning or loss of hair (alopecia). Copper peptides have been studied for hair follicle support, angiogenesis, and potential regrowth stimulation through improved scalp blood flow and reduced inflammation.",
        "category": "Skin/Hair",
    },
    "androgenic alopecia": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500"],
        "description": "Hormonal hair loss driven by DHT sensitivity. Peptides like GHK-Cu support follicle health through improved blood supply and reduced inflammation, while BPC-157 may aid tissue repair in the scalp. These do not block DHT but support follicle environment.",
        "category": "Skin/Hair",
    },
    "skin regeneration": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500", "kpv"],
        "description": "Renewal and repair of skin tissue. Multiple peptides support different aspects of skin regeneration through collagen production, angiogenesis, and cell migration.",
        "category": "Skin/Hair",
    },
    "skin firmness": {
        "peptides": ["ghk-cu"],
        "description": "Skin tightness and resistance to sagging. GHK-Cu supports collagen and elastin production for improved skin firmness.",
        "category": "Skin/Hair",
    },
    "tanning": {
        "peptides": ["melanotan-2", "ghk-cu"],
        "description": "Skin pigmentation through melanin production. Melanotan II stimulates melanocortin receptors for increased melanin synthesis and UV-independent tanning.",
        "category": "Skin/Hair",
    },
    # ─── Bone / Joint / Connective Tissue ───
    "osteoporosis": {
        "peptides": ["ghk-cu", "bpc-157", "tb-500", "mk-677"],
        "description": "Reduced bone density and increased fracture risk. GHK-Cu supports bone remodeling; MK-677 has been studied for bone turnover in elderly populations.",
        "category": "Bone/Joint/Connective Tissue",
    },
    "bone density": {
        "peptides": ["ghk-cu", "mk-677", "bpc-157"],
        "description": "Bone mineral content and structural strength. Peptides supporting collagen synthesis and GH signaling may influence bone metabolism.",
        "category": "Bone/Joint/Connective Tissue",
    },
    "joint health": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Joint structure and function. Healing and anti-inflammatory peptides support joint tissue integrity and repair.",
        "category": "Bone/Joint/Connective Tissue",
    },
    "cartilage": {
        "peptides": ["bpc-157", "ghk-cu", "tb-500"],
        "description": "Flexible connective tissue cushioning joints. Repair peptides may support cartilage matrix maintenance through collagen and proteoglycan synthesis.",
        "category": "Bone/Joint/Connective Tissue",
    },
    "connective tissue repair": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Repair of ligaments, tendons, and fascia. Healing peptides promote collagen synthesis and angiogenesis for connective tissue regeneration.",
        "category": "Bone/Joint/Connective Tissue",
    },
    "ligament healing": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu"],
        "description": "Repair of torn or damaged ligaments. BPC-157 and TB-500 support ligament healing through improved blood flow and collagen alignment.",
        "category": "Bone/Joint/Connective Tissue",
    },
    "tendon healing": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu"],
        "description": "Repair of tendon injuries. BPC-157 has preclinical evidence for accelerating tendon healing through increased collagen production.",
        "category": "Bone/Joint/Connective Tissue",
    },
    "osteoarthritis": {
        "peptides": ["bpc-157", "tb-500", "ghk-cu", "kpv"],
        "description": "Degenerative joint disease. Anti-inflammatory and tissue-repair peptides may support joint health in osteoarthritis.",
        "category": "Bone/Joint/Connective Tissue",
    },
    # ─── Cardiovascular / Pulmonary ───
    "heart health": {
        "peptides": ["ss-31", "humanin", "mots-c", "ghk-cu", "bpc-157"],
        "description": "Cardiovascular system wellness. SS-31 has been studied in heart failure; humanin offers cardioprotective effects in preclinical models.",
        "category": "Cardiovascular/Pulmonary",
    },
    "blood pressure": {
        "peptides": ["semaglutide", "tirzepatide", "retatrutide", "bpc-157"],
        "description": "Arterial blood pressure levels. Weight loss from incretin therapies often improves blood pressure. BPC-157 has shown blood pressure modulation in animal studies.",
        "category": "Cardiovascular/Pulmonary",
    },
    "cardiovascular": {
        "peptides": ["ss-31", "humanin", "mots-c", "ghk-cu", "bpc-157"],
        "description": "Heart and blood vessel health. Mitochondrial-targeted peptides support cardiac energy metabolism; incretin therapies improve cardiovascular risk factors.",
        "category": "Cardiovascular/Pulmonary",
    },
    "heart disease": {
        "peptides": ["ss-31", "humanin", "bpc-157"],
        "description": "Conditions affecting the heart. SS-31 has clinical trial data in heart failure. Humanin shows cardioprotective effects in preclinical models.",
        "category": "Cardiovascular/Pulmonary",
    },
    "heart failure": {
        "peptides": ["ss-31", "humanin"],
        "description": "Reduced cardiac pumping capacity. SS-31 (elamipretide) has been studied in clinical trials for heart failure with preserved ejection fraction.",
        "category": "Cardiovascular/Pulmonary",
    },
    "exercise tolerance": {
        "peptides": ["ss-31", "mots-c", "aod-9604"],
        "description": "Capacity for physical exertion. SS-31 has shown improved exercise tolerance in clinical studies of mitochondrial dysfunction.",
        "category": "Cardiovascular/Pulmonary",
    },
    "vascular health": {
        "peptides": ["ss-31", "humanin", "bpc-157", "ghk-cu"],
        "description": "Blood vessel function and integrity. Angiogenic and mitochondrial peptides support different aspects of vascular health.",
        "category": "Cardiovascular/Pulmonary",
    },
    # ─── Sexual / Reproductive ───
    "low libido": {
        "peptides": ["pt-141", "kisspeptin-10", "melanotan-2"],
        "description": "Reduced sexual desire. PT-141 (bremelanotide) is FDA-approved for hypoactive sexual desire disorder. Kisspeptin-10 modulates reproductive hormone signaling.",
        "category": "Sexual/Reproductive",
    },
    "sexual desire": {
        "peptides": ["pt-141", "kisspeptin-10", "melanotan-2"],
        "description": "Interest in sexual activity. PT-141 activates melanocortin receptors in the brain's reward and desire pathways.",
        "category": "Sexual/Reproductive",
    },
    "erectile dysfunction": {
        "peptides": ["pt-141", "kisspeptin-10", "melanotan-2"],
        "description": "Difficulty achieving or maintaining erections. PT-141 is used off-label for ED through central melanocortin activation rather than vascular mechanisms.",
        "category": "Sexual/Reproductive",
    },
    "sexual arousal": {
        "peptides": ["pt-141", "kisspeptin-10", "melanotan-2"],
        "description": "Physiological and psychological sexual response. PT-141 directly activates central pathways involved in sexual arousal.",
        "category": "Sexual/Reproductive",
    },
    "hsdd": {
        "peptides": ["pt-141"],
        "description": "Hypoactive sexual desire disorder. PT-141 (bremelanotide/Vyleesi) is FDA-approved specifically for HSDD in premenopausal women.",
        "category": "Sexual/Reproductive",
    },
    "fertility": {
        "peptides": ["kisspeptin-10", "ghrp-6", "pt-141"],
        "description": "Reproductive capacity. Kisspeptin-10 stimulates GnRH release and has been studied for reproductive hormone modulation.",
        "category": "Sexual/Reproductive",
    },
    "testosterone": {
        "peptides": ["kisspeptin-10", "pt-141", "tesamorelin", "ipamorelin"],
        "description": "Primary male sex hormone. Kisspeptin-10 stimulates LH release which signals testosterone production. GH-axis peptides support the hormonal environment.",
        "category": "Sexual/Reproductive",
    },
    "hormonal imbalance": {
        "peptides": ["kisspeptin-10", "tesamorelin", "pt-141", "ghrp-6"],
        "description": "Disruption in normal hormone levels. Peptides modulating the HPG and GH axes may help address certain hormonal imbalances.",
        "category": "Sexual/Reproductive",
    },
    # ─── Hormonal / GH Optimization ───
    "growth hormone": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "sermorelin", "mk-677", "ghrp-2", "ghrp-6", "hexarelin", "aod-9604"],
        "description": "Increasing endogenous growth hormone production. GHRH analogs and GH secretagogues stimulate pituitary GH release through complementary mechanisms.",
        "category": "Hormonal/GH Optimization",
    },
    "gh deficiency": {
        "peptides": ["tesamorelin", "sermorelin", "cjc-1295", "mk-677", "ghrp-2", "ipamorelin"],
        "description": "Insufficient growth hormone production. GHRH analogs like tesamorelin and sermorelin have clinical data for GH deficiency indications.",
        "category": "Hormonal/GH Optimization",
    },
    "igf-1": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "mk-677", "sermorelin", "ghrp-2", "igf-1-lr3", "hexarelin"],
        "description": "Insulin-like growth factor 1 levels. GH-axis peptides increase endogenous IGF-1 production. IGF-1 LR3 provides direct receptor activation.",
        "category": "Hormonal/GH Optimization",
    },
    "hgh": {
        "peptides": ["tesamorelin", "ipamorelin", "cjc-1295", "sermorelin", "mk-677", "ghrp-2", "ghrp-6", "hexarelin"],
        "description": "Human growth hormone signaling. GHRH analogs and GH secretagogues stimulate the body's own GH production rather than providing exogenous HGH.",
        "category": "Hormonal/GH Optimization",
    },
    "hormone optimization": {
        "peptides": ["tesamorelin", "ipamorelin", "kisspeptin-10", "mk-677", "sermorelin", "cjc-1295"],
        "description": "Balancing and optimizing hormone levels. GH-axis and reproductive hormone-modulating peptides support endocrine function.",
        "category": "Hormonal/GH Optimization",
    },
    "pituitary": {
        "peptides": ["tesamorelin", "sermorelin", "cjc-1295", "ghrp-2", "ipamorelin"],
        "description": "The master endocrine gland. GHRH analogs directly stimulate the pituitary to release growth hormone in natural pulsatile patterns.",
        "category": "Hormonal/GH Optimization",
    },
    # ─── Mitochondrial / Energy ───
    "low energy": {
        "peptides": ["ss-31", "mots-c", "humanin", "aod-9604", "ghk-cu"],
        "description": "Insufficient physical or mental energy. Mitochondrial peptides target cellular energy production at the mitochondrial level.",
        "category": "Mitochondrial/Energy",
    },
    "fatigue": {
        "peptides": ["ss-31", "mots-c", "humanin", "aod-9604", "dsip", "ghk-cu"],
        "description": "Persistent tiredness or exhaustion. Mitochondrial peptides address cellular energy; DSIP supports restorative sleep for fatigue recovery.",
        "category": "Mitochondrial/Energy",
    },
    "mitochondrial function": {
        "peptides": ["ss-31", "mots-c", "humanin", "ghk-cu"],
        "description": "Cellular energy production efficiency. SS-31 targets the inner mitochondrial membrane; MOTS-c regulates metabolic signaling from mitochondria.",
        "category": "Mitochondrial/Energy",
    },
    "cellular energy": {
        "peptides": ["ss-31", "mots-c", "humanin", "ghk-cu"],
        "description": "ATP production at the cellular level. Mitochondrial-targeted peptides optimize electron transport chain efficiency and reduce oxidative stress.",
        "category": "Mitochondrial/Energy",
    },
    "chronic fatigue": {
        "peptides": ["ss-31", "mots-c", "humanin", "dsip"],
        "description": "Persistent, unexplained exhaustion. Mitochondrial peptides target the cellular energy deficit that may underlie chronic fatigue.",
        "category": "Mitochondrial/Energy",
    },
    "energy levels": {
        "peptides": ["ss-31", "mots-c", "humanin", "aod-9604", "ghk-cu"],
        "description": "Overall daily energy and vitality. Mitochondrial support peptides optimize the cellular machinery responsible for energy production.",
        "category": "Mitochondrial/Energy",
    },
    "metabolic flexibility": {
        "peptides": ["mots-c", "ss-31", "aod-9604", "humanin"],
        "description": "The ability to switch between fuel sources. MOTS-c regulates metabolic transitions between glucose and fat utilization.",
        "category": "Mitochondrial/Energy",
    },
    # ─── General ───
    "hot flashes": {
        "peptides": ["kisspeptin-10", "melanotan-2", "tesamorelin", "selank"],
        "description": "Sudden sensations of warmth often associated with hormonal changes. Kisspeptin-10 modulates reproductive hormone signaling involved in temperature regulation.",
        "category": "Hormonal/GH Optimization",
    },
    "menopause": {
        "peptides": ["kisspeptin-10", "tesamorelin", "aod-9604", "ghk-cu", "dsip"],
        "description": "The natural end of menstrual cycles. Peptides addressing hormonal, metabolic, and sleep changes may support women during menopausal transition.",
        "category": "Hormonal/GH Optimization",
    },
}

COMMUNITY_NOTES = {
    "retatrutide+tesamorelin": "Community discussions often pair incretin-based fat-loss signals with GH-axis body-composition goals; this is anecdotal and must be validated against trial evidence.",
    "retatrutide+tesamorelin+ipamorelin": "Forum protocols sometimes phase GH-axis adjuncts after initial response period; evidence quality is lower than controlled trials.",
    "semax+selank": "Community reports commonly describe focus/calm pairing; classify as anecdotal unless stronger controlled evidence is available.",
    "melanotan-2+ghk-cu": "Community discussions often pair tanning-focused protocols with skin-quality support peptides; this remains anecdotal.",
    "ghk-cu+tb-500": "Repair-focused communities frequently combine these as a recovery protocol, with limited controlled clinical validation.",
    "dsip+selank": "Sleep and calm pairings are discussed in anecdotal protocol threads and should be weighted below trial-grade evidence.",
    "ss-31+mots-c": "Performance communities may combine mitochondrial and metabolic flexibility signals; controlled comparative evidence is limited.",
}


def normalize_term(term):
    key = term.strip().lower()
    return ALIASES.get(key, key)


def fetch_json(url, headers=None, data=None, timeout=8):
    try:
        req = Request(url, data=data, headers=headers or {"User-Agent": "peptide-wiki/1.0"})
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def source_status(wiki, trials, pubmed, fda_data, pubchem=None, rcsb=None, uniprot=None):
    return {
        "wikipedia": bool(wiki and wiki.get("summary")),
        "clinicaltrials": bool(trials),
        "pubmed": bool(pubmed),
        "openfda": bool(fda_data),
        "pubchem": bool(pubchem),
        "rcsb_pdb": bool(rcsb),
        "uniprot": bool(uniprot),
    }


def fetch_pubchem(term):
    endpoint = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(term)}/JSON"
    data = fetch_json(endpoint)
    if not data:
        return None
    props = data.get("PC_Compounds", [{}])[0].get("props", [])
    result = {}
    for p in props:
        label = p.get("urn", {}).get("label", "")
        value = p.get("value", {}).get("sval", "")
        if label == "Molecular Weight":
            result["molecular_weight"] = value
        elif label == "Molecular Formula":
            result["formula"] = value
        elif label == "IUPAC Name":
            result["iupac"] = value
        elif label == "Log P":
            result["log_p"] = value
        elif label == "Hydrogen Bond Donor Count":
            result["h_bond_donors"] = value
        elif label == "Hydrogen Bond Acceptor Count":
            result["h_bond_acceptors"] = value
        if len(result) >= 5:
            break
    return result if result else None


def fetch_rcsb_pdb(term):
    query = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [{
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": term}
            }]
        },
        "return_type": "entry",
        "rows": 3
    }
    data = fetch_json("https://search.rcsb.org/rcsbsearch/v2/query", {
        "User-Agent": "peptide-wiki/1.0",
        "Content-Type": "application/json",
    }, data=json.dumps(query).encode())
    if not data:
        return None
    hits = data.get("result_set", [])
    if not hits:
        return None
    structures = []
    for hit in hits[:3]:
        pdb_id = hit.get("identifier", "")
        if pdb_id:
            structures.append({
                "pdb_id": pdb_id,
                "url": f"https://www.rcsb.org/structure/{pdb_id}",
            })
    return structures if structures else None


def fetch_uniprot(term):
    url = f"https://rest.uniprot.org/uniprotkb/search?query={quote(term)}&format=json&size=1"
    data = fetch_json(url, {"User-Agent": "peptide-wiki/1.0"})
    if not data or not data.get("results"):
        return None
    entry = data["results"][0]
    result = {
        "accession": entry.get("primaryAccession"),
        "id": entry.get("uniProtkbId"),
        "protein_name": entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
        "gene": entry.get("genes", [{}])[0].get("geneName", {}).get("value"),
    }
    for comment in entry.get("comments", []):
        ctype = comment.get("commentType")
        if ctype == "FUNCTION":
            texts = comment.get("texts", [])
            if texts:
                result["function"] = texts[0].get("value")
        elif ctype == "PHARMACEUTICAL":
            texts = comment.get("texts", [])
            if texts:
                result["pharmaceutical"] = texts[0].get("value")
        elif ctype == "BIOTECHNOLOGY":
            texts = comment.get("texts", [])
            if texts:
                result["biotechnology"] = texts[0].get("value")
        elif ctype == "DISEASE":
            diseases = []
            disease_data = comment.get("disease")
            if disease_data:
                if isinstance(disease_data, list):
                    for d in disease_data:
                        if isinstance(d, dict) and "diseaseId" in d:
                            diseases.append(d["diseaseId"])
                elif isinstance(disease_data, dict) and "diseaseId" in disease_data:
                    diseases.append(disease_data["diseaseId"])
            result["diseases"] = diseases
    result["keywords"] = [kw.get("name") for kw in entry.get("keywords", [])]
    return result


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


@lru_cache(maxsize=128)
def fetch_clinical_trials(term):
    # Use condition + title search for relevance — avoid loose full-text matches
    endpoint = f"https://clinicaltrials.gov/api/v2/studies?query.term={quote(term)}&pageSize=20&filter.overallStatus=NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED,TERMINATED"
    data = fetch_json(endpoint)
    if not data:
        return []
    studies = data.get("studies", [])
    results = []
    term_lower = term.lower()
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


@lru_cache(maxsize=128)
def fetch_pubmed(term):
    query = f"({term}[Title/Abstract]) AND (peptide[Title/Abstract] OR ({term}[MeSH Terms]))"
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=15&sort=relevance&term={quote(query)}"
    search_data = fetch_json(search_url)
    if not search_data:
        return []
    ids = search_data.get("esearchresult", {}).get("idlist", [])
    papers = []
    term_lower = term.lower()
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


def tier_points(tier):
    return {"A": 24, "B": 18, "C": 10, "D": 4}.get(tier, 2)


def build_peptide_evidence(pep):
    term = quote(pep)
    return {
        "peptide": pep,
        "clinicaltrials_url": f"https://clinicaltrials.gov/search?term={term}",
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/?term={term}",
    }


def describe_effect(effect):
    labels = {
        "fat_loss": "fat-mass reduction pressure",
        "glycemic_support": "glucose-control and insulin-signaling support",
        "appetite_modulation": "central appetite modulation",
        "visceral_fat": "visceral adiposity targeting",
        "gh_axis": "growth-hormone and IGF-1 axis signaling",
        "body_composition": "body-composition repartitioning",
        "lean_mass_support": "lean-mass retention and support",
        "recovery": "recovery and tissue-repair support",
        "metabolic_flexibility": "substrate-use and metabolic flexibility",
        "focus": "attentional focus signaling",
        "stress_response": "stress-response regulation",
        "calm": "calm/anxiolytic signaling",
        "anxiety_support": "anxiety-load reduction support",
        "tanning_support": "melanocortin-linked pigmentation signaling",
        "uv_response": "UV-response adaptation",
        "skin_quality": "skin remodeling support",
        "healing_support": "healing cascade support",
        "connective_tissue_support": "connective tissue remodeling support",
        "fat_loss_support": "adjunct fat-loss signaling",
        "sleep_support": "sleep architecture support",
        "mitochondrial_support": "mitochondrial energetic support",
        "exercise_tolerance": "exercise tolerance signaling",
        "inflammation_hypothesis": "inflammation-related exploratory signaling",
        "ghrelin_axis": "ghrelin-receptor growth-hormone secretagogue signaling",
        "sexual_function": "sexual-function and arousal signaling",
        "thymic_support": "thymic and adaptive-immune support",
        "igf_signaling": "direct IGF-1 receptor activation signaling",
        "myostatin_inhibition": "myostatin-inhibition and muscle-growth signaling",
    }
    return labels.get(effect, effect.replace("_", " "))


def build_stack_deep_research(goal, unique_stack):
    pathways = []
    mechanism_map = []
    synergy_analysis = []
    neuroplasticity_notes = []
    risk_profile = []
    evidence_gaps = []
    risk_flags = []

    for pep in unique_stack:
        meta = STACK_KNOWLEDGE.get(pep, {})
        effects = meta.get("effects", [])
        tier = meta.get("tier", "D")
        pathways.append(
            {
                "peptide": pep,
                "targets": [describe_effect(e) for e in effects],
                "pathway_focus": [e for e in effects],
            }
        )
        mechanism_map.append(
            {
                "peptide": pep,
                "what_it_does": meta.get("summary", "No summary available."),
                "how_it_does_it": "Primary action is inferred from effect-cluster alignment and current evidence tier.",
                "why_it_does_it": "Expected outcomes are driven by receptor-level or signaling-pathway modulation represented by the mapped effect set.",
                "targets": [describe_effect(e) for e in effects],
                "pathways": effects,
                "evidence_tier": tier,
            }
        )
        if "focus" in effects or "stress_response" in effects or "calm" in effects or "sleep_support" in effects:
            neuroplasticity_notes.append(
                {
                    "peptide": pep,
                    "note": "Neurocognitive and stress-regulation hypotheses may involve synaptic signaling adaptation and neurotrophic-pathway interaction, but certainty is limited by trial depth.",
                    "confidence": "LIMITED" if tier in ["C", "D"] else "MODERATE",
                }
            )
        if "gh_axis" in effects:
            risk_flags.append("gh_axis")
            risk_profile.append(
                {
                    "peptide": pep,
                    "risk_type": "GH-axis caution",
                    "detail": "Excessive or prolonged GH/IGF-1 pathway stimulation can increase concern for insulin resistance trajectory, glucose dysregulation, and growth signaling load in susceptible individuals.",
                    "severity": "ELEVATED",
                }
            )
            risk_profile.append(
                {
                    "peptide": pep,
                    "risk_type": "Predisposition concerns",
                    "detail": "In predisposed contexts, intensified anabolic signaling may raise concern about pro-growth environments, including theoretical tumor-growth signal amplification pathways.",
                    "severity": "ELEVATED",
                }
            )
        if tier in ["C", "D"]:
            evidence_gaps.append(
                {
                    "peptide": pep,
                    "gap": "Needs stronger randomized human outcome data and longer-horizon safety characterization.",
                }
            )

    for i in range(len(unique_stack)):
        for j in range(i + 1, len(unique_stack)):
            left = unique_stack[i]
            right = unique_stack[j]
            left_meta = STACK_KNOWLEDGE.get(left, {})
            right_meta = STACK_KNOWLEDGE.get(right, {})
            left_effects = set(left_meta.get("effects", []))
            right_effects = set(right_meta.get("effects", []))
            overlap = sorted(left_effects.intersection(right_effects))
            left_unique = sorted(left_effects - right_effects)
            right_unique = sorted(right_effects - left_effects)
            synergy_analysis.append(
                {
                    "pair": [left, right],
                    "why_complementary": "One component may broaden pathway coverage while the other deepens target intensity, creating a layered objective fit.",
                    "shared_targets": [describe_effect(x) for x in overlap],
                    "left_unique_targets": [describe_effect(x) for x in left_unique],
                    "right_unique_targets": [describe_effect(x) for x in right_unique],
                    "pathway_reasoning": "Overlap can reinforce core goal biology while non-overlap can extend support to adjacent physiological constraints.",
                }
            )

    if not neuroplasticity_notes:
        neuroplasticity_notes.append(
            {
                "peptide": "stack",
                "note": "This stack is not primarily neuroplasticity-targeted, though systemic metabolic and stress-load changes can still indirectly affect brain plasticity context.",
                "confidence": "LIMITED",
            }
        )

    if not risk_profile:
        risk_profile.append(
            {
                "peptide": "stack",
                "risk_type": "General caution",
                "detail": "Stacking increases complexity and confounding. Misuse can magnify adverse-response uncertainty and should be interpreted within controlled evidence limitations.",
                "severity": "MODERATE",
            }
        )

    return {
        "goal_label": goal.get("label"),
        "what_it_does": "Stack objective is to combine high-overlap primary target coverage with selective adjunct pathways to improve goal-aligned response probability.",
        "how_it_does_it": "Mechanistically, each peptide contributes effect-cluster pressure across metabolic, endocrine, recovery, neurocognitive, or pigmentation pathways depending on composition.",
        "why_it_does_it": "Complementary pathway coverage can reduce single-path dependence and support multi-node biology relevant to the selected goal.",
        "mechanism_map": mechanism_map,
        "pathway_targets": pathways,
        "synergy_analysis": synergy_analysis,
        "neuroplasticity_notes": neuroplasticity_notes,
        "risk_profile": risk_profile,
        "risk_flags": sorted(list(set(risk_flags))),
        "evidence_gaps": evidence_gaps,
    }


def build_stack_candidates(goal_key, priority_peptide):
    goal = GOAL_BLUEPRINTS.get(goal_key)
    if not goal:
        return []
    priority = normalize_term(priority_peptide or "")
    known_priority = priority if priority in STACK_KNOWLEDGE else None
    candidates = []
    base_pool = [
        ["retatrutide", "tesamorelin"],
        ["retatrutide", "tesamorelin", "ipamorelin"],
        ["retatrutide", "tesamorelin", "mots-c"],
        ["semaglutide", "tesamorelin"],
        ["tirzepatide", "tesamorelin"],
        ["tesamorelin", "ipamorelin"],
        ["semax", "selank"],
        ["melanotan-2", "ghk-cu"],
        ["ghk-cu", "tb-500"],
        ["dsip", "selank"],
        ["ss-31", "mots-c"],
        ["semaglutide", "aod-9604"],
        ["tirzepatide", "mots-c", "ss-31"],
        ["retatrutide", "cagrilintide"],
        ["semaglutide", "cagrilintide"],
        ["tesamorelin", "mk-677"],
        ["mk-677", "ipamorelin"],
        ["pt-141", "kisspeptin-10"],
        ["thymosin-alpha-1", "ghk-cu"],
        ["igf-1-lr3", "peg-mgf"],
        ["semax", "dihexa"],
        ["ghrp-2", "cjc-1295"],
        ["ghrp-6", "sermorelin"],
        ["liraglutide", "tirzepatide"],
        ["ss-31", "humanin"],
        ["thymosin-alpha-1", "thymulin"],
        ["aod-9604", "mk-677"],
        ["dsip", "pinealon"],
        ["pinealon", "selank"],
        ["bpc-157", "ghk-cu"],
        ["tb-500", "bpc-157"],
        ["mots-c", "humanin"],
        ["ipamorelin", "cjc-1295"],
        ["semax", "selank", "dsip"],
    ]
    for stack in base_pool:
        if known_priority and known_priority not in stack:
            continue
        score = 0
        reasons = []
        tier_tags = []
        has_relevance = False
        for pep in stack:
            meta = STACK_KNOWLEDGE.get(pep)
            if not meta:
                continue
            tier = meta.get("tier", "D")
            tier_tags.append({"peptide": pep, "tier": tier})
            score += tier_points(tier)
            effects = set(meta.get("effects", []))
            overlaps = [x for x in goal.get("primary_targets", []) if x in effects]
            if overlaps:
                score += len(overlaps) * 7
                has_relevance = True
                reasons.append(f"{pep} aligns with {', '.join(overlaps)}")
            optional = [x for x in goal.get("optional_support", []) if x in effects]
            if optional:
                score += len(optional) * 3
        if not has_relevance:
            continue
        unique_stack = list(dict.fromkeys(stack))
        if len(unique_stack) >= 2:
            score += 5
        stack_key = "+".join(unique_stack)
        community_note = COMMUNITY_NOTES.get(stack_key)
        evidence_tier = "HIGH" if score >= 70 else "MEDIUM" if score >= 50 else "LIMITED"
        peptide_evidence = []
        for pep in unique_stack:
            meta = STACK_KNOWLEDGE.get(pep, {})
            evidence_row = build_peptide_evidence(pep)
            evidence_row["tier"] = meta.get("tier", "D")
            evidence_row["summary"] = meta.get("summary", "No summary available.")
            peptide_evidence.append(evidence_row)
        deep_research = build_stack_deep_research(goal, unique_stack)
        candidates.append(
            {
                "goal": goal_key,
                "goal_label": goal.get("label"),
                "priority_peptide": known_priority,
                "stack": unique_stack,
                "score": min(100, score),
                "evidence_tier": evidence_tier,
                "rationale": reasons[:5],
                "phase_note": goal.get("phase_note"),
                "tier_tags": tier_tags,
                "community_signal": {
                    "present": bool(community_note),
                    "note": community_note,
                    "classification": "ANECDOTAL" if community_note else "NONE",
                },
                "peptide_evidence": peptide_evidence,
                "deep_research": deep_research,
                "sources": [
                    {"label": "ClinicalTrials.gov", "url": "https://clinicaltrials.gov/"},
                    {"label": "PubMed", "url": "https://pubmed.ncbi.nlm.nih.gov/"},
                ],
            }
        )
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    return candidates[:5]


def fetch_openfda(term):
    """Fetch FDA drug label data. Validates result actually matches the queried term."""
    endpoint = f"https://api.fda.gov/drug/label.json?search={quote(term)}&limit=3"
    data = fetch_json(endpoint)
    if not data:
        return None
    results = data.get("results", [])
    if not results:
        return None

    term_lower = term.lower().strip()
    best = None
    best_score = 0
    for item in results:
        generic = (item.get("generic_name") or item.get("openfda", {}).get("generic_name", [""])[0] or "").lower()
        brand = (item.get("brand_name") or item.get("openfda", {}).get("brand_name", [""])[0] or "").lower()
        indications_text = (item.get("indications_and_usage", [""])[0] or "").lower()[:500]
        score = 0
        if term_lower in generic or term_lower in brand:
            score += 20
        elif term_lower in indications_text:
            score += 10
        # Bonus if term appears in any field
        if term_lower in str(item).lower():
            score += 5
        if score > best_score:
            best_score = score
            best = item

    # Only return data if we found a meaningful match
    if not best or best_score < 10:
        return None

    indications = best.get("indications_and_usage", [""])
    warnings = best.get("warnings", [""])
    reactions = best.get("adverse_reactions", [""])
    generic_name = best.get("generic_name") or best.get("openfda", {}).get("generic_name", [""])[0] or ""
    brand_name = best.get("brand_name") or best.get("openfda", {}).get("brand_name", [""])[0] or ""
    return {
        "indications": indications[0][:500] if indications and indications[0] else "No FDA indication text available.",
        "warnings": warnings[0][:500] if warnings and warnings[0] else "No FDA warnings text available.",
        "adverse": reactions[0][:500] if reactions and reactions[0] else "No FDA adverse reaction text available.",
        "generic_name": generic_name,
        "brand_name": brand_name,
    }


def build_medical_definition(name, trials, fda_data, wiki_summary, uniprot_data=None):
    has_trials = bool(trials)
    has_fda = bool(fda_data)
    trial_count = len(trials) if trials else 0

    parts = [f"{name} is a peptide — a short chain of amino acids that acts like a signaling molecule in the body."]

    if uniprot_data and uniprot_data.get("protein_name") and uniprot_data["protein_name"].lower() != name.lower():
        parts.append(f"Its official protein name is {uniprot_data['protein_name']}.")

    if uniprot_data and uniprot_data.get("function"):
        parts.append(f"At the molecular level: {uniprot_data['function'][:500]}")

    if has_trials:
        top = trials[0]
        phases = []
        phase_text = top.get("methods", "")
        if "Phase 3" in phase_text or "Phase3" in phase_text or "PHASE3" in phase_text:
            phases.append("late-stage human testing (Phase 3)")
        elif "Phase 2" in phase_text or "Phase2" in phase_text:
            phases.append("mid-stage human testing (Phase 2)")
        elif "Phase 1" in phase_text or "Phase1" in phase_text:
            phases.append("early human safety testing (Phase 1)")
        status = top.get("status", "").replace("_", " ").title()
        parts.append(
            f"It has been studied in {trial_count} clinical trial{'s' if trial_count != 1 else ''} on humans. "
            f"The main study, '{top.get('title', 'N/A')}', is currently listed as {status}."
        )
        if phases:
            parts.append(f"This places it in {phases[0]} — meaning it has{'already' if 'late' in phases[0] else ''} been tested in people to see if it works and is safe.")
    elif has_fda:
        parts.append(
            f"It is linked to regulated drug labeling through the FDA, meaning it has undergone formal regulatory review "
            f"for safety and intended use in at least one medical context."
        )

    if fda_data:
        ind = fda_data.get("indications", "")
        if ind and ind != "No FDA indication text available.":
            parts.append(f"From FDA sources, its approved or investigated use involves: {ind[:400]}")

    if uniprot_data and uniprot_data.get("pharmaceutical"):
        parts.append(f"Its pharmaceutical role, from protein databases: {uniprot_data['pharmaceutical'][:400]}")

    if wiki_summary and "No encyclopedia" not in wiki_summary and "No summary" not in wiki_summary:
        short_wiki = wiki_summary[:500]
        parts.append(f"General background: {short_wiki}")

    if not has_trials and not has_fda:
        parts.append(f"Currently, detailed human study data is limited in public research databases. Core background: {wiki_summary[:400]}")

    return " ".join(parts)


def build_plain_summary(wiki_summary, trials, fda_data=None, pubchem=None, uniprot_data=None):
    parts = []

    if trials:
        first = trials[0]
        total = len(trials)
        phases_found = set()
        statuses = set()
        for t in trials:
            m = t.get("methods", "")
            s = t.get("status", "")
            statuses.add(s)
            if "Phase 3" in m: phases_found.add("Phase 3")
            elif "Phase 2" in m: phases_found.add("Phase 2")
            elif "Phase 1" in m: phases_found.add("Phase 1")
        status_summary = ", ".join(s.replace("_", " ").title() for s in sorted(statuses) if s)

        parts.append(
            f"In everyday language: {first['title']}. "
            f"This peptide has been looked at in {total} human stud{'ies' if total != 1 else 'y'} "
            f"available on ClinicalTrials.gov"
        )
        if phases_found:
            parts.append(f"through {' and '.join(sorted(phases_found))} testing")
        parts.append(".")
        if status_summary:
            parts.append(f" Study statuses include: {status_summary}.")
        parts.append(f" Here's what one study summary says: {first['lay_summary']}")

    elif fda_data:
        ind = fda_data.get("indications", "No FDA information available")
        parts.append(
            "In simple terms: This peptide has information in FDA drug labeling systems. "
            f"Its documented medical use involves: {ind[:500]}"
        )
        warn = fda_data.get("warnings", "")
        if warn and warn != "No FDA warnings text available.":
            parts.append(f" Safety note from regulators: {warn[:300]}")
    elif uniprot_data and uniprot_data.get("function"):
        parts.append(f"From protein databases: {uniprot_data['function'][:500]}")
    else:
        parts.append(f"In simple terms: {wiki_summary[:600]}")

    if uniprot_data and uniprot_data.get("pharmaceutical") and not fda_data:
        parts.append(f"Its pharmaceutical role: {uniprot_data['pharmaceutical'][:400]}")

    if pubchem:
        mw = pubchem.get("molecular_weight")
        formula = pubchem.get("formula")
        iupac = pubchem.get("iupac")
        log_p = pubchem.get("log_p")
        if formula or mw:
            chem = "Chemically, "
            if formula: chem += f"its molecular formula is {formula}"
            if formula and mw: chem += " and "
            if mw: chem += f"it weighs about {mw} g/mol (a measure of molecular size)"
            chem += "."
            parts.append(chem)
        if iupac:
            parts.append(f"Its official chemical name is: {iupac[:200]}")
        if log_p:
            try:
                lp = float(log_p)
                if lp < 0:
                    parts.append(f"Its LogP value is {log_p}, meaning it dissolves easily in water (not fatty tissues).")
                elif lp < 3:
                    parts.append(f"Its LogP value is {log_p}, meaning it has a balanced mix of water and fat solubility.")
                else:
                    parts.append(f"Its LogP value is {log_p}, meaning it is more attracted to fatty tissues than water.")
            except (ValueError, TypeError):
                # Skip LogP info if value is non-numeric
                pass

    if not trials and not fda_data and not pubchem and not (uniprot_data and uniprot_data.get("function")):
        parts.append(wiki_summary[:600])

    return " ".join(parts)


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


def build_clinical_snapshot(term, trials, pubmed, fda_data, wiki_summary, pubchem=None, uniprot_data=None):
    base = SNAPSHOT_LIBRARY.get(term, {})
    primary_effect = base.get("primary_effect")
    mechanism_pathway = base.get("mechanism_pathway")
    expected_body_outcomes = base.get("expected_body_outcomes")
    clinical_context = base.get("clinical_context")

    trial_count = len(trials) if trials else 0
    uniprot_func = uniprot_data.get("function") if uniprot_data else None
    uniprot_pharm = uniprot_data.get("pharmaceutical") if uniprot_data else None

    if not primary_effect:
        if trials:
            top = trials[0]
            status = top.get('status', '').replace('_', ' ').title()
            primary_effect = (
                f"This peptide is being studied in humans to see what health effects it has. "
                f"So far, {trial_count} trial{'s' if trial_count != 1 else ''} {'have' if trial_count != 1 else 'has'} been registered. "
                f"The main study is called '{top.get('title', 'N/A')}' and its current status is '{status}'. "
                f"In simple terms, researchers are running this study to find out whether the peptide works for a specific health purpose "
                f"and whether it is safe for people to take."
            )
        elif fda_data:
            ind = fda_data.get('indications', '')
            primary_effect = (
                f"This peptide is mentioned in official FDA drug records, meaning it has some level of regulatory review behind it. "
                f"According to the FDA, its documented medical purpose is: {ind[:400] if ind else 'Available in drug labeling databases.'}"
            )
        elif uniprot_func:
            primary_effect = f"According to protein databases, this peptide has the following biological role: {uniprot_func[:400]}"
        else:
            primary_effect = (
                f"Based on public research databases, this peptide is known to scientists and has been written about in research papers. "
                f"The exact effects on the human body depend on more detailed clinical studies. Current public data gives us a starting point but does not yet provide a complete picture."
            )

    if not mechanism_pathway:
        if uniprot_func and uniprot_data.get("keywords"):
            keywords = ", ".join(uniprot_data["keywords"][:5])
            mechanism_pathway = (
                f"From protein database records, this peptide is classified with the following biological keywords: {keywords}. "
                f"Its described function is: {uniprot_func[:300]}"
            )
        elif trials:
            top = trials[0]
            methods = top.get("methods", "")
            mechanism_pathway = (
                f"A mechanism is how a peptide works inside your body at the cellular level. "
                f"While detailed mechanism data is still being studied, here is what we know from the clinical trial setup: {methods}"
            )
        else:
            mechanism_pathway = (
                f"A peptide's mechanism is the specific way it interacts with cells and signals in the body. "
                f"Detailed mechanism information is not yet widely available in public databases for this specific peptide. "
                f"For context: {wiki_summary[:300]}"
            )

    if not expected_body_outcomes:
        if uniprot_pharm:
            expected_body_outcomes = uniprot_pharm[:400]
        else:
            expected_body_outcomes = (
                "What might happen in your body depends on many factors: the specific peptide, how much is taken (dose), "
                "how long it is used, the person's health status, and whether it is combined with other treatments. "
                "People may experience different effects. For the most reliable picture of what to expect, "
                "look at the completed clinical trials below — they show what happened to actual study participants."
            )

    if not clinical_context:
        clinical_context = (
            "To make sense of this information, it helps to know how reliable the evidence is. "
            "Randomized, controlled trials (where one group gets the peptide and another gets a placebo) "
            "give the strongest evidence. Early-phase studies (Phase 1) mainly test safety, while later phases (Phase 2-3) "
            "test effectiveness. Keep in mind that results in a tightly controlled study may not always match what happens "
            "in everyday use — real people have different health conditions, ages, and lifestyles than study participants."
        )

    evidence_points = int(bool(trials)) + int(bool(pubmed)) + int(bool(fda_data))
    evidence_strength = "HIGH" if evidence_points >= 2 else "MODERATE" if evidence_points == 1 else "LIMITED"

    return {
        "primary_effect": primary_effect,
        "mechanism_pathway": mechanism_pathway,
        "expected_body_outcomes": expected_body_outcomes,
        "clinical_context": clinical_context,
        "evidence_strength": evidence_strength,
    }

CACHE_BUST = str(int(time.time()))
VERSION = "VER-006"


# ── Evidence cache for Ask AI live data ──
EVIDENCE_CACHE = {}
MAX_CACHE_AGE = 300  # 5 minutes


def fetch_peptide_evidence(pep):
    now = time.time()
    cached = EVIDENCE_CACHE.get(pep)
    if cached and (now - cached["cached_at"]) < MAX_CACHE_AGE:
        return cached

    term = normalize_term(pep)
    wiki = fetch_wikipedia_summary(term)
    trials = fetch_clinical_trials(term)
    pubmed_raw = fetch_pubmed(term)
    pubmed = rank_pubmed(pubmed_raw) if pubmed_raw else []
    # Skip OpenFDA for known research chemicals — they won't have drug labels
    reg_status = REGULATORY_STATUS.get(pep, "research_chemical")
    if reg_status != "research_chemical":
        fda_data = fetch_openfda(term)
    else:
        fda_data = None
    evidence_score = build_evidence_score(trials, pubmed, fda_data, wiki)
    claims = build_evidence_claims(trials, pubmed, fda_data)

    # ── PrimeKG enrichment ──
    try:
        primekg_data = primekg.get_entity_summary(term)
    except Exception:
        primekg_data = None

    result = {
        "peptide": pep,
        "trials": trials or [],
        "trial_count": len(trials) if trials else 0,
        "completed_trials": sum(1 for t in (trials or []) if (t.get("status") or "") == "COMPLETED"),
        "pubmed": pubmed or [],
        "pubmed_count": len(pubmed) if pubmed else 0,
        "fda_data": fda_data,
        "wiki": wiki,
        "evidence_score": evidence_score,
        "claims": claims or [],
        "primekg": primekg_data,
        "cached_at": now,
    }
    EVIDENCE_CACHE[pep] = result
    return result


def tier_badge_html(tier):
    labels = {"A": "Trial-heavy", "B": "Observational", "C": "Mechanistic", "D": "Anecdotal"}
    l = labels.get(tier, "Unknown")
    return f'<span class="badge badge-tier-{tier.lower()}">{tier} — {l}</span>'


def regulatory_badge_html(status):
    styles = {
        "fda_approved": '<span class="badge badge-fda">FDA Approved</span>',
        "investigational": '<span class="badge badge-investigational">In Clinical Trials</span>',
        "research_chemical": '<span class="badge badge-research">Research Chemical</span>',
    }
    return styles.get(status, '<span class="badge">Unknown</span>')


@app.context_processor
def inject_cache_bust():
    return dict(cache_bust=CACHE_BUST, version=VERSION)

@app.route('/')
def index():
    all_peptides = sorted(set(ALIASES.values()) | set(STACK_KNOWLEDGE.keys()))
    return render_template('index.html', all_peptides=all_peptides)


@app.route('/stacks')
def stacks_page():
    all_peptides = sorted(set(ALIASES.values()) | set(STACK_KNOWLEDGE.keys()))
    goals = {k: v["label"] for k, v in GOAL_BLUEPRINTS.items()}
    return render_template('stacks.html', all_peptides=all_peptides, goals=goals)


@app.route('/tracker')
def tracker_page():
    all_peptides = sorted(set(ALIASES.values()) | set(STACK_KNOWLEDGE.keys()))
    return render_template('tracker.html', all_peptides=all_peptides)


@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route('/catalog')
def catalog():
    return jsonify({"items": ORDER_CATALOG}), 200

@app.route('/search')
def search():
    try:
        return _do_search()
    except Exception as e:
        return jsonify({"error": "Search failed due to a server error. Some external databases may be temporarily unavailable. Please try again.", "detail": str(e)[:200]}), 500


def _do_search():
    raw_term = (request.args.get("term") or "").strip()
    if not raw_term:
        return jsonify({"error": "Please enter a peptide name before searching."}), 400

    term = normalize_term(raw_term)
    wiki = fetch_wikipedia_summary(term)
    trials = fetch_clinical_trials(term)
    pubmed = rank_pubmed(fetch_pubmed(term))
    fda_data = fetch_openfda(term)
    pubchem = fetch_pubchem(term)
    rcsb = fetch_rcsb_pdb(term)
    uniprot_data = fetch_uniprot(term)
    medical_definition = build_medical_definition(wiki["title"], trials, fda_data, wiki["summary"], uniprot_data)
    plain_summary = build_plain_summary(wiki["summary"], trials, fda_data, pubchem, uniprot_data)
    benefits, cons = build_benefits_and_cons(trials, fda_data)
    timeline = build_timeline(trials)
    claims = build_evidence_claims(trials, pubmed, fda_data)
    snapshot = build_clinical_snapshot(term, trials, pubmed, fda_data, wiki["summary"], pubchem, uniprot_data)
    evidence_score = build_evidence_score(trials, pubmed, fda_data, wiki)
    source_ok = source_status(wiki, trials, pubmed, fda_data, pubchem, rcsb, uniprot_data)
    healthy_sources = sum(1 for ok in source_ok.values() if ok)
    reliability = "HIGH" if healthy_sources >= 4 else ("MEDIUM" if healthy_sources >= 2 else "LOW")

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
        "pubchem": pubchem,
        "pdb_structures": rcsb,
        "uniprot": uniprot_data,
        "source_status": source_ok,
        "reliability": reliability,
        "partial_data": healthy_sources < 4,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {"label": "Wikipedia", "url": wiki["url"]},
            {"label": "ClinicalTrials.gov search", "url": f"https://clinicaltrials.gov/search?term={quote(term)}"},
            {"label": "PubMed search", "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={quote(term)}"},
            {"label": "OpenFDA drug labels", "url": f"https://api.fda.gov/drug/label.json?search={quote(term)}&limit=1"},
            {"label": "PubChem", "url": f"https://pubchem.ncbi.nlm.nih.gov/#query={quote(term)}"},
            {"label": "RCSB Protein Data Bank", "url": f"https://www.rcsb.org/search?request=%7B%22query%22%3A%7B%22type%22%3A%22group%22%2C%22logical_operator%22%3A%22and%22%2C%22nodes%22%3A%5B%7B%22type%22%3A%22terminal%22%2C%22service%22%3A%22full_text%22%2C%22parameters%22%3A%7B%22value%22%3A%22{quote(term)}%22%7D%7D%5D%7D%7D"},
            {"label": "UniProt", "url": f"https://www.uniprot.org/uniprotkb?query={quote(term)}"},
        ],
        "protocol": STACK_PROTOCOLS.get(term),
        "stack_pairings": [
            {
                "stack_key": sk,
                "name": proto.get("name", sk),
                "goal": proto.get("goal", ""),
                "cycle_weeks": proto.get("cycle_weeks", 0),
                "summary": proto.get("evidence_summary", ""),
            }
            for sk, proto in STACK_PROTOCOLS.items()
            if term in sk.split("+")
        ][:8],
        "local_data": {
            "stack_knowledge": STACK_KNOWLEDGE.get(term, {}),
            "snapshot": SNAPSHOT_LIBRARY.get(term, {}),
            "goals": [
                gk for gk, gv in GOAL_BLUEPRINTS.items()
                if any(
                    et in STACK_KNOWLEDGE.get(term, {}).get("effects", [])
                    for et in gv.get("primary_targets", [])
                )
            ],
        },
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


@app.route('/stack-protocol')
def stack_protocol():
    stack_key = (request.args.get("stack") or "").strip().lower()
    if not stack_key:
        return jsonify({"error": "No stack key provided."}), 400
    # Try exact match first, then search for any protocol containing all peptides
    if stack_key in STACK_PROTOCOLS:
        return jsonify({"stack": stack_key, "protocol": STACK_PROTOCOLS[stack_key]}), 200
    # Try partial match — check each protocol key if it contains all terms
    terms = stack_key.replace("+", " ").split()
    for key, proto in STACK_PROTOCOLS.items():
        key_lower = key.lower()
        if all(t in key_lower for t in terms):
            return jsonify({"stack": key, "protocol": proto}), 200
    return jsonify({"error": "No protocol found for this stack combination."}), 404


@app.route('/stack-recommend')
def stack_recommend():
    goal = (request.args.get("goal") or "fat_loss").strip().lower()
    priority = (request.args.get("priority") or "").strip().lower()
    if goal not in GOAL_BLUEPRINTS:
        return jsonify({"error": "Unsupported goal."}), 400
    candidates = build_stack_candidates(goal, priority)
    # Attach protocol data to each recommendation
    for cand in candidates:
        stack_key = "+".join(cand.get("stack", []))
        if stack_key in STACK_PROTOCOLS:
            cand["protocol"] = STACK_PROTOCOLS[stack_key]
    return jsonify(
        {
            "goal": goal,
            "goal_label": GOAL_BLUEPRINTS[goal]["label"],
            "priority": normalize_term(priority),
            "recommendations": candidates,
            "policy": {
                "research_only": True,
                "medical_note": "Educational research context only. Not medical advice.",
                "evidence_tiers": {
                    "A": "Trial-heavy (human trials)",
                    "B": "Observational/review-weighted",
                    "C": "Mechanistic or limited human evidence",
                    "D": "Mostly anecdotal/preclinical",
                },
            },
        }
    ), 200


@app.route('/symptom-search')
def symptom_search():
    raw_query = (request.args.get("q") or "").strip()
    if not raw_query:
        return jsonify({"error": "Please describe what you are looking for."}), 400

    query = raw_query.lower().strip()
    stop_words = {
        "a", "an", "the", "for", "and", "or", "to", "of", "in", "with", "that",
        "is", "it", "on", "at", "by", "i", "me", "my", "we", "our", "you",
        "your", "he", "she", "they", "them", "their", "this", "that", "these",
        "those", "am", "are", "was", "were", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "but", "if", "because", "as",
        "until", "while", "about", "between", "through", "during", "before",
        "after", "above", "below", "up", "down", "out", "off", "over", "under",
        "again", "further", "then", "once", "here", "there", "when", "where",
        "why", "how", "all", "each", "every", "both", "few", "more", "most",
        "other", "some", "such", "no", "nor", "not", "only", "own", "same",
        "so", "than", "too", "very", "just", "get", "something", "need",
        "help", "want", "looking", "good", "best", "treat", "treatment",
        "peptide", "peptides", "can", "what", "any", "anything",
    }
    tokens = re.findall(r'[a-z]+', query)
    tokens = [t for t in tokens if t not in stop_words and len(t) > 1]

    if not tokens:
        # Single word query that was a stop word — still try exact match
        tokens = [query]

    scored = []
    for condition_key, entry in SYMPTOM_CONDITION_MAP.items():
        score = 0
        if query == condition_key:
            score += 100
        elif condition_key in query or query in condition_key:
            score += 60
        key_tokens = set(re.findall(r'[a-z]+', condition_key))
        if tokens:
            overlap = sum(1 for t in tokens if t in condition_key)
            score += overlap * 20
            partial = sum(
                1 for t in tokens for k in key_tokens
                if len(t) > 2 and (t in k or k in t)
            )
            score += partial * 8
        if score > 0:
            scored.append((condition_key, score, entry))

    if not scored:
        for pep_name, meta in STACK_KNOWLEDGE.items():
            pep_lower = pep_name.lower()
            if pep_lower in query or query in pep_lower:
                scored.append((pep_name, 90, {
                    "peptides": [pep_name],
                    "description": meta.get("summary", ""),
                    "category": "Direct Peptide Match",
                }))
            elif any(t in pep_lower for t in tokens):
                scored.append((pep_name, 40, {
                    "peptides": [pep_name],
                    "description": meta.get("summary", ""),
                    "category": "Direct Peptide Match",
                }))

    scored.sort(key=lambda x: x[1], reverse=True)

    seen_peptides = set()
    results = []
    for condition_key, score, entry in scored[:20]:
        for pep in entry["peptides"]:
            pep = normalize_term(pep)
            if pep in STACK_KNOWLEDGE and pep not in seen_peptides:
                seen_peptides.add(pep)
                sk = STACK_KNOWLEDGE[pep]
                results.append({
                    "peptide": pep,
                    "condition_matched": condition_key,
                    "match_score": score,
                    "reason": entry["description"],
                    "category": entry.get("category", "General"),
                    "stack_knowledge": {
                        "effects": sk.get("effects", []),
                        "tier": sk.get("tier", "D"),
                        "summary": sk.get("summary", ""),
                    },
                    "snapshot": {
                        k: SNAPSHOT_LIBRARY.get(pep, {}).get(k, "")
                        for k in ["primary_effect", "mechanism_pathway",
                                  "expected_body_outcomes", "clinical_context"]
                    },
                })

    matched_peptides_set = set(r["peptide"] for r in results)
    relevant_stacks = []
    for stack_key, proto in STACK_PROTOCOLS.items():
        stack_peps = stack_key.split("+")
        overlap = [p for p in stack_peps if p in matched_peptides_set]
        if overlap:
            relevance = len(overlap) / len(stack_peps)
            first_pep = stack_peps[0]
            relevant_stacks.append({
                "stack_key": stack_key,
                "name": proto.get("name", stack_key),
                "goal": proto.get("goal", ""),
                "matched_peptides": overlap,
                "relevance": round(relevance, 2),
                "protocol": {
                    "cycle_weeks": proto.get("cycle_weeks", 0),
                    "off_weeks": proto.get("off_weeks", 0),
                    "phases": proto.get("phases", []),
                    "post_cycle": proto.get("post_cycle", ""),
                    "evidence_summary": proto.get("evidence_summary", ""),
                },
                "evidence_tier": STACK_KNOWLEDGE.get(first_pep, {}).get("tier", "D"),
            })
    relevant_stacks.sort(key=lambda s: (s["relevance"], len(s["matched_peptides"])), reverse=True)
    relevant_stacks = relevant_stacks[:5]

    return jsonify({
        "query": raw_query,
        "normalized_query": query,
        "matched_conditions": [c for c, s, e in scored[:10]],
        "peptide_results": results[:15],
        "matched_stacks": relevant_stacks,
        "total_peptides_matched": len(results),
        "total_stacks_matched": len(relevant_stacks),
    }), 200


@app.route('/ask')
def ask_page():
    all_peptides = sorted(set(ALIASES.values()) | set(STACK_KNOWLEDGE.keys()))
    return render_template('ask.html', all_peptides=all_peptides)


@app.route('/api/ask', methods=['POST'])
def api_ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Please ask a question."}), 400

    q = question.lower().strip()
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
        "help","want","looking","good","best","treat","treatment",
        "peptide","peptides","can","what","any","anything","tell",
        "know","does","work","use","used","using",
    }
    tokens = re.findall(r'[a-z]+', q)
    tokens = [t for t in tokens if t not in stop_words and len(t) > 1]
    if not tokens:
        tokens = [q]

    matched_peptides = set()
    matched_conditions = []
    matched_goals = []

    # ── Score peptides by multiple match signals ──
    # {pep: {"score": int, "reasons": [str], "matched_effects": [str]}}
    pep_score = {}

    # ── Search symptom/condition map ──
    scored_conditions = []
    for cond_key, entry in SYMPTOM_CONDITION_MAP.items():
        score = 0
        if q == cond_key:
            score += 100
        elif cond_key in q or q in cond_key:
            score += 60
        for t in tokens:
            if t in cond_key:
                score += 20
        if score > 0:
            scored_conditions.append((cond_key, score, entry))
    scored_conditions.sort(key=lambda x: x[1], reverse=True)

    for cond_key, score, entry in scored_conditions[:5]:
        matched_conditions.append({
            "condition": cond_key,
            "description": entry["description"],
            "category": entry.get("category", "General"),
            "peptides": entry["peptides"],
        })
        cond_reason = "Matched condition: " + cond_key.replace("_", " ").title()
        for pep in entry["peptides"]:
            pep = normalize_term(pep)
            if pep not in STACK_KNOWLEDGE:
                continue
            matched_peptides.add(pep)
            if pep not in pep_score:
                pep_score[pep] = {"score": 0, "reasons": [], "matched_effects": []}
            pep_score[pep]["score"] += score // 2  # halved since condition matching is per-condition not per-peptide
            if cond_reason not in pep_score[pep]["reasons"]:
                pep_score[pep]["reasons"].append(cond_reason)

    # ── Search STACK_KNOWLEDGE directly (name/substring match) ──
    for pep_name, meta in STACK_KNOWLEDGE.items():
        pep_lower = pep_name.lower()
        matched_here = False
        if pep_lower in q or q in pep_lower:
            matched_peptides.add(pep_name)
            matched_here = True
        else:
            for t in tokens:
                if t in pep_lower:
                    matched_peptides.add(pep_name)
                    matched_here = True
                    break
        if matched_here:
            if pep_name not in pep_score:
                pep_score[pep_name] = {"score": 0, "reasons": [], "matched_effects": []}
            pep_score[pep_name]["score"] += 50
            if "Direct name match" not in pep_score[pep_name]["reasons"]:
                pep_score[pep_name]["reasons"].append("Direct name match")

    # ── Search goals ──
    for gk, gv in GOAL_BLUEPRINTS.items():
        label = gv["label"].lower()
        for t in tokens:
            if t in label or label in t:
                matched_goals.append(gk)
                break

    # ── Search effects via EFFECT_KEYWORDS ──
    query_effects = set()
    for t in tokens:
        if t in EFFECT_KEYWORDS:
            for eid in EFFECT_KEYWORDS[t]:
                query_effects.add(eid)

    if query_effects:
        for pep_name, meta in STACK_KNOWLEDGE.items():
            pep_effects = set(meta.get("effects", []))
            overlap = pep_effects & query_effects
            if overlap:
                if pep_name not in matched_peptides:
                    matched_peptides.add(pep_name)
                if pep_name not in pep_score:
                    pep_score[pep_name] = {"score": 0, "reasons": [], "matched_effects": []}
                pep_score[pep_name]["score"] += 30 * len(overlap)
                for eid in overlap:
                    label = EFFECT_LABELS.get(eid, eid.replace("_", " ").title())
                    reason = "Matches effect: " + label
                    if reason not in pep_score[pep_name]["reasons"]:
                        pep_score[pep_name]["reasons"].append(reason)
                    if label not in pep_score[pep_name]["matched_effects"]:
                        pep_score[pep_name]["matched_effects"].append(label)

    # ── Search SNAPSHOT_LIBRARY text fields ──
    for pep_name, snap in SNAPSHOT_LIBRARY.items():
        if pep_name not in STACK_KNOWLEDGE:
            continue
        fields = ["primary_effect", "mechanism_pathway", "expected_body_outcomes", "clinical_context"]
        match_count = 0
        for field in fields:
            text = (snap.get(field) or "").lower()
            for t in tokens:
                if t in text:
                    match_count += 1
                    break
        if match_count:
            if pep_name not in matched_peptides:
                matched_peptides.add(pep_name)
            if pep_name not in pep_score:
                pep_score[pep_name] = {"score": 0, "reasons": [], "matched_effects": []}
            pep_score[pep_name]["score"] += 15 * match_count
            if "Matches description" not in pep_score[pep_name]["reasons"]:
                pep_score[pep_name]["reasons"].append("Matches description")

    # ── Attach full data to matched peptides ──
    peptide_data = {}
    for pep in matched_peptides:
        sk = STACK_KNOWLEDGE.get(pep, {})
        snap = SNAPSHOT_LIBRARY.get(pep, {})
        sc = pep_score.get(pep, {"score": 0, "reasons": [], "matched_effects": []})
        peptide_data[pep] = {
            "summary": sk.get("summary", ""),
            "effects": sk.get("effects", []),
            "tier": sk.get("tier", "D"),
            "primary_effect": snap.get("primary_effect", ""),
            "mechanism": snap.get("mechanism_pathway", ""),
            "outcomes": snap.get("expected_body_outcomes", ""),
            "score": sc["score"],
            "reasons": sc["reasons"],
            "matched_effects": sc["matched_effects"],
        }

    # ── PrimeKG Knowledge Graph enrichment ──
    primekg_relations = {}
    primekg_disease_info = {}
    try:
        for pep in list(matched_peptides)[:5]:
            relations = primekg.query_drug_relations(pep, max_results=10)
            if relations:
                primekg_relations[pep] = relations
        for mc in matched_conditions[:3]:
            disease_info = primekg.query_disease_relations(mc["condition"], max_results=8)
            if disease_info and any(v for v in disease_info.values()):
                primekg_disease_info[mc["condition"]] = disease_info
    except Exception:
        app.logger.warning("PrimeKG query failed", exc_info=True)

    # ── Find relevant stacks ──
    relevant_stacks = []
    for stack_key, proto in STACK_PROTOCOLS.items():
        stack_peps = stack_key.split("+")
        overlap = [p for p in stack_peps if p in matched_peptides]
        if overlap:
            relevant_stacks.append({
                "key": stack_key,
                "name": proto.get("name", stack_key),
                "goal": proto.get("goal", ""),
                "cycle_weeks": proto.get("cycle_weeks", 0),
                "matched_peptides": overlap,
            })

    # ── Check community notes ──
    community_matches = []
    for ck, note in COMMUNITY_NOTES.items():
        for t in tokens:
            if t in ck:
                community_matches.append((ck, note))
                break

    # ── Build answer (HTML format with badges) ──
    answer_parts = []

    # ── Intro paragraph ──
    all_pep_names = list(peptide_data.keys())
    if matched_conditions:
        cond_names = [mc["condition"].replace("_", " ").title() for mc in matched_conditions[:2]]
        top_peps = all_pep_names[:3]
        pep_list_str = ", ".join(p.title() for p in top_peps)
        answer_parts.append(
            "I found information matching **" + cond_names[0] + "** with "
            + str(len(all_pep_names)) + " related peptides including " + pep_list_str + ". Here is the breakdown:"
        )
    elif matched_goals:
        goal_labels = [GOAL_BLUEPRINTS[gk]["label"] for gk in matched_goals[:2]]
        top_peps = all_pep_names[:3]
        pep_list_str = ", ".join(p.title() for p in top_peps)
        answer_parts.append(
            "Your query relates to **" + goal_labels[0] + "** — here are "
            + str(len(all_pep_names)) + " relevant peptides including " + pep_list_str + ":"
        )
    elif all_pep_names:
        top_peps = all_pep_names[:3]
        pep_list_str = ", ".join(p.title() for p in top_peps)
        answer_parts.append(
            "Based on your query, here are the most relevant peptides from our database (" + str(len(all_pep_names)) + " found):"
        )

    if matched_conditions:
        answer_parts.append("")
        for mc in matched_conditions[:2]:
            title = mc["condition"].replace("_", " ").title()
            answer_parts.append("**" + title + "**")
            answer_parts.append(mc["description"])
            if mc["peptides"]:
                pep_list = ", ".join(mc["peptides"])
                answer_parts.append("Related peptides: " + pep_list + ".")

    if peptide_data:
        answer_parts.append("")
        sorted_peps = sorted(peptide_data.items(),
                             key=lambda x: (-x[1].get("score", 0), {"A": 0, "B": 1, "C": 2, "D": 3}.get(x[1]["tier"], 4)))
        shown = set()
        answered_peps = 0
        for pep, pd in sorted_peps:
            if pep in shown:
                continue
            shown.add(pep)

            # Fetch live evidence for top peptides
            ev = None
            if answered_peps < 2:
                try:
                    ev = fetch_peptide_evidence(pep)
                except Exception:
                    ev = None

            answer_parts.append("")
            # Name + tier badge HTML
            tier = pd.get("tier", "D")
            tier_html = tier_badge_html(tier)
            answer_parts.append("**" + pep.title() + "** " + tier_html)

            # Regulatory badge
            reg_status = REGULATORY_STATUS.get(pep, "research_chemical")
            reg_html = regulatory_badge_html(reg_status)
            answer_parts.append(reg_html)

            # ═ NEW: Why it matched ═
            reasons = pd.get("reasons", [])
            if reasons:
                why = " | ".join(reasons[:3])
                answer_parts.append("**Why it matched**: " + why)

            # Evidence score from live data
            if ev and ev.get("evidence_score"):
                es = ev["evidence_score"]
                score = es.get("score", 0)
                tier_label = es.get("tier", "LOW")
                answer_parts.append(
                    "**Evidence Score**: " + str(score) + "/100 (" + tier_label + ")"
                )

            # Clinical trials count
            if ev:
                tc = ev.get("trial_count", 0)
                cc = ev.get("completed_trials", 0)
                pc = ev.get("pubmed_count", 0)
                if tc > 0:
                    answer_parts.append("**Clinical Trials**: " + str(tc) + " registered, " + str(cc) + " completed")
                if pc > 0:
                    answer_parts.append("**PubMed Articles**: " + str(pc) + " indexed")

            # FDA data
            if ev and ev.get("fda_data"):
                fda = ev["fda_data"]
                parts = []
                drug_name = fda.get("brand_name") or fda.get("generic_name") or ""
                prefix = " (" + drug_name + ")" if drug_name else ""
                if fda.get("indications"):
                    parts.append("Indication: " + fda["indications"][:200])
                if fda.get("warnings"):
                    parts.append("Warning: " + fda["warnings"][:200])
                if parts:
                    answer_parts.append("**FDA Data**" + prefix + ": " + " | ".join(parts))
            elif ev and ev.get("fda_data") is None:
                answer_parts.append("*No FDA drug labeling data found for this peptide — it is not an approved drug.*")

            # Primary effect, mechanism, outcomes from local data
            if pd.get("summary"):
                answer_parts.append(pd["summary"])
            if pd.get("primary_effect"):
                answer_parts.append("**Primary effect**: " + pd["primary_effect"])
            if pd.get("mechanism"):
                answer_parts.append("**Mechanism**: " + pd["mechanism"])
            if pd.get("outcomes"):
                answer_parts.append("**Expected outcomes**: " + pd["outcomes"])
            if pd.get("effects"):
                effect_str = ", ".join(e.replace("_", " ").title() for e in pd["effects"])
                answer_parts.append("**Effect profile**: " + effect_str)

            # ═ NEW: Safety inline ═
            safety = SAFETY_NOTES.get(pep) or SAFETY_NOTES.get("general", {})
            safety_points = safety.get("points", [])
            if safety_points:
                first = safety_points[0]
                extra = ""
                if len(safety_points) > 1:
                    extra = " (+" + str(len(safety_points) - 1) + " more safety notes)"
                answer_parts.append("**Safety**: " + first + extra)

            # Evidence breakdown
            if ev and ev.get("evidence_score"):
                bd = ev["evidence_score"].get("breakdown", {})
                breakdown_items = []
                if bd.get("trials"):
                    breakdown_items.append("Trial data: " + str(bd["trials"]) + " pts")
                if bd.get("pubmed"):
                    breakdown_items.append("PubMed quality: " + str(bd["pubmed"]) + " pts")
                if bd.get("fda"):
                    breakdown_items.append("FDA records: " + str(bd["fda"]) + " pts")
                if bd.get("encyclopedia"):
                    breakdown_items.append("Encyclopedia: " + str(bd["encyclopedia"]) + " pts")
                if breakdown_items:
                    answer_parts.append("**Evidence breakdown**: " + " | ".join(breakdown_items))

            # Distinguish approved vs research
            if reg_status == "fda_approved":
                answer_parts.append("*This peptide is FDA-approved for specific medical indications.*")
            elif reg_status == "investigational":
                answer_parts.append("*This peptide is under clinical investigation but not yet FDA-approved.*")
            elif reg_status == "research_chemical":
                answer_parts.append("*This peptide is a research chemical — not FDA-approved. Long-term safety data is limited.*")

            # ═ NEW: Community note inline ═
            for ck, note in COMMUNITY_NOTES.items():
                stack_peps = ck.split("+")
                if pep in stack_peps and any(p in stack_peps for p in shown if p != pep):
                    answer_parts.append("*Community note*: " + note[:300])
                    break

            answered_peps += 1
            if answered_peps >= 3:
                break

    if relevant_stacks:
        answer_parts.append("")
        answer_parts.append("**Relevant Stack Protocols**")
        for rs in relevant_stacks[:3]:
            answer_parts.append("- **" + rs["name"] + "**: " + rs["goal"] +
                               " (" + str(rs["cycle_weeks"]) + " week cycle)")
        answer_parts.append("*Tap a stack link below for full protocol details.*")

    if matched_goals:
        goal_labels = [GOAL_BLUEPRINTS[gk]["label"] for gk in matched_goals[:3]]
        answer_parts.append("")
        answer_parts.append("**Related Goals**: " + ", ".join(goal_labels))

    # ── PrimeKG knowledge graph evidence section ──
    if primekg_relations:
        answer_parts.append("")
        answer_parts.append("**Knowledge Graph Relationships**")
        for pep, relations in primekg_relations.items():
            kg = primekg.format_relations_for_context(relations, pep)
            if kg:
                # Extract only the bullet lines, skip header/source
                for line in kg.split("\n"):
                    if line.startswith("**"):
                        answer_parts.append("- " + line.strip("*"))
        answer_parts.append("*Source: [PrimeKG](https://github.com/mims-harvard/PrimeKG) biomedical knowledge graph (Harvard).*")
    if primekg_disease_info:
        answer_parts.append("")
        for disease, dinfo in primekg_disease_info.items():
            drugs = dinfo.get("drugs", [])
            if drugs:
                drug_names = [d.get("other_name", "") for d in drugs[:3] if d.get("other_name")]
                answer_parts.append("- **" + disease.replace("_", " ").title() + "** associated drugs: " + ", ".join(drug_names))

    # ── Try AI-generated response using research context ──
    if matched_peptides:
        try:
            medical_terms = extract_medical_terms(question)
            research_ctx = build_research_context(list(matched_peptides), medical_terms)
            is_compare = detect_comparison_query(question)
            sysp = ASK_SYSTEM_PROMPT
            if research_ctx:
                sysp += f"\n\n### Research Context (use this to inform your response):\n{research_ctx}"
            ai_answer = generate_local_ai_response(
                question, research_ctx, list(matched_peptides), is_compare, sysp
            )
            if ai_answer and len(ai_answer) > 100:
                answer_parts = [ai_answer]
        except Exception:
            pass

    # Use LLM when no peptide name is directly mentioned in the question
    known_names = set(STACK_KNOWLEDGE.keys())
    known_names.update(a for a in ALIASES if len(a) >= 4)
    known_names.update(a for a in ALIASES.values() if len(a) >= 4)
    has_direct_peptide_match = any(name in q for name in known_names)
    should_use_llm = not has_direct_peptide_match and bool(answer_parts)

    if not answer_parts or all(p.strip() == "" for p in answer_parts) or should_use_llm:
        # ── LLM fallback via Ollama + PubMed ──
        try:
            llm_result = ask_llm.generate_answer(question)
        except Exception as e:
            app.logger.warning("LLM fallback error: %s", e)
            llm_result = None

        if llm_result and llm_result.get("answer"):
            # LLM succeeded — use AI answer
            answer_parts = [llm_result["answer"]]
            llm_citations = []
            for cite in llm_result.get("citations", []):
                llm_citations.append({
                    "source": cite.get("pmid", ""),
                    "label": cite.get("title", "PubMed Article")[:60],
                    "peptide": cite.get("pmid", ""),
                    "link": cite.get("link", ""),
                })
            source_tag = "\n\n*Answer generated by local AI (" + ask_llm.DEFAULT_MODEL + ") with PubMed references.*"
            answer_parts.append(source_tag)

            return jsonify({
                "answer": "\n".join(answer_parts),
                "citations": llm_citations,
                "stacks": [],
                "evidence": {},
                "matched_conditions": [],
                "matched_peptides": [],
                "source": "llm",
            }), 200

        # LLM unavailable (Vercel / cloud) — use PubMed directly
        pubmed_articles = ask_llm.search_pubmed_general(question, retmax=5)
        if pubmed_articles:
            answer_parts = [
                "I searched PubMed for **\"" + question + "\"** and found these research articles:",
                "",
            ]
            pubmed_citations = []
            for a in pubmed_articles:
                answer_parts.append("**" + a["title"] + "**")
                if a.get("abstract"):
                    answer_parts.append(a["abstract"][:400] + ("..." if len(a.get("abstract","")) > 400 else ""))
                if a.get("authors"):
                    answer_parts.append("*" + ", ".join(a["authors"][:3]) + " — " + (a.get("pubdate") or "") + "*")
                answer_parts.append("*Source: " + (a.get("source") or "PubMed") + "*")
                answer_parts.append("")
                pubmed_citations.append({
                    "source": a["pmid"],
                    "label": a["title"][:60],
                    "peptide": a["pmid"],
                    "link": a["link"],
                })
            answer_parts.append("*Results from PubMed. Always consult a healthcare professional before starting any new protocol.*")

            return jsonify({
                "answer": "\n".join(answer_parts),
                "citations": pubmed_citations,
                "stacks": [],
                "evidence": {},
                "matched_conditions": [],
                "matched_peptides": [],
                "source": "pubmed",
            }), 200

        # Try Wikipedia as 3rd fallback — filter out generic/top-level articles
        GENERIC_WIKI_TITLES = {"peptide", "peptides", "protein", "proteins", "drug", "drugs",
                               "medicine", "health", "disease", "therapy", "chemical compound",
                               "biology", "biochemistry", "pharmacology", "amino acid"}
        wiki_articles = ask_llm.search_wikipedia(question, max_results=2)
        wiki_articles = [a for a in wiki_articles
                         if a.get("title", "").lower().strip() not in GENERIC_WIKI_TITLES]
        if wiki_articles:
            answer_parts = [
                "I found information on **Wikipedia** related to your question:",
                "",
            ]
            wiki_citations = []
            for a in wiki_articles:
                answer_parts.append("**" + a["title"] + "**")
                if a.get("summary"):
                    answer_parts.append(a["summary"])
                answer_parts.append("*Source: [" + a["title"] + "](" + a["link"] + ")*")
                answer_parts.append("")
                wiki_citations.append({
                    "source": a["title"],
                    "label": a["title"][:60],
                    "peptide": a["title"],
                    "link": a["link"],
                })
            answer_parts.append("*Information from Wikipedia. Always consult a healthcare professional before starting any new protocol.*")

            return jsonify({
                "answer": "\n".join(answer_parts),
                "citations": wiki_citations,
                "stacks": [],
                "evidence": {},
                "matched_conditions": [],
                "matched_peptides": [],
                "source": "wikipedia",
            }), 200

        # No results from any source
        answer_parts = [
            "I couldn't find specific research about \"" + question + "\" in our database or PubMed.",
            "Try searching for a specific peptide or condition, or rephrase your question.",
            "You can also browse the **Stacks** tab for protocol recommendations.",
        ]

    answer = "\n".join(answer_parts).strip()

    # ── Build evidence dict for frontend ──
    evidence_data = {}
    for pep in sorted(peptide_data.keys(),
                      key=lambda p: -pep_score.get(p, {}).get("score", 0))[:8]:
        try:
            ev = fetch_peptide_evidence(pep)
            if ev:
                es = ev.get("evidence_score") or {}
                evidence_data[pep] = {
                    "tier": STACK_KNOWLEDGE.get(pep, {}).get("tier", "D"),
                    "score": es.get("score", 0),
                    "tier_label": es.get("tier", "LOW"),
                    "trial_count": ev.get("trial_count", 0),
                    "completed_trials": ev.get("completed_trials", 0),
                    "pubmed_count": ev.get("pubmed_count", 0),
                    "has_fda": bool(ev.get("fda_data")),
                    "regulatory_status": REGULATORY_STATUS.get(pep, "research_chemical"),
                }
        except Exception:
            pass

    # ── Build citations ──
    citations = []
    for pep in sorted(matched_peptides,
                      key=lambda p: -pep_score.get(p, {}).get("score", 0))[:12]:
        citations.append({
            "source": pep,
            "label": pep.title(),
            "peptide": pep,
        })
    if community_matches:
        for ck, note in community_matches[:2]:
            parts = ck.split("+")
            for p in parts:
                if p not in {c["source"] for c in citations}:
                    citations.append({
                        "source": p,
                        "label": p.title(),
                        "peptide": p,
                    })

    # ── Stack links ──
    stacks = [rs["key"] for rs in relevant_stacks[:5]]

    return jsonify({
        "answer": answer,
        "citations": citations,
        "stacks": stacks,
        "evidence": evidence_data,
        "matched_conditions": [mc["condition"] for mc in matched_conditions],
        "matched_peptides": list(matched_peptides)[:10],
        "primekg": primekg_relations or None,
        "primekg_diseases": primekg_disease_info or None,
    }), 200


@app.route('/api/interactions', methods=['POST'])
def api_interactions():
    data = request.get_json(silent=True) or {}
    peptides = [normalize_term(p.strip().lower()) for p in data.get("peptides", []) if p.strip()]
    if len(peptides) < 2:
        return jsonify({"interactions": []})

    results = []
    for i in range(len(peptides)):
        for j in range(i + 1, len(peptides)):
            a, b = sorted([peptides[i], peptides[j]])
            interaction = INTERACTION_MATRIX.get((a, b))
            if interaction:
                results.append({
                    "peptide_a": a,
                    "peptide_b": b,
                    "type": interaction["type"],
                    "note": interaction["note"],
                    "evidence": interaction.get("evidence", ""),
                })

    return jsonify({"interactions": results})


@app.route('/api/dosage/<path:peptide>')
def api_dosage(peptide):
    pep = normalize_term(peptide.strip().lower())
    data = DOSAGE_REFERENCE.get(pep)
    if not data:
        return jsonify({"error": "No dosage data for this peptide."}), 404
    return jsonify({"peptide": pep, "dosage": data})


@app.route('/api/safety/<path:peptide>')
def api_safety(peptide):
    pep = normalize_term(peptide.strip().lower())
    data = SAFETY_NOTES.get(pep)
    if data:
        return jsonify({"peptide": pep, "safety": data})
    # Return general safety if no specific notes
    general = SAFETY_NOTES.get("general", {})
    return jsonify({"peptide": pep, "safety": general})


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT SYSTEM PROMPT - Shared across /ask/message and /ask/stream
# ══════════════════════════════════════════════════════════════════════════════

ASK_SYSTEM_PROMPT = """You are an expert research assistant specializing in peptides, pharmaceuticals, and evidence-based medicine. You generate responses using ONLY the research context provided below — no paid APIs, no external AI services.

Guidelines:
1. Provide accurate, evidence-based information with citations from research literature
2. Reference clinical trials, PubMed articles, and research data when available
3. Compare treatments objectively with supporting evidence — discuss efficacy, safety, mechanisms, and clinical outcomes
4. When comparing treatments, provide structured analysis with pros/cons for each option
5. Suggest peptide alternatives when they have superior or complementary evidence
6. Include clinical protocol recommendations and dosages when backed by research
7. Be conversational yet professional — explain complex concepts in accessible terms
8. Admit when evidence is limited, conflicting, or when more research is needed
9. Always prioritize safety and mention when medical supervision is recommended
10. For dosing and protocols, only provide information backed by clinical research
11. Answer general medical questions beyond just peptides — cover pharmaceuticals, supplements, and lifestyle interventions
12. When discussing off-label uses, clearly distinguish between FDA-approved indications and experimental applications
13. Cite PrimeKG knowledge graph relationships when available — drug-disease associations, protein interactions, and disease phenotypes
14. Cite Clinical Knowledge Graph (CKG) evidence when available — protein interactions, drug targets, pathways, disease associations, side effect profiles
15. When research data is insufficient, offer guidance on how to find more information rather than inventing answers
16. Maintain conversation context — refer to previous exchanges when relevant
17. When SIDER side effect data is available in the research context, include relevant adverse reaction information for any discussed drugs or peptides — cite the specific side effects and mention they come from FDA label data
18. When DrugBank pharmacology data is available, reference mechanisms of action, protein targets, and indications — this provides authoritative pharmacological context for any drug or peptide being discussed

When research context is provided below, prioritize that data in your response and cite it appropriately.

Important: Format citations as clickable links. For PubMed articles, use: [PubMed PMID:12345678](https://pubmed.ncbi.nlm.nih.gov/12345678)
For clinical trials, use: [ClinicalTrials.gov NCT12345678](https://clinicaltrials.gov/study/NCT12345678)
For PrimeKG knowledge graph, reference: [PrimeKG (Harvard)](https://github.com/mims-harvard/PrimeKG)
For Clinical Knowledge Graph, reference: [CKG (MannLab)](https://github.com/MannLabs/CKG)
For side effect data, reference: [SIDER (EMBL)](http://sideeffects.embl.de/)
For pharmacology data, reference: [DrugBank](https://go.drugbank.com/)"""

COMPARISON_PROMPT_EXTENSION = """\n\n### Comparison Query Detected
For this comparison question:
- Present a balanced analysis of both/all treatments mentioned
- Discuss mechanisms of action, clinical efficacy, side effect profiles, and cost considerations
- Cite specific studies comparing the treatments when available
- Provide evidence-based recommendations with appropriate caveats
- Consider synergy potential if both could be used together"""

# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def detect_comparison_query(message):
    """Detect if the message is asking for a treatment comparison."""
    comparison_patterns = [
        r'\bvs\b',
        r'\bversus\b',
        r'\bcompare\b',
        r'\bcomparison\b',
        r'\bbetter than\b',
        r'\bor\b.*\bfor\b',  # e.g., "minoxidil or finasteride for hair loss"
        r'\bwhich is better\b',
        r'\bdifference between\b',
    ]
    message_lower = message.lower()
    for pattern in comparison_patterns:
        if re.search(pattern, message_lower):
            return True
    return False


def extract_medical_terms(message):
    """Extract medical terms and treatment names from user message for semantic search."""
    # Common medical keywords that suggest the user wants research
    medical_keywords = [
        'hair loss', 'alopecia', 'weight loss', 'obesity', 'diabetes',
        'fat loss', 'muscle growth', 'anti-aging', 'longevity', 'aging',
        'visceral fat', 'insulin resistance', 'glucose', 'metabolism',
        'testosterone', 'growth hormone', 'hgh', 'healing', 'injury',
        'inflammation', 'recovery', 'skin', 'wrinkles', 'collagen',
        'neuroprotection', 'cognitive', 'memory', 'brain', 'nootropic',
        'cardiovascular', 'heart', 'blood pressure', 'cholesterol',
        'minoxidil', 'finasteride', 'dutasteride', 'rogaine',
        'metformin', 'berberine', 'rapamycin', 'nad', 'nmn', 'resveratrol',
    ]

    message_lower = message.lower()
    extracted_terms = []

    # Look for medical keywords in the message
    for keyword in medical_keywords:
        if keyword in message_lower:
            extracted_terms.append(keyword)

    # Extract treatment names from comparison queries (e.g., "X vs Y")
    comparison_match = re.search(r'(\w+(?:-\w+)*)\s+(?:vs|versus|or)\s+(\w+(?:-\w+)*)', message_lower)
    if comparison_match:
        extracted_terms.extend([comparison_match.group(1), comparison_match.group(2)])

    return list(set(extracted_terms))  # Remove duplicates


def extract_peptide_mentions(message):
    """Extract peptide names mentioned in a user message."""
    message_lower = message.lower()
    mentioned = []

    # Check aliases first
    for alias, canonical in ALIASES.items():
        if alias in message_lower:
            if canonical not in mentioned:
                mentioned.append(canonical)

    # Check canonical names
    all_peptides = set(ALIASES.values()) | set(STACK_KNOWLEDGE.keys()) | set(SNAPSHOT_LIBRARY.keys())
    for peptide in all_peptides:
        if peptide.lower() in message_lower:
            if peptide not in mentioned:
                mentioned.append(peptide)

    return mentioned


def build_research_context(peptides, medical_terms=None):
    """Fetch research context for mentioned peptides and medical terms."""
    context_parts = []

    # Process peptides
    for peptide in peptides[:3]:  # Limit to 3 peptides to avoid token overflow
        term = normalize_term(peptide)

        # Get snapshot if available
        if term in SNAPSHOT_LIBRARY:
            snapshot = SNAPSHOT_LIBRARY[term]
            context_parts.append(f"\n### {peptide.upper()} - Clinical Snapshot\n")
            context_parts.append(f"**Primary Effect:** {snapshot.get('primary_effect', 'N/A')}\n")
            context_parts.append(f"**Mechanism:** {snapshot.get('mechanism_pathway', 'N/A')}\n")
            context_parts.append(f"**Outcomes:** {snapshot.get('expected_body_outcomes', 'N/A')}\n")
            context_parts.append(f"**Clinical Context:** {snapshot.get('clinical_context', 'N/A')}\n")

        # Get clinical trials (limited)
        try:
            trials = fetch_clinical_trials(term)
            if trials:
                context_parts.append(f"\n**Clinical Trials for {peptide}:**\n")
                for trial in trials[:10]:  # Limit to 10 trials
                    context_parts.append(f"- {trial.get('title', 'N/A')} (NCT ID: {trial.get('nct_id', 'N/A')})\n")
                    context_parts.append(f"  Status: {trial.get('status', 'N/A')}, Phase: {trial.get('phase', 'N/A')}\n")
        except:
            pass

        # Get PubMed articles (limited)
        try:
            pubmed = fetch_pubmed(term)
            ranked = rank_pubmed(pubmed)
            if ranked:
                context_parts.append(f"\n**Recent Research for {peptide}:**\n")
                for article in ranked[:10]:  # Limit to 10 articles
                    context_parts.append(f"- {article.get('title', 'N/A')}\n")
                    context_parts.append(f"  PMID: {article.get('pmid', 'N/A')}\n")
        except:
            pass

        # ── PrimeKG Knowledge Graph evidence ──
        try:
            relations = primekg.query_drug_relations(peptide, max_results=8)
            if relations:
                ctx = primekg.format_relations_for_context(relations, peptide)
                if ctx:
                    context_parts.append(ctx + "\n")
        except Exception:
            pass

        # ── SIDER side effects ──
        try:
            sider_ctx = sider_db.format_side_effects_for_context(peptide, max_results=10)
            if sider_ctx:
                context_parts.append(sider_ctx + "\n")
        except Exception:
            pass

        # ── DrugBank pharmacology ──
        try:
            drugbank_ctx = drugbank.format_drugbank_for_context(peptide)
            if drugbank_ctx:
                context_parts.append(drugbank_ctx + "\n")
        except Exception:
            pass

    # ── SIDER side effects for medical terms ──
    if medical_terms:
        for term in medical_terms[:2]:
            try:
                sider_ctx = sider_db.format_side_effects_for_context(term, max_results=8)
                if sider_ctx:
                    context_parts.append(sider_ctx + "\n")
            except Exception:
                pass

    # Process general medical terms (for semantic search)
    if medical_terms:
        for term in medical_terms[:3]:  # Limit to 3 terms
            try:
                pubmed = fetch_pubmed(term)
                ranked = rank_pubmed(pubmed)
                if ranked:
                    context_parts.append(f"\n**Research for '{term}':**\n")
                    for article in ranked[:10]:  # Limit to 10 articles
                        context_parts.append(f"- {article.get('title', 'N/A')}\n")
                        context_parts.append(f"  PMID: {article.get('pmid', 'N/A')}\n")
            except:
                pass

    # ── Append CKG domain context for clinical grounding ──
    if peptides or medical_terms:
        ckg_domains = ckg.get_domain_summary()
        if ckg_domains:
            context_parts.append("\n### Clinical Knowledge Graph (CKG) — Available Domains\n")
            for domain in ckg_domains:
                context_parts.append(
                    f"- **{domain['domain']}** ({domain['relevance']})\n"
                )
            context_parts.append(
                "*Source: [MannLabs/CKG](https://github.com/MannLabs/CKG) — "
                "16M+ nodes, 220M+ relationships*\n\n"
            )

    return "".join(context_parts) if context_parts else None


def _build_ollama_messages(system_prompt, conversation_history, user_message):
    """Build a message list for Ollama from the system prompt and conversation."""
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[-10:]:
        role = "user" if msg.get("role") == "user" else "assistant"
        content = msg.get("content", "")
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def generate_local_ai_response(user_message, research_context, mentioned_peptides, is_comparison, system_prompt=None):
    """Generate an intelligent response using available research context.

    Strategy:
      1. Try Ollama (local LLM) if running — gives the best response quality
      2. Fall back to synthesized template response using research context data
    """

    # ── Strategy 1: Try Ollama if available ──
    if system_prompt and len(system_prompt) < 15000:
        try:
            ollama_msg = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            llm_answer = ask_llm.query_ollama(ollama_msg, max_tokens=1024)
            if llm_answer and len(llm_answer) > 50:
                disclaimer = ""
                if mentioned_peptides or "treatment" in user_message.lower() or "dose" in user_message.lower():
                    disclaimer = (
                        "\n\n---\n\n**Important:** This information is for educational purposes. "
                        "Consult with a qualified healthcare provider before starting any treatment protocol."
                    )
                return llm_answer.strip() + disclaimer
        except Exception:
            pass  # Fall through to template strategy

    # ── Strategy 2: Synthesized template response ──
    parts = []

    # Opening line
    if is_comparison:
        parts.append("Here is a comparison based on available clinical research and knowledge base data:\n\n")
    elif mentioned_peptides:
        peptide_list = ", ".join(mentioned_peptides[:3])
        parts.append(f"Here is what the research database shows about **{peptide_list}** in relation to your question:\n\n")
    else:
        parts.append("Here is what the available research indicates:\n\n")

    # ── Parse research context sections ──
    has_snapshot = False
    has_trials = False
    has_pubmed = False
    has_medical_research = False
    has_primekg = False
    has_ckg = False

    if research_context:
        # --- Clinical Snapshots ---
        if "Clinical Snapshot" in research_context:
            has_snapshot = True
            sections = research_context.split("###")
            for section in sections:
                if "Clinical Snapshot" in section:
                    lines = section.strip().split("\n")
                    name = lines[0].replace("- Clinical Snapshot", "").strip()
                    parts.append(f"### {name} — Clinical Profile\n\n")
                    for line in lines[1:]:
                        text = line.strip()
                        if text.startswith("**") and ":**" in text:
                            key, _, val = text[2:].partition(":** ")
                            parts.append(f"- **{key}:** {val}\n")
                    parts.append("\n")

        # --- Clinical Trials ---
        if "Clinical Trials for" in research_context:
            has_trials = True
            parts.append("### Clinical Trials\n\n")
            trials_sections = research_context.split("**Clinical Trials for")[1:]
            for tsec in trials_sections[:2]:
                tlines = tsec.split("\n")
                peptide_label = tlines[0].strip().rstrip(":**")
                parts.append(f"**{peptide_label}:**\n")
                count = 0
                for line in tlines[1:]:
                    if line.strip().startswith("-") and count < 5:
                        parts.append(f"- {line.strip().lstrip('- ')}\n")
                        count += 1
                    elif "NCT" in line and count <= 5:
                        parts.append(f"  {line.strip()}\n")
                parts.append("\n")

        # --- PubMed peptide research ---
        if "Recent Research for" in research_context:
            has_pubmed = True
            parts.append("### Published Research\n\n")
            rsections = research_context.split("**Recent Research for")[1:]
            for rsec in rsections[:2]:
                rlines = rsec.split("\n")
                peptide_label = rlines[0].strip().rstrip(":**")
                parts.append(f"**{peptide_label} — Recent Studies:**\n")
                count = 0
                for line in rlines[1:]:
                    text = line.strip()
                    if text.startswith("-") and count < 5:
                        title = text.lstrip("- ")
                        parts.append(f"- {title}\n")
                        count += 1
                    elif "PMID:" in text:
                        pmid = text.split("PMID:")[1].strip()
                        parts.append(f"  [PubMed PMID:{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid})\n")
                parts.append("\n")

        # --- PubMed general medical research (FIX: marker was "Research for" not "Recent Research for") ---
        if "Research for '" in research_context:
            has_medical_research = True
            if not has_pubmed:
                parts.append("### Published Research\n\n")
            m_sections = research_context.split("**Research for '")[1:]
            for msec in m_sections[:2]:
                mlines = msec.split("\n")
                term = mlines[0].strip().rstrip("':**")
                parts.append(f"**{term.capitalize()}:**\n")
                count = 0
                for line in mlines[1:]:
                    text = line.strip()
                    if text.startswith("-") and count < 5:
                        title = text.lstrip("- ")
                        parts.append(f"- {title}\n")
                        count += 1
                    elif "PMID:" in text:
                        pmid = text.split("PMID:")[1].strip()
                        parts.append(f"  [PubMed PMID:{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid})\n")
                parts.append("\n")

        # --- PrimeKG ---
        if "PrimeKG Knowledge Graph" in research_context:
            has_primekg = True
            parts.append("### Knowledge Graph Connections (PrimeKG)\n\n")
            kg_sections = research_context.split("###")
            for section in kg_sections:
                if "PrimeKG Knowledge Graph" in section:
                    for line in section.strip().split("\n"):
                        text = line.strip()
                        if text.startswith("**") and ":**" in text:
                            key, _, val = text[2:].partition(":** ")
                            parts.append(f"- **{key}:** {val}\n")
            parts.append("\n*Source: [PrimeKG (Harvard)](https://github.com/mims-harvard/PrimeKG)*\n\n")

        # --- CKG ---
        if "Clinical Knowledge Graph (CKG)" in research_context:
            has_ckg = True
            parts.append("### Clinical Knowledge Graph — Available Evidence\n\n")
            ckg_sections = research_context.split("###")
            for section in ckg_sections:
                if "Clinical Knowledge Graph (CKG)" in section:
                    for line in section.split("\n"):
                        text = line.strip()
                        if text.startswith("- **"):
                            parts.append(f"{text}\n")
            parts.append("\n*Source: [CKG (MannLab)](https://github.com/MannLabs/CKG)*\n\n")

    # ── If we found research data but have no synthesised content, add snapshot/stack ──
    response_text = "".join(parts)
    if mentioned_peptides and len(response_text) < 200:
        for peptide in mentioned_peptides[:2]:
            term = normalize_term(peptide)
            snap = SNAPSHOT_LIBRARY.get(term)
            if snap:
                parts.append(f"### {peptide.upper()}\n\n")
                if snap.get("primary_effect"):
                    parts.append(f"- **Primary Effect:** {snap['primary_effect']}\n")
                if snap.get("mechanism_pathway"):
                    parts.append(f"- **Mechanism:** {snap['mechanism_pathway']}\n")
                if snap.get("expected_body_outcomes"):
                    parts.append(f"- **Expected Outcomes:** {snap['expected_body_outcomes']}\n")
                if snap.get("clinical_context"):
                    parts.append(f"- **Clinical Context:** {snap['clinical_context']}\n")
                parts.append("\n")
            stack = STACK_KNOWLEDGE.get(term)
            if stack and stack.get("description"):
                parts.append(f"{stack['description']}\n\n")
                if stack.get("benefits") and isinstance(stack["benefits"], list):
                    parts.append(f"**Benefits:** {', '.join(stack['benefits'][:5])}\n\n")

    # ── If STILL nothing useful, give a contextual fallback (not the generic one) ──
    response_text = "".join(parts)
    if not response_text or len(response_text) < 100:
        # Build a contextual fallback that references the question
        question_preview = user_message[:150]
        if mentioned_peptides:
            parts = [
                f"I've identified **{', '.join(mentioned_peptides[:3])}** in your question.\n\n",
                "Here's what I can tell you from our research database:\n\n",
            ]
            for peptide in mentioned_peptides[:2]:
                term = normalize_term(peptide)
                snap = SNAPSHOT_LIBRARY.get(term)
                if snap:
                    parts.append(f"**{peptide.upper()}** — {snap.get('primary_effect', 'researched compound')}\n\n")
                    if snap.get("clinical_context"):
                        parts.append(f"{snap['clinical_context']}\n\n")
                stack = STACK_KNOWLEDGE.get(term)
                if stack and stack.get("description"):
                    parts.append(f"{stack['description']}\n\n")
            parts.append(
                "**To get more specific information, I recommend:**\n\n"
                "- Checking [PubMed](https://pubmed.ncbi.nlm.nih.gov) for recent studies\n"
                "- Reviewing [ClinicalTrials.gov](https://clinicaltrials.gov) for ongoing trials\n"
                "- Exploring [PrimeKG](https://github.com/mims-harvard/PrimeKG) or [CKG](https://github.com/MannLabs/CKG) biomedical knowledge graphs\n\n"
            )
        else:
            parts = [
                f"I understand you're asking about: _{question_preview}_\n\n"
                "I wasn't able to find specific research data in our database for this topic.\n\n"
                "**You can try:**\n\n"
                "- Asking about a specific peptide or compound (e.g., BPC-157, semaglutide, MK-677)\n"
                "- Checking [PubMed](https://pubmed.ncbi.nlm.nih.gov) for scientific literature\n"
                "- Reviewing [ClinicalTrials.gov](https://clinicaltrials.gov) for clinical studies\n"
                "- Exploring [PrimeKG](https://github.com/mims-harvard/PrimeKG) or [CKG](https://github.com/MannLabs/CKG) knowledge graphs\n\n"
            ]

    # ── Add disclaimer ──
    final = "".join(parts)
    if mentioned_peptides or "treatment" in user_message.lower() or "dose" in user_message.lower():
        final += "\n\n---\n\n**Important:** This information is for educational purposes. Consult with a qualified healthcare provider before starting any treatment protocol."

    return final


@app.route('/ask/message', methods=['POST'])
def ask_message():
    """Handle AI chat messages with free local research-based response."""
    try:
        payload = request.get_json(silent=True) or {}
        user_message = (payload.get("message") or "").strip()
        conversation_history = payload.get("history") or []

        if not user_message:
            return jsonify({"error": "Message cannot be empty."}), 400

        if len(user_message) > 5000:
            return jsonify({"error": "Message too long. Please limit to 5000 characters."}), 400

        # Extract peptide mentions and medical terms for semantic search
        mentioned_peptides = extract_peptide_mentions(user_message)
        medical_terms = extract_medical_terms(user_message)
        is_comparison = detect_comparison_query(user_message)

        # Build research context
        research_context = None
        if mentioned_peptides or medical_terms:
            research_context = build_research_context(mentioned_peptides, medical_terms)

        # Build system prompt from shared constant
        system_prompt = ASK_SYSTEM_PROMPT

        # Add comparison-specific instructions
        if is_comparison:
            system_prompt += COMPARISON_PROMPT_EXTENSION

        # Add research context if available
        if research_context:
            system_prompt += f"\n\n### Research Context (use this to inform your response):\n{research_context}"

        # Build conversation messages from history
        messages = []
        for msg in conversation_history[-10:]:  # Limit to last 10 messages
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Generate response locally using research context (no external API calls!)
        ai_response = generate_local_ai_response(
            user_message,
            research_context,
            mentioned_peptides,
            is_comparison,
            system_prompt
        )

        # Extract sources from the response (look for markdown links)
        sources = []
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, ai_response)
        for label, url in matches:
            if any(k in url.lower() for k in ["pubmed", "clinicaltrials", "nih.gov", "primekg", "harvard", "mannlabs", "ckg", "sideeffects", "drugbank"]):
                sources.append({"label": label, "url": url})

        # Add knowledge graph sources if their data was included
        if research_context:
            if "PrimeKG Knowledge Graph" in research_context:
                sources.append({
                    "label": "PrimeKG (Harvard)",
                    "url": "https://github.com/mims-harvard/PrimeKG",
                })
            if "Clinical Knowledge Graph" in research_context or "CKG" in research_context:
                sources.append({
                    "label": "CKG (MannLab)",
                    "url": "https://github.com/MannLabs/CKG",
                })
            if "SIDER" in research_context:
                sources.append({
                    "label": "SIDER (EMBL)",
                    "url": "http://sideeffects.embl.de/",
                })
            if "DrugBank" in research_context:
                sources.append({
                    "label": "DrugBank",
                    "url": "https://go.drugbank.com/",
                })

        return jsonify({
            "response": ai_response,
            "sources": sources,
            "mentioned_peptides": mentioned_peptides,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tokens_used": len(prompt.split()) + len(ai_response.split())  # Approximate token count
        }), 200

    except Exception as e:
        return jsonify({"error": f"Chat failed: {str(e)[:100]}"}), 500


@app.route('/ask/stream')
def ask_stream():
    """Stream AI chat responses using Server-Sent Events with free local research-based response."""
    user_message = request.args.get("message", "").strip()
    history_json = request.args.get("history", "[]")

    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    if len(user_message) > 5000:
        return jsonify({"error": "Message too long. Please limit to 5000 characters."}), 400

    try:
        conversation_history = json.loads(history_json)
    except:
        conversation_history = []

    def generate():
        try:
            # Extract peptide mentions and medical terms for semantic search
            mentioned_peptides = extract_peptide_mentions(user_message)
            medical_terms = extract_medical_terms(user_message)
            is_comparison = detect_comparison_query(user_message)

            # Build research context
            research_context = None
            if mentioned_peptides or medical_terms:
                research_context = build_research_context(mentioned_peptides, medical_terms)

            # Build system prompt from shared constant
            system_prompt = ASK_SYSTEM_PROMPT

            # Add comparison-specific instructions
            if is_comparison:
                system_prompt += COMPARISON_PROMPT_EXTENSION

            if research_context:
                system_prompt += f"\n\n### Research Context (use this to inform your response):\n{research_context}"

            # Build conversation
            messages = []
            for msg in conversation_history[-10:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": user_message})

            # Generate response locally using research context (no external API calls!)
            ai_response = generate_local_ai_response(
                user_message,
                research_context,
                mentioned_peptides,
                is_comparison,
                system_prompt
            )

            # Simulate streaming by yielding response in chunks
            chunk_size = 50  # characters per chunk
            for i in range(0, len(ai_response), chunk_size):
                chunk = ai_response[i:i + chunk_size]
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                time.sleep(0.01)  # Small delay to simulate streaming

            # Send final metadata
            yield f"data: {json.dumps({'done': True, 'mentioned_peptides': mentioned_peptides})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)[:100]})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
