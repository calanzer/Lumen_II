"""Generate a realistic sample ABA progress report DOCX for pipeline testing.

Run this script once to create the fixture:
    python -m tests.fixtures.generate_sample_report
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from pathlib import Path


def add_heading_with_style(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1A, 0x3C, 0x5E)
    return h


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
    return table


def generate():
    doc = Document()

    # -- Title page --
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("PROGRESS REPORT & REAUTHORIZATION REQUEST\n")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x1A, 0x3C, 0x5E)

    sub = title.add_run("Applied Behavior Analysis Services\nAuthorization Period: July 1, 2025 – December 31, 2025\n")
    sub.font.size = Pt(12)

    clinic = title.add_run("\nBrightPath ABA Services\n2847 Pacific Coast Highway, Suite 200\nLong Beach, CA 90806\nPhone: (562) 555-0142 | Fax: (562) 555-0143\nTax ID: 83-4291056 | NPI: 1234567890\n")
    clinic.font.size = Pt(10)
    clinic.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    doc.add_page_break()

    # -- Section 1: Client Information --
    add_heading_with_style(doc, "1. Client Information")
    add_table(doc,
        ["Field", "Value"],
        [
            ["Client ID", "CR-2024-0847"],
            ["Date of Birth", "09/14/2021"],
            ["Age at Time of Report", "4 years, 1 month"],
            ["Primary Diagnosis", "Autism Spectrum Disorder, Level 2 — Requiring Substantial Support (F84.0)"],
            ["Secondary Diagnosis", "Mixed Receptive-Expressive Language Disorder (F80.2)"],
            ["Referral Source", "Dr. Sarah Chen, Developmental Pediatrician"],
            ["Date of ASD Diagnosis", "03/22/2023"],
            ["Authorization Period", "07/01/2025 – 12/31/2025"],
            ["Payor", "Anthem Blue Cross California"],
            ["Member ID", "XJK9847201"],
            ["Supervising BCBA", "Dr. Maria Gonzalez, BCBA-D"],
            ["BCBA Credential #", "1-19-42831"],
            ["BCBA NPI", "1987654321"],
            ["Lead RBT", "Carlos Mendez, RBT"],
            ["RBT Credential #", "RBT-20230198"],
            ["Service Locations", "Clinic (primary), Home (secondary)"],
        ]
    )

    # -- Section 2: Background & History --
    add_heading_with_style(doc, "2. Background & Relevant History")
    doc.add_paragraph(
        "The client is a 4-year-old male who was diagnosed with Autism Spectrum Disorder (ASD), Level 2 "
        "(Requiring Substantial Support) at 18 months of age by Dr. Sarah Chen, a board-certified developmental "
        "pediatrician. The diagnosis was confirmed through administration of the ADOS-2 (Module 1, comparison score "
        "= 8) and developmental history review. A co-occurring diagnosis of Mixed Receptive-Expressive Language "
        "Disorder (F80.2) was assigned by Dr. Amanda Torres, SLP-CCC, following speech-language evaluation on "
        "06/15/2023."
    )
    doc.add_paragraph(
        "The client began receiving ABA services at BrightPath on 01/15/2024. He lives at home with both parents "
        "and one younger sibling (age 2). The primary language spoken in the home is Spanish, with English used in "
        "community and clinical settings. The client is not currently enrolled in preschool due to behavioral "
        "concerns (aggression) but is on the waitlist for an ASD-inclusive program through the local school district."
    )
    doc.add_paragraph(
        "Relevant medical history includes a history of recurrent otitis media (resolved with PE tubes, 04/2024) "
        "and mild constipation managed with dietary modifications. The client takes no psychotropic medications. "
        "He receives concurrent speech-language therapy (2x/week) and occupational therapy (1x/week) through a "
        "separate provider. ABA treatment goals are coordinated with the SLP to avoid target overlap and ensure "
        "complementary communication approaches."
    )

    # -- Section 3: Assessment Results --
    add_heading_with_style(doc, "3. Standardized Assessment Results")

    add_heading_with_style(doc, "3.1 VB-MAPP (Verbal Behavior Milestones Assessment and Placement Program)", level=2)
    doc.add_paragraph("Date Administered: 10/02/2025")
    doc.add_paragraph("Previous Administration: 04/10/2025")
    doc.add_paragraph("Age Equivalent: 24-30 months")
    doc.add_paragraph("")

    add_table(doc,
        ["Domain", "Current Score", "Previous Score (04/2025)", "Change"],
        [
            ["Mand", "10.5", "8.0", "+2.5"],
            ["Tact", "7.0", "5.5", "+1.5"],
            ["Listener Responding", "6.5", "5.0", "+1.5"],
            ["Visual Perceptual Skills & MTS", "12.0", "10.5", "+1.5"],
            ["Independent Play", "5.0", "4.0", "+1.0"],
            ["Social Behavior & Social Play", "4.5", "3.5", "+1.0"],
            ["Motor Imitation", "9.0", "7.0", "+2.0"],
            ["Echoic", "11.5", "10.0", "+1.5"],
            ["Spontaneous Vocal Behavior", "3.5", "2.5", "+1.0"],
            ["LRFFC", "4.0", "3.0", "+1.0"],
            ["Intraverbal", "2.5", "1.5", "+1.0"],
            ["Classroom Routines & Group Skills", "3.0", "2.0", "+1.0"],
            ["Linguistic Structure", "4.5", "3.5", "+1.0"],
            ["Reading", "0.0", "0.0", "0.0"],
            ["Writing", "0.0", "0.0", "0.0"],
            ["Math", "1.0", "0.5", "+0.5"],
        ]
    )
    doc.add_paragraph(
        "\nClinical Interpretation: The client demonstrates a scatter profile consistent with ASD Level 2. "
        "Relative strengths are observed in Visual Perceptual Skills (12.0) and Echoic (11.5), which are being "
        "leveraged therapeutically to build weaker domains. The most significant deficits are in Intraverbal (2.5), "
        "Spontaneous Vocal Behavior (3.5), and Classroom Routines (3.0). Social Behavior (4.5) remains a core "
        "treatment target. All domains showed improvement from the prior administration, with the largest gains "
        "in Mand (+2.5) and Motor Imitation (+2.0)."
    )

    add_heading_with_style(doc, "3.2 Vineland Adaptive Behavior Scales, Third Edition (Vineland-3)", level=2)
    doc.add_paragraph("Date Administered: 10/08/2025 (Comprehensive Interview Form — Caregiver)")
    doc.add_paragraph("Previous Administration: 04/12/2025")
    add_table(doc,
        ["Domain", "Standard Score", "Percentile", "Age Equiv.", "Previous Score", "Change"],
        [
            ["Communication", "58", "0.3", "18 mo", "54", "+4"],
            ["Daily Living Skills", "68", "2", "28 mo", "65", "+3"],
            ["Socialization", "55", "0.1", "16 mo", "52", "+3"],
            ["Motor Skills", "78", "7", "32 mo", "76", "+2"],
            ["Adaptive Behavior Composite", "62", "1", "22 mo", "58", "+4"],
        ]
    )
    doc.add_paragraph(
        "\nClinical Interpretation: The Vineland-3 ABC score of 62 (1st percentile) reflects a developmental "
        "gap of approximately 26 months. The Socialization domain score of 55 (0.1st percentile, age equivalent "
        "16 months) represents the most significant area of impairment and is consistent with ASD-related social "
        "communication deficits. Improvement from the previous ABC of 58 to 62 indicates the client is making "
        "gains, though the rate of gain (4 points in 6 months) is slower than would be needed to close the "
        "developmental gap without continued intensive intervention."
    )

    add_heading_with_style(doc, "3.3 CARS-2 (Childhood Autism Rating Scale, Second Edition — Standard Form)", level=2)
    doc.add_paragraph("Date Administered: 10/08/2025")
    doc.add_paragraph("Previous Administration: 04/12/2025")
    add_table(doc,
        ["Metric", "Current", "Previous", "Change"],
        [
            ["Raw Score", "35.5", "37.0", "-1.5"],
            ["Classification", "Mild-to-Moderate Autism", "Moderate Autism", "Improved"],
        ]
    )
    doc.add_paragraph(
        "\nClinical Interpretation: The CARS-2 raw score decreased from 37.0 (moderate autism range) to 35.5 "
        "(mild-to-moderate range). Items contributing most to the current score include Relating to People, "
        "Emotional Response, and Adaptation to Change."
    )

    # -- Section 4: Skill Acquisition --
    add_heading_with_style(doc, "4. Skill Acquisition Progress")
    doc.add_paragraph(
        "During the current authorization period, 10 skill acquisition targets were actively programmed. "
        "The client mastered 5 targets (50% mastery rate). Detailed progress on each target is presented below."
    )

    add_table(doc,
        ["Domain", "Target", "Introduced", "Mastered", "Current %", "Criterion", "Gen.", "Notes"],
        [
            ["Manding", "Mands for missing items using carrier phrase 'I want ___'",
             "07/08/25", "09/19/25", "92%", "80%", "Yes",
             "Generalized across clinic, home, and community park settings with 3 different adults"],
            ["Manding", "Mands for actions using 2-word phrases (e.g., 'push me', 'open please')",
             "09/22/25", "—", "55%", "80%", "No",
             "Emerging with gestural prompt; independent in high-motivation contexts only (swing, bubbles)"],
            ["Tacting", "Tacts 50 common objects in natural environment",
             "07/08/25", "10/30/25", "88%", "80%", "Yes",
             "Mastered 53 items; generalizes across 2D images, 3D objects, and natural environment"],
            ["Tacting", "Tacts actions in pictures and videos (e.g., 'running', 'eating')",
             "08/12/25", "—", "40%", "80%", "No",
             "Identifies 8 of 20 target actions; errors concentrated on similar topography actions (jumping/hopping)"],
            ["Listener Responding", "Follows 2-step unrelated instructions (e.g., 'clap hands and touch nose')",
             "07/15/25", "—", "35%", "80%", "No",
             "Follows single-step instructions at 90% but loses second step; possible auditory processing component"],
            ["Social Skills", "Parallel play alongside peer for 3 minutes without disruptive behavior",
             "08/05/25", "11/04/25", "85%", "80%", "No",
             "Mastered in structured clinic setting; not yet tested in community or school settings"],
            ["Social Skills", "Initiates joint attention by showing or pointing to items of interest",
             "09/02/25", "—", "20%", "80%", "No",
             "Responds to joint attention bids at 60% but rarely initiates; critical ASD core deficit"],
            ["Daily Living", "Independent hand washing with visual schedule support",
             "07/22/25", "10/15/25", "90%", "80%", "Yes",
             "Completed all steps independently; visual schedule faded to last 2 steps only"],
            ["Daily Living", "Tolerates teeth brushing for 60 seconds without crying or turning head",
             "08/19/25", "—", "60%", "80%", "No",
             "Tolerates 40 seconds currently; systematic desensitization protocol in place"],
            ["Imitation", "Imitates 10 gross motor actions on request",
             "07/08/25", "08/28/25", "95%", "80%", "Yes",
             "Mastered all 10 actions; now serves as prerequisite for motor imitation sequences"],
        ]
    )

    # -- Section 5: Behavior Reduction --
    add_heading_with_style(doc, "5. Behavior Reduction Progress")

    add_heading_with_style(doc, "5.1 Aggression", level=2)
    doc.add_paragraph(
        "Operational Definition: Any instance of hitting, kicking, biting, scratching, or head-butting directed "
        "toward another person's body, with sufficient force to produce an audible sound, leave a visible mark, "
        "or cause the other person to vocalize in pain. Includes attempts where contact is made but intercepted "
        "by blocking."
    )
    doc.add_paragraph("Measurement: Frequency (episodes per hour)")
    doc.add_paragraph("Function: Escape from demands; access to tangibles (dual-maintained per FBA dated 01/20/2024)")
    add_table(doc,
        ["Metric", "Value"],
        [
            ["Baseline (07/01/2025)", "8.3 episodes/hr"],
            ["Current (11/10/2025)", "2.7 episodes/hr"],
            ["Reduction from Baseline", "67%"],
            ["Trend", "Decreasing"],
        ]
    )
    doc.add_paragraph(
        "Intervention Strategies:\n"
        "• Functional Communication Training (FCT) — teaching 'break please' and 'my turn'\n"
        "• Antecedent manipulation — demand fading with gradual increase\n"
        "• Noncontingent reinforcement (NCR) — 2-minute fixed-time schedule\n"
        "• Differential reinforcement of alternative behavior (DRA)\n"
        "• Response blocking for safety"
    )
    doc.add_paragraph(
        "Clinical Note: Aggression shows a clear decreasing trend. Spikes correlate with schedule changes "
        "and novel demands. The client now independently requests 'break please' in approximately 60% of "
        "demand situations where aggression previously occurred. The 2-minute NCR schedule has been thinned "
        "from the initial 30-second schedule. Aggression remains above the discharge criterion of <1.0/hr."
    )

    add_heading_with_style(doc, "5.2 Vocal Stereotypy", level=2)
    doc.add_paragraph(
        "Operational Definition: Repetitive vocalizations that are not communicative in context, including "
        "scripting from videos/TV, repetitive humming lasting more than 3 seconds, and echolalic utterances "
        "not directed at a communication partner. Scored as percentage of 10-second partial intervals during "
        "structured instruction."
    )
    doc.add_paragraph("Measurement: Partial interval recording (10-second intervals)")
    doc.add_paragraph("Function: Automatic/sensory reinforcement (per FBA dated 01/20/2024)")
    add_table(doc,
        ["Metric", "Value"],
        [
            ["Baseline (07/01/2025)", "45% of intervals"],
            ["Current (11/10/2025)", "32% of intervals"],
            ["Reduction from Baseline", "29%"],
            ["Trend", "Decreasing"],
        ]
    )
    doc.add_paragraph(
        "Intervention Strategies:\n"
        "• Response interruption and redirection (RIRD)\n"
        "• Differential reinforcement of other behavior (DRO) — 1-minute momentary\n"
        "• Increased opportunities for functional vocal behavior"
    )
    doc.add_paragraph(
        "Clinical Note: Vocal stereotypy has decreased but remains above the 20% discharge criterion. "
        "The behavior is most prevalent during transition times and low-structure periods. RIRD has been "
        "effective in reducing duration of episodes. The team has increased structured vocal responding "
        "opportunities (tacting, manding) as competing behavior."
    )

    add_heading_with_style(doc, "5.3 Elopement", level=2)
    doc.add_paragraph(
        "Operational Definition: Leaving or attempting to leave the designated therapeutic area (therapy room, "
        "fenced playground, or parent-defined boundary) without adult permission, defined as any movement of "
        "both feet beyond the boundary or sustained contact with exit points (door handles, gate latches) "
        "lasting more than 2 seconds."
    )
    doc.add_paragraph("Measurement: Frequency (episodes per hour)")
    doc.add_paragraph("Function: Escape from demands (per FBA dated 01/20/2024)")
    add_table(doc,
        ["Metric", "Value"],
        [
            ["Baseline (07/01/2025)", "3.1 episodes/hr"],
            ["Current (11/10/2025)", "0.8 episodes/hr"],
            ["Reduction from Baseline", "74%"],
            ["Trend", "Decreasing"],
        ]
    )
    doc.add_paragraph(
        "Intervention Strategies:\n"
        "• Environmental arrangement — secured exits with adult supervision\n"
        "• FCT — requesting 'go outside' or 'all done' appropriately\n"
        "• Premack principle — access to preferred outdoor activity contingent on task completion\n"
        "• Visual schedule to increase predictability"
    )
    doc.add_paragraph(
        "Clinical Note: Elopement has shown the most significant reduction of all behavior targets. "
        "The client now uses 'all done' independently in approximately 70% of situations where elopement "
        "previously occurred. Remaining instances are concentrated during transitions between activities "
        "and when novel staff are present."
    )

    # -- Section 6: Treatment Goals --
    add_heading_with_style(doc, "6. Treatment Plan & Goal Status")

    for goal in [
        {
            "num": 1, "area": "Communication",
            "statement": "Client will independently use 2-3 word mand frames to request desired items, actions, and cessation of non-preferred activities across 3 settings with 80% accuracy over 5 consecutive sessions.",
            "baseline": "Client used single-word mands for 12 items with gestural prompts in clinic setting only.",
            "current": "Client independently mands using carrier phrase 'I want ___' for 25+ items across 2 settings; 2-word action mands at 55%.",
            "status": "In Progress",
            "mod": None,
        },
        {
            "num": 2, "area": "Social Skills",
            "statement": "Client will engage in reciprocal play interactions with a peer for 5 minutes, including turn-taking and joint attention, with no more than 1 adult prompt per interaction across 3 consecutive opportunities.",
            "baseline": "Client engaged in solitary play only; no peer-directed social initiations observed.",
            "current": "Client engages in parallel play for 3+ minutes; responds to joint attention at 60%; initiates joint attention at 20%.",
            "status": "In Progress",
            "mod": None,
        },
        {
            "num": 3, "area": "Behavior Reduction",
            "statement": "Client will reduce aggression to fewer than 1.0 episodes per hour across all settings for 4 consecutive weeks, using functionally equivalent replacement behaviors.",
            "baseline": "Aggression at 8.3 episodes per hour, dual-maintained by escape and tangible access.",
            "current": "Aggression at 2.7 episodes per hour, 67% reduction from baseline.",
            "status": "In Progress",
            "mod": None,
        },
        {
            "num": 4, "area": "Adaptive Behavior",
            "statement": "Client will independently complete 5 daily living skill routines (hand washing, teeth brushing, putting on shoes, putting on coat, cleaning up toys) with no more than visual schedule support.",
            "baseline": "Client completed 0 of 5 routines independently; required full physical prompting for all.",
            "current": "Client independently completes hand washing and imitation tasks; teeth brushing at 60%; shoes and coat not yet introduced.",
            "status": "Modified",
            "mod": "Original goal included 7 routines; modified to 5 highest-priority routines after team discussion with caregivers. Shoes and coat deferred to next auth period to prioritize hygiene routines and safety skills.",
        },
    ]:
        add_heading_with_style(doc, f"Goal {goal['num']}: {goal['area']}", level=2)
        doc.add_paragraph(f"Goal Statement: {goal['statement']}")
        doc.add_paragraph(f"Baseline Performance: {goal['baseline']}")
        doc.add_paragraph(f"Current Performance: {goal['current']}")
        doc.add_paragraph(f"Status: {goal['status']}")
        if goal["mod"]:
            doc.add_paragraph(f"Modification Rationale: {goal['mod']}")

    # -- Section 7: Hours Utilization --
    add_heading_with_style(doc, "7. Hours Utilization")
    add_table(doc,
        ["CPT Code", "Description", "Authorized Units", "Utilized Units", "Utilization %", "Notes"],
        [
            ["97153", "Adaptive Behavior Treatment by Protocol", "624", "580", "92.9%", "—"],
            ["97155", "Adaptive Behavior Treatment — Protocol Modification", "96", "88", "91.7%", "—"],
            ["97156", "Family Adaptive Behavior Treatment Guidance", "48", "36", "75.0%",
             "Family cancelled 4 sessions due to illness (gastroenteritis outbreak at sibling's daycare) "
             "and 2 sessions due to caregiver work schedule changes. Make-up sessions offered but not all "
             "could be rescheduled within the auth period."],
            ["97151", "Behavior Identification Assessment", "24", "24", "100%", "—"],
        ]
    )
    doc.add_paragraph(
        "\nTotal authorized units: 792 | Total utilized units: 728 | Overall utilization: 91.9%"
    )

    # -- Section 8: Requested Hours --
    add_heading_with_style(doc, "8. Requested Hours for Next Authorization Period")
    doc.add_paragraph("Authorization Period Requested: 01/01/2026 – 06/30/2026")
    add_table(doc,
        ["CPT Code", "Description", "Weekly Units Requested", "Total Units (26 weeks)"],
        [
            ["97153", "Adaptive Behavior Treatment by Protocol", "24", "624"],
            ["97155", "Protocol Modification (BCBA supervision)", "4", "104"],
            ["97156", "Family Adaptive Behavior Treatment Guidance", "2", "52"],
            ["97151", "Behavior Identification Assessment", "1", "26"],
        ]
    )
    doc.add_paragraph(
        "\nClinical Justification: The client's Level 2 ASD diagnosis with co-occurring mixed receptive-expressive "
        "language disorder necessitates continued intensive intervention. While significant progress has been made "
        "(67% reduction in aggression, 74% reduction in elopement, 5 of 10 skill targets mastered), the client "
        "has met 0 of 6 discharge criteria. Ongoing safety concerns (aggression at 2.7/hr), core ASD deficits "
        "in joint attention (20%) and social reciprocity, and the need for continued caregiver training support "
        "the requested intensity. The Vineland-3 ABC of 62 (1st percentile) confirms substantial adaptive "
        "behavior deficits requiring intensive intervention."
    )

    # -- Section 9: Caregiver Training --
    add_heading_with_style(doc, "9. Caregiver Training Summary")
    doc.add_paragraph("Total Sessions Conducted: 14 (of 24 authorized)")
    doc.add_paragraph(
        "Topics Covered:\n"
        "• Functional Communication Training implementation at home\n"
        "• Antecedent strategies for aggression prevention\n"
        "• 3-step prompting hierarchy for manding\n"
        "• Visual schedule creation and use for daily routines\n"
        "• Data collection on behavior frequency (simplified tally method)\n"
        "• Naturalistic teaching strategies during mealtimes and play\n"
        "• Response blocking for aggression — safety procedures\n"
        "• Generalization strategies across home and community settings\n"
        "• Toilet training readiness assessment and initial protocol"
    )
    doc.add_paragraph(
        "Caregiver Skill Acquisition: Primary caregiver (mother) demonstrates FCT implementation with 82% "
        "fidelity and correct use of 3-step prompting hierarchy with 88% fidelity. Father participates in "
        "alternate sessions and demonstrates prompting at 75% fidelity. Both caregivers can independently "
        "implement visual schedules for hand washing and mealtimes."
    )
    doc.add_paragraph(
        "Barriers to Participation: Father's rotating work schedule limits attendance to every other session. "
        "Family illness (October) resulted in 4 cancelled sessions. Language barrier — sessions conducted in "
        "English with occasional Spanish interpretation; bilingual materials provided."
    )

    # -- Section 10: Medical Necessity --
    add_heading_with_style(doc, "10. Medical Necessity Statement")
    doc.add_paragraph(
        "Continued intensive ABA services are medically necessary for this 4-year-old client diagnosed with "
        "Autism Spectrum Disorder, Level 2 (F84.0) and Mixed Receptive-Expressive Language Disorder (F80.2)."
    )
    doc.add_paragraph(
        "Functional Impairment: The Vineland-3 Adaptive Behavior Composite score of 62 (1st percentile, age "
        "equivalent 22 months) reflects a developmental gap of approximately 26 months. The Socialization "
        "domain score of 55 represents the most significant impairment area. VB-MAPP assessment reveals "
        "critical deficits in Intraverbal skills (2.5), Spontaneous Vocal Behavior (3.5), and Social Behavior "
        "(4.5) — all domains directly related to ASD core deficits."
    )
    doc.add_paragraph(
        "Risk of Regression: Without continued services, the client is at significant risk of regression. "
        "Aggression, while reduced by 67%, remains at 2.7 episodes per hour. Without ongoing FCT and behavioral "
        "programming, regression to baseline levels (8.3/hr) is likely, as replacement behaviors are not yet "
        "fully established. Elopement at 0.8 episodes per hour remains a safety concern. Vocal stereotypy at "
        "32% of intervals interferes with learning and would likely increase without intervention."
    )
    doc.add_paragraph(
        "ASD Core Deficits: Social communication deficits (joint attention initiation at 20%, peer interaction "
        "requiring adult facilitation), restricted/repetitive behaviors (vocal stereotypy at 32%), and functional "
        "communication limitations (2-word mand frames at 55%) are directly connected to the client's ASD diagnosis."
    )
    doc.add_paragraph(
        "Intensity Justification: The requested intensity of 24 weekly units of direct service (97153), 4 weekly "
        "units of supervision (97155), 2 weekly units of caregiver training (97156), and 1 weekly unit of "
        "assessment (97151) is appropriate given the severity of deficits (Vineland ABC 1st percentile), the "
        "number of active treatment goals (4 goals, 10 skill targets), ongoing safety concerns, and the client's "
        "demonstrated responsiveness to treatment. The client has met 0 of 6 discharge criteria."
    )

    # -- Section 11: Discharge Plan --
    add_heading_with_style(doc, "11. Discharge Plan")
    doc.add_paragraph("Discharge from intensive ABA services will be recommended when the following criteria are met:")
    doc.add_paragraph(
        "1. Aggression below 1.0 episodes per hour for 4 consecutive weeks across all settings (currently 2.7/hr)\n"
        "2. Elopement below 0.3 episodes per hour for 4 consecutive weeks (currently 0.8/hr)\n"
        "3. Vocal stereotypy below 20% of intervals during structured instruction (currently 32%)\n"
        "4. Mastery of 80% of current skill acquisition targets with generalization across 3 settings (currently 50% mastered)\n"
        "5. Caregiver implementation fidelity above 90% for FCT and prompting procedures (currently 82-88% mother, 75% father)\n"
        "6. Vineland-3 ABC score at or above 70 (currently 62)"
    )
    doc.add_paragraph("Criteria Met: 0 of 6")
    doc.add_paragraph(
        "Transition Plan: Phase 1 — reduce to 20 hours/week direct service with maintained supervision. "
        "Phase 2 — reduce to 12 hours/week focused on social skills and community integration. "
        "Phase 3 — transition to consultation model (5 hours/week) with monthly BCBA check-ins. "
        "Final transition to school-based services with IEP consultation."
    )
    doc.add_paragraph(
        "Current Discharge Readiness: The client has met 0 of 6 discharge criteria. Substantial progress "
        "on aggression (67% reduction) and elopement (74% reduction) but not yet at criterion levels. "
        "Continued intensive services strongly recommended."
    )

    # -- Signatures --
    doc.add_page_break()
    add_heading_with_style(doc, "12. Signatures & Attestation")
    doc.add_paragraph(
        "I certify that the information in this report is accurate and reflects the clinical data from the "
        "current authorization period. I have personally supervised this client's ABA program and reviewed "
        "all data presented herein."
    )
    doc.add_paragraph("")
    doc.add_paragraph("_____________________________________________")
    doc.add_paragraph("Dr. Maria Gonzalez, BCBA-D")
    doc.add_paragraph("Credential #1-19-42831 | NPI: 1987654321")
    doc.add_paragraph("Date: 11/15/2025")
    doc.add_paragraph("")
    doc.add_paragraph("_____________________________________________")
    doc.add_paragraph("Carlos Mendez, RBT")
    doc.add_paragraph("Credential #RBT-20230198")
    doc.add_paragraph("Date: 11/15/2025")

    # Save
    out_path = Path(__file__).parent / "sample_progress_report.docx"
    doc.save(str(out_path))
    print(f"Generated: {out_path}")
    return out_path


if __name__ == "__main__":
    generate()
