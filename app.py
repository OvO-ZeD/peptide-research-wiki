from flask import Flask, render_template, request, jsonify
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
import time
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
        "primary_effect": "GHK-Cu (copper peptide) is a naturally occurring small peptide that binds copper ions. It is best known for skin regeneration and wound healing — it is a common ingredient in high-end skin care products for anti-aging and collagen support.",
        "mechanism_pathway": "GHK-Cu is a tripeptide (three amino acids: glycine-histidine-lysine) with a copper ion attached. It signals skin cells to produce more collagen and elastin (the proteins that keep skin firm and youthful), reduces inflammation, and acts as an antioxidant. It also promotes blood vessel growth to injured tissues, which aids wound healing. The copper ion is essential for these effects.",
        "expected_body_outcomes": "Topical application may improve skin firmness, reduce fine lines and wrinkles, and support wound healing. Injected forms are discussed for tissue repair, hair growth, and anti-aging, though injection use has less formal study than topical. Effects on skin typically appear after weeks to months of consistent use.",
        "clinical_context": "GHK-Cu is widely used in cosmetic skin care products and has been studied in clinical settings for wound healing. It is not FDA approved as a drug (it is a cosmetic ingredient). Injectable forms are available as research chemicals. The safety of long-term injection use is not as well established as topical application.",
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

ORDER_CATALOG = [
    {"id": "tesamorelin-5mg", "name": "Tesamorelin", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "retatrutide-10mg", "name": "Retatrutide", "variant": "10mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "semaglutide-5mg", "name": "Semaglutide", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "tirzepatide-10mg", "name": "Tirzepatide", "variant": "10mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "cjc1295-5mg", "name": "CJC-1295", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
    {"id": "bpc157-5mg", "name": "BPC-157", "variant": "5mg vial", "price": 120.0, "currency": "USD", "in_stock": True},
]

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

@app.context_processor
def inject_cache_bust():
    return dict(cache_bust=CACHE_BUST)

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
                    "A": "Human trial-heavy",
                    "B": "Observational/review-weighted",
                    "C": "Mechanistic or limited human evidence",
                    "D": "Mostly anecdotal/preclinical",
                },
            },
        }
    ), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
