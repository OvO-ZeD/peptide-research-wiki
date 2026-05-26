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


def fetch_json(url, headers=None, data=None):
    try:
        req = Request(url, data=data, headers=headers or {"User-Agent": "peptide-wiki/1.0"})
        with urlopen(req, timeout=18) as response:
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
            for d in comment.get("disease", []):
                diseases.append(d.get("diseaseId"))
            if diseases:
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
    ]
    for stack in base_pool:
        if known_priority and known_priority not in stack:
            continue
        score = 0
        reasons = []
        tier_tags = []
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
                reasons.append(f"{pep} aligns with {', '.join(overlaps)}")
            optional = [x for x in goal.get("optional_support", []) if x in effects]
            if optional:
                score += len(optional) * 3
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
            lp = float(log_p)
            if lp < 0:
                parts.append(f"Its LogP value is {log_p}, meaning it dissolves easily in water (not fatty tissues).")
            elif lp < 3:
                parts.append(f"Its LogP value is {log_p}, meaning it has a balanced mix of water and fat solubility.")
            else:
                parts.append(f"Its LogP value is {log_p}, meaning it is more attracted to fatty tissues than water.")

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

@app.route('/')
def index():
    all_peptides = sorted(set(ALIASES.values()) | set(STACK_KNOWLEDGE.keys()))
    return render_template('index.html', all_peptides=all_peptides)


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


@app.route('/stack-recommend')
def stack_recommend():
    goal = (request.args.get("goal") or "fat_loss").strip().lower()
    priority = (request.args.get("priority") or "retatrutide").strip().lower()
    if goal not in GOAL_BLUEPRINTS:
        return jsonify({"error": "Unsupported goal."}), 400
    candidates = build_stack_candidates(goal, priority)
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
