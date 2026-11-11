"""Fictional new-period progress reports, the input to extraction and generation.

complete_report(): every section filled in, table-heavy (Word).
gappy_report(): realistic holes -- no assessment results, no caregiver training, low
hours with no explanation, no discharge criteria, a behavior with no baseline (PDF).
All people, clinics, IDs and numbers are invented.
"""

CLINIC = "Harborview Behavior Therapy"


def complete_report() -> list[tuple]:
    return [
        ("title", "Progress Report and Reauthorization Request",
         f"{CLINIC}\nAuthorization period: 01/01/2026 – 06/30/2026"),
        ("h", "1. Client Information"),
        ("kv", [
            ("Client ID", "HB-2025-0311"),
            ("Age at time of report", "6 years, 4 months"),
            ("Primary diagnosis", "Autism Spectrum Disorder, Level 2 (F84.0)"),
            ("Secondary diagnosis", "Language Disorder (F80.9)"),
            ("Payor", "Aetna"),
            ("Authorization period", "01/01/2026 – 06/30/2026"),
            ("Supervising BCBA", "Dr. Priya Raman, BCBA-D"),
            ("BCBA credential #", "1-20-51377"),
            ("Service locations", "Clinic (primary), home (secondary)"),
        ]),
        ("h", "2. Background"),
        ("p", "Sam is a 6-year-old who began ABA services at Harborview in September 2024. He lives with his "
              "parents and a younger brother. English and Korean are spoken at home. He attends kindergarten full "
              "time with a shared aide. He receives speech-language therapy twice weekly through a separate provider, "
              "and treatment goals are coordinated to avoid overlap."),
        ("h", "3. Standardized Assessments"),
        ("table", ["Assessment", "Date", "Domain", "Current", "Previous (07/2025)", "Change"], [
            ["VB-MAPP", "06/10/2026", "Mand", "11.0", "9.0", "+2.0"],
            ["VB-MAPP", "06/10/2026", "Tact", "10.5", "8.5", "+2.0"],
            ["VB-MAPP", "06/10/2026", "Intraverbal", "7.0", "5.0", "+2.0"],
            ["VB-MAPP", "06/10/2026", "Social Behavior & Social Play", "6.5", "5.0", "+1.5"],
            ["VB-MAPP", "06/10/2026", "Total", "98.5", "84.0", "+14.5"],
            ["Vineland-3 ABC", "06/12/2026", "Adaptive Behavior Composite", "72", "66", "+6"],
        ]),
        ("h", "4. Skill Acquisition"),
        ("table", ["Domain", "Target", "Status", "Accuracy", "Criterion", "Generalized"], [
            ["Manding", "Mands for 30 items independently", "Mastered 03/2026", "92%", "80%", "Yes"],
            ["Tacting", "Tacts actions in pictures", "Mastered 04/2026", "88%", "80%", "Yes"],
            ["Intraverbal", "Answers 'wh' questions about routines", "In progress", "68%", "80%", "No"],
            ["Social skills", "Takes turns in a 3-step game", "In progress", "74%", "80%", "No"],
            ["Daily living", "Dresses independently (6 steps)", "Mastered 05/2026", "95%", "90%", "Yes"],
            ["Play", "Plays cooperatively for 5 minutes", "In progress", "60%", "80%", "No"],
        ]),
        ("h", "5. Behavior Reduction"),
        ("table", ["Behavior", "Measure", "Baseline (09/2025)", "Current (06/2026)", "Trend", "Function"], [
            ["Aggression (hitting or kicking others)", "Rate per hour", "3.4", "0.6", "Decreasing", "Escape from demands"],
            ["Task refusal (verbal or physical)", "Rate per hour", "7.8", "2.2", "Decreasing", "Escape from demands"],
            ["Elopement from designated area", "Episodes per week", "2.5", "0.2", "Decreasing", "Access to preferred items"],
        ]),
        ("p", "Interventions include functional communication training for requesting breaks, a token economy, "
              "and differential reinforcement of alternative behavior."),
        ("h", "6. Treatment Goals"),
        ("table", ["#", "Area", "Goal", "Baseline", "Current", "Status"], [
            ["1", "Communication", "Answer 'wh' questions about routines at 80% across 3 sessions", "20%", "68%", "In progress"],
            ["2", "Social skills", "Take turns in games with a peer at 80% across 3 sessions", "25%", "74%", "In progress"],
            ["3", "Behavior reduction", "Reduce aggression to below 0.5 per hour for 4 weeks", "3.4 per hour", "0.6 per hour", "In progress"],
            ["4", "Adaptive", "Dress independently at 90%", "30%", "95%", "Met"],
        ]),
        ("h", "7. Hours Utilization"),
        ("table", ["CPT code", "Service", "Authorized units", "Utilized units", "Utilization"], [
            ["97153", "Direct treatment", "2,080", "1,872", "90%"],
            ["97155", "Supervision", "156", "148", "95%"],
            ["97156", "Caregiver training", "52", "44", "85%"],
        ]),
        ("p", "Requested for the next period: 97153 at 16 hours per week, 97155 at 1.5 hours per week, "
              "97156 at 1 hour per week. Hours are reduced from the current period because of Sam's gains in "
              "daily living skills and reduced behavior."),
        ("h", "8. Caregiver Training"),
        ("p", "Parents completed 11 sessions covering prompting, reinforcement, and managing refusal at home. "
              "Sam's mother runs the evening routine at 88% fidelity. The main barrier was parent work schedules, "
              "addressed by adding recorded video feedback between sessions."),
        ("h", "9. Discharge and Transition Plan"),
        ("table", ["Criterion", "Benchmark"], [
            ["Aggression", "Below 0.5 per hour for 12 consecutive weeks"],
            ["Task refusal", "Below 1.0 per hour for 12 consecutive weeks"],
            ["Intraverbal skills", "'Wh' questions at 80% across settings"],
            ["Caregiver fidelity", "90% across core routines"],
        ]),
        ("p", "Estimated discharge to a lower level of care: 12 months. Transition will be coordinated with the "
              "school team, with a step-down to school-based consultation."),
    ]


def gappy_report() -> list[tuple]:
    return [
        ("title", "ABA Progress Summary", f"{CLINIC}\nPeriod: 07/01/2025 – 12/31/2025"),
        ("h", "Client Information"),
        ("kv", [
            ("Client ID", "HB-2025-0422"),
            ("Age", "4 years"),
            ("Diagnosis", "Autism Spectrum Disorder (F84.0)"),
            ("Payor", "Anthem Blue Cross California"),
            ("Supervising BCBA", "Marcus Ellery, MS, BCBA"),
        ]),
        ("h", "Overview"),
        ("p", "Devon started services in April 2025 and has made steady progress overall. He is more engaged during "
              "sessions and is using more words to request items."),
        ("h", "Skill Acquisition"),
        ("table", ["Target", "Status", "Accuracy"], [
            ["Mands for 10 items", "Mastered", "85%"],
            ["Imitates 5 gross motor actions", "In progress", "60%"],
            ["Matches identical pictures", "In progress", "72%"],
            ["Responds to name", "Mastered", "90%"],
        ]),
        ("h", "Behavior"),
        ("table", ["Behavior", "Measure", "Baseline", "Current"], [
            ["Crying during transitions", "Episodes per day", "8", "3"],
            ["Throwing materials", "Episodes per session", "", "2"],
        ]),
        ("p", "Throwing materials was added mid-period, and a baseline was not recorded."),
        ("h", "Goals"),
        ("p", "Continue to improve communication and reduce challenging behavior. Increase play skills."),
        ("h", "Hours"),
        ("table", ["Service", "Authorized units", "Used units"], [
            ["97153 Direct treatment", "1,560", "910"],
            ["97155 Supervision", "117", "60"],
        ]),
        ("p", "Requesting the same level of services for the next period."),
    ]
