"""Fictional past reauthorization reports, used to test the template library.

All people, clinics, IDs and numbers are invented. Each uses a different layout so
template extraction has to pick up genuinely different structures.
"""

CLINIC = "Harborview Behavior Therapy"


def anthem_style_report() -> list[tuple]:
    """Narrative-heavy Word report: nine sections with plain-language headings."""
    return [
        ("title", "ABA Reauthorization Request", f"{CLINIC}\nPrepared for Anthem Blue Cross California"),
        ("kv", [
            ("Client ID", "HB-2024-0156"),
            ("Diagnosis", "Autism Spectrum Disorder, Level 2 (F84.0)"),
            ("Authorization period", "01/01/2025 – 06/30/2025"),
            ("Supervising BCBA", "Dr. Priya Raman, BCBA-D"),
        ]),
        ("h", "Reason for Request"),
        ("p", "Riley is a 5-year-old who has received comprehensive ABA services at Harborview since March 2024. "
              "This report requests continued authorization for the period beginning July 1, 2025, and documents "
              "progress made during the current authorization period."),
        ("h", "Background and Current Functioning"),
        ("p", "Riley lives at home with both parents and an older sister. He communicates primarily with single words "
              "and two-word phrases and uses a tablet-based device to support requesting. He attends a half-day "
              "preschool program three mornings per week, where a one-to-one aide is provided by the district."),
        ("p", "At the start of this period Riley required full physical prompts for most self-care routines and "
              "engaged in frequent protest behavior during transitions. His family reported that community outings "
              "were being avoided as a result."),
        ("h", "Assessment Results"),
        ("p", "The VB-MAPP was re-administered on 05/20/2025. Riley's total score increased from 52.5 to 64.0. The "
              "largest gains were in Mand (+3.5), Tact (+2.5) and Listener Responding (+2.0). Scores on the Vineland-3 "
              "Adaptive Behavior Composite moved from 61 to 67, with the greatest improvement in the Daily Living "
              "Skills domain."),
        ("h", "Skill Acquisition Progress"),
        ("p", "Of 18 active skill targets, 11 were mastered during this period (61%). Riley now mands for 25 items "
              "independently across three settings, up from 9 at the start of the period. Tacting of common objects "
              "reached 86% accuracy across two consecutive weeks and has generalized to a new instructor. Two "
              "targets related to peer play were modified from 80% to 70% criterion after data showed a plateau, "
              "with added peer-mediated prompts."),
        ("h", "Behavior Reduction Progress"),
        ("p", "Transition-related protest (screaming and dropping to the floor) decreased from a baseline of 6.2 "
              "episodes per hour to 1.4 episodes per hour, a 77% reduction. The behavior is maintained by escape from "
              "non-preferred activities. Interventions include visual schedules, first-then boards and differential "
              "reinforcement of calm transitions. Elopement from the treatment area has not occurred since March."),
        ("h", "Caregiver Involvement"),
        ("p", "Parents attended 14 of 16 scheduled training sessions. Topics included prompting hierarchies, "
              "reinforcement schedules and managing transitions at home. Riley's mother now independently runs the "
              "bedtime routine with 90% treatment fidelity. Schedule conflicts with his father's shift work were the "
              "main barrier, and evening sessions were added to address it."),
        ("h", "Hours Requested and Rationale"),
        ("p", "Direct treatment (97153) was authorized for 30 hours per week, with 28 delivered on average (93%). "
              "Supervision (97155) was delivered at 6% of direct hours. For the next period we request 28 hours per "
              "week of direct treatment, 2 hours of supervision, and 1.5 hours of caregiver training (97156), "
              "reflecting reduced prompting needs in self-care while maintaining intensity for communication and "
              "social goals."),
        ("h", "Medical Necessity"),
        ("p", "Without continued intensive services Riley is at significant risk of regression in functional "
              "communication and a return of transition-related behavior that previously prevented participation in "
              "preschool and community activities. His core deficits in social communication and flexibility "
              "continue to impair daily functioning at home and at school. The requested intensity is consistent "
              "with the severity of these impairments and with his rate of progress to date."),
        ("h", "Transition and Discharge Planning"),
        ("p", "Discharge criteria include independent use of functional communication across settings, a sustained "
              "transition protest rate below 0.5 per hour for three months, and caregivers running all core routines "
              "at 90% fidelity. Based on current progress we estimate a step-down to a lower intensity in 12 to 18 "
              "months, coordinated with the school team."),
    ]


def carelon_style_report() -> list[tuple]:
    """Clinical-form PDF: member header, changes since last report, goal-by-goal progress."""
    return [
        ("title", "Provider Treatment Report — Concurrent Review", f"{CLINIC}\nSubmitted to Carelon Behavioral Health"),
        ("h", "1. Member Identifying Information"),
        ("kv", [
            ("Member ID (internal)", "HB-2024-0207"),
            ("Age", "8 years"),
            ("Diagnosis", "F84.0 Autism Spectrum Disorder"),
            ("Report period", "07/01/2025 – 12/31/2025"),
            ("Treating BCBA", "Marcus Ellery, MS, BCBA"),
        ]),
        ("h", "2. Changes Since Last Assessment or Treatment Report"),
        ("p", "Since the previous report the member changed schools in September and now attends a general-education "
              "classroom with a shared aide. His family relocated, so home-based sessions moved from a weekday "
              "evening to a weekend morning. No changes to medication."),
        ("h", "3. Summary of Program History"),
        ("p", "Services began in 2022. Early programming focused on functional communication, compliance and "
              "self-care. Current programming centers on conversation skills, peer interaction and independence "
              "in school routines."),
        ("h", "4. Progress by Goal"),
        ("table", ["Goal", "Baseline", "Current", "Criterion", "Status"], [
            ["Initiate a conversation with a peer", "0 per day", "3 per day", "5 per day, 3 sessions", "In progress"],
            ["Complete morning routine independently", "40%", "85%", "90%, 5 days", "In progress"],
            ["Request a break appropriately", "20%", "92%", "90%, 3 sessions", "Met"],
            ["Reduce task refusal", "5.0 per hour", "1.1 per hour", "Below 1.0 per hour", "In progress"],
        ]),
        ("p", "Data is reported per goal as collected. Graphs for each goal are attached to the original submission."),
        ("h", "5. Assessment Results"),
        ("p", "The ABLLS-R was re-administered in November. The member now scores 71% of items in the Social "
              "Interaction domain, up from 54%. A Vineland-3 update is scheduled for the next period."),
        ("h", "6. Coordination of Care"),
        ("p", "The BCBA met with the school team twice and with the member's speech-language pathologist monthly. "
              "Goals were aligned to avoid overlap, and a shared communication log is used with the classroom aide."),
        ("h", "7. Parent and Caregiver Training"),
        ("p", "Caregivers completed 10 training sessions focused on prompting at homework time and on reinforcing "
              "independent morning routines. Both parents now run the routine with 85% fidelity."),
        ("h", "8. Transition and Discharge Plan"),
        ("p", "The team is moving toward a school-based consultation model. Criteria for reducing hours include "
              "task refusal below 1.0 per hour for eight consecutive weeks and independent morning routine at 90% "
              "for four weeks."),
        ("h", "9. Recommended Services"),
        ("table", ["Service", "Code", "Current / week", "Requested / week"], [
            ["Direct treatment", "97153", "20 hours", "16 hours"],
            ["Supervision", "97155", "3 hours", "2.5 hours"],
            ["Caregiver training", "97156", "1 hour", "1 hour"],
        ]),
        ("p", "Hours are requested at a lower level than the current period because of the member's progress and "
              "his increased time in the classroom."),
    ]
