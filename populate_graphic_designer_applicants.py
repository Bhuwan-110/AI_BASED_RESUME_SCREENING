"""
Script to create Graphic Designer vacancy and 15 applicants with PDF CVs
complying with the exact user requirements:
- 5 CVs matching ~82%, ~80%, ~80%, ~75%, ~60%
- Other CVs below them (descending from ~48% down to ~6%)
- 2 CVs matching ~2% due to being completely non-field persons
"""

import os
import sys
import io
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurukul.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job
from applications.models import Application
from resume_ai.models import ResumeExtraction, ResumeScreening, ResumeAnalysis
from resume_ai.service import calculate_resume_match
from resume_ai.ml_service import ResumeMLService

def create_pdf_bytes(lines):
    """Generates standard compliant PDF bytes with no third-party dependencies."""
    content = "BT /F1 11 Tf 50 750 Td 14 TL\n"
    for line in lines:
        escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        content += f"({escaped}) Tj T*\n"
    content += "ET"
    stream_bytes = content.encode('latin1', errors='replace')

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    obj4 = f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode('latin1') + stream_bytes + b"\nendstream\nendobj\n"
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    header = b"%PDF-1.4\n"
    offsets = [0]
    pos = len(header)
    offsets.append(pos)
    pos += len(obj1)
    offsets.append(pos)
    pos += len(obj2)
    offsets.append(pos)
    pos += len(obj3)
    offsets.append(pos)
    pos += len(obj4)
    offsets.append(pos)
    pos += len(obj5)

    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode('latin1')

    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF\n".encode('latin1')
    return header + obj1 + obj2 + obj3 + obj4 + obj5 + xref + trailer

def calibrate_text_to_score(base_text, desc, skills, qual, exp, target_pct, is_nonfield=False):
    """Fine-tunes the text so that calculate_resume_match hits the desired target percentage."""
    best_text = base_text
    best_diff = 999.0
    best_score = 0.0

    # Filler vocabulary for controlling dilution without changing core meaning
    dilution_words = [
        "curriculum", "institution", "academic", "student", "faculty", "administrative",
        "documentation", "management", "communication", "coordination", "leadership",
        "presentation", "evaluation", "assessment", "collaboration", "headquarters",
        "portfolio", "deliverables", "review", "stakeholder", "schedule", "reporting"
    ]

    # Non-field filler words
    mechanical_words = [
        "hydraulic", "caterpillar", "diesel", "transmission", "excavator", "bulldozer",
        "engine", "cylinder", "pneumatic", "crane", "rigging", "lubrication", "welding",
        "machinery", "quarry", "haulage", "earthmoving", "chassis", "torque", "gearbox",
        "flange", "piston", "manifold", "radiator", "axle", "drilling", "heavy", "mechanic"
    ]

    marine_words = [
        "trawler", "vessel", "offshore", "deckhand", "anchorage", "navigation", "maritime",
        "haul", "nets", "seamanship", "buoy", "cargo", "crane", "tide", "harbor", "sonar",
        "rigging", "winch", "hull", "marine", "diesel", "captain", "crew", "safety", "berth"
    ]

    if is_nonfield:
        pool = mechanical_words if "Mechanic" in base_text else marine_words
        # For nonfield, we want exactly ~2% match. We add 1 common word like 'course' or 'learning'
        # and adjust the amount of nonfield text until it lands on ~2.0%
        for n in range(20, 150, 5):
            extra = " ".join((pool * 10)[:n])
            # add single overlapping word 'course'
            candidate = f"{base_text}\nCompleted preparatory safety training course certification.\nEquipment details: {extra}"
            res = calculate_resume_match(desc, skills, candidate, qual, exp)
            score = res['match_percentage']
            diff = abs(score - target_pct)
            if diff < best_diff:
                best_diff = diff
                best_score = score
                best_text = candidate
        return best_text, best_score

    # For design candidates:
    # We test combinations of repeating the core matching keywords and adding neutral dilution words
    core_kw = "photoshop illustrator figma canva after effects typography graphic designer visual learning infographics diagrams banners layouts"
    
    for r in range(1, 8):
        for d in range(0, 100, 4):
            core_part = (" " + core_kw) * r
            dilution_part = " ".join((dilution_words * 10)[:d])
            candidate = f"{base_text}\nKey Competencies: {core_part}\nAdditional institutional background: {dilution_part}"
            res = calculate_resume_match(desc, skills, candidate, qual, exp)
            score = res['match_percentage']
            diff = abs(score - target_pct)
            if diff < best_diff:
                best_diff = diff
                best_score = score
                best_text = candidate
            if diff < 0.3:
                break
        if best_diff < 0.3:
            break

    return best_text, best_score

def main():
    print("Setting up Graphic Designer Vacancy and 15 Candidates...")

    # 1. Setup or retrieve Graphic Designer Job
    job = Job.objects.filter(id=15).first()
    if not job:
        job = Job.objects.filter(title__icontains="Graphic Designer").first()

    if not job:
        job = Job.objects.create(
            title="Graphic Designer & Visual Media Specialist",
            department="Curriculum & Content",
            description="Looking for a creative Graphic Designer to create Loksewa preparation diagrams, visual learning infographics, course banners, and academic publishing layouts.",
            required_skills="Photoshop, Illustrator, Figma, Canva, After Effects, Typography",
            qualification="Bachelor's in Graphic Design, Fine Arts, or Multimedia",
            experience="2+ Years",
            job_type="Full Time",
            location="Kathmandu (Putalisadak) / Hybrid",
            deadline=timezone.now().date() + timedelta(days=30)
        )
    else:
        job.title = "Graphic Designer & Visual Media Specialist"
        job.description = "Looking for a creative Graphic Designer to create Loksewa preparation diagrams, visual learning infographics, course banners, and academic publishing layouts."
        job.required_skills = "Photoshop, Illustrator, Figma, Canva, After Effects, Typography"
        job.qualification = "Bachelor's in Graphic Design, Fine Arts, or Multimedia"
        job.experience = "2+ Years"
        job.deadline = timezone.now().date() + timedelta(days=30)
        job.save()

    print(f"Target Vacancy: {job.title} (ID: {job.id})")

    # Clean existing applications for this job if any so we have a clean set of exactly 15 applicants
    existing_apps = Application.objects.filter(job=job)
    print(f"Removing {existing_apps.count()} pre-existing applications for Job {job.id}...")
    existing_apps.delete()

    # Define the 15 candidate specifications
    candidates_spec = [
        # 5 Top matches: 82%, 80%, 80%, 75%, 60%
        {
            "username": "aarav_designer_82",
            "full_name": "Aarav Sharma",
            "email": "aarav.sharma@example.com",
            "target_score": 82.0,
            "base_text": "Aarav Sharma - Senior Graphic Designer & Visual Media Specialist\nEducation: Bachelor's in Graphic Design\nExperience: 4 years of professional experience in graphic design and visual publishing\nProficiency: Photoshop, Illustrator, Figma, Canva, After Effects, Typography\nDuties: Create Loksewa preparation diagrams, visual learning infographics, course banners, academic publishing layouts.",
            "is_nonfield": False
        },
        {
            "username": "pooja_visual_80a",
            "full_name": "Pooja Shrestha",
            "email": "pooja.shrestha@example.com",
            "target_score": 80.0,
            "base_text": "Pooja Shrestha - Creative Graphic Designer & Digital Illustrator\nEducation: Bachelor's in Multimedia Arts\nExperience: 3 years of work experience creating infographics and educational layouts\nSkills: Illustrator, Photoshop, Figma, Canva, Typography, After Effects\nSpecialization: Visual learning infographics, course banners, academic layouts, Loksewa diagrams.",
            "is_nonfield": False
        },
        {
            "username": "rohan_graphics_80b",
            "full_name": "Rohan Adhikari",
            "email": "rohan.adhikari@example.com",
            "target_score": 80.0,
            "base_text": "Rohan Adhikari - Lead Visual Media & Layout Designer\nEducation: Bachelor's in Fine Arts (Graphic Design)\nExperience: 3.5 years of experience in publication graphics\nTechnical Skills: Photoshop, Illustrator, Typography, Figma, After Effects, Canva\nResponsibilities: Academic publishing layouts, Loksewa preparation diagrams, infographics, course banners.",
            "is_nonfield": False
        },
        {
            "username": "sneha_ui_75",
            "full_name": "Sneha Karki",
            "email": "sneha.karki@example.com",
            "target_score": 75.0,
            "base_text": "Sneha Karki - Graphic & UI/UX Designer\nEducation: Bachelor's in Computer Application with Graphic Design Certification\nExperience: 2.5 years of experience in digital illustrations and media banners\nSkills: Figma, Illustrator, Photoshop, Typography, Canva, After Effects\nProjects: Course promotional banners, learning infographics, visual diagrams.",
            "is_nonfield": False
        },
        {
            "username": "bibek_media_60",
            "full_name": "Bibek Thapa",
            "email": "bibek.thapa@example.com",
            "target_score": 60.0,
            "base_text": "Bibek Thapa - Multimedia Designer & Content Creator\nEducation: Bachelor's in Information Technology\nExperience: 2 years of experience in digital media production\nTools: Photoshop, Canva, Illustrator, Typography\nActivities: Educational banners, visual infographics, social media layouts.",
            "is_nonfield": False
        },
        # Intermediate / Lower matches below 60%
        {
            "username": "manish_arts_48",
            "full_name": "Manish Tamang",
            "email": "manish.tamang@example.com",
            "target_score": 48.0,
            "base_text": "Manish Tamang - Junior Graphic Artist\nEducation: Bachelor's in Humanities & Fine Arts\nExperience: 1.5 years experience in design studio\nSkills: Photoshop, Canva, Typography, digital drawing\nFocus: Poster design, catalog layout, banner creation.",
            "is_nonfield": False
        },
        {
            "username": "anjali_web_42",
            "full_name": "Anjali Basnet",
            "email": "anjali.basnet@example.com",
            "target_score": 42.0,
            "base_text": "Anjali Basnet - Web Content & Junior Designer\nEducation: Bachelor's in Science\nExperience: 2 years in content formatting\nSkills: Canva, Figma basics, HTML, CSS, image editing\nTasks: Web banners, blog infographics, social assets.",
            "is_nonfield": False
        },
        {
            "username": "suman_media_35",
            "full_name": "Suman Maharjan",
            "email": "suman.maharjan@example.com",
            "target_score": 35.0,
            "base_text": "Suman Maharjan - Desktop Publishing Assistant\nEducation: Intermediate 10+2 with DTP Diploma\nExperience: 3 years in print shop\nSkills: PageMaker, InDesign, Photoshop basics, Typography\nWork: Typesetting, book formatting, print layout.",
            "is_nonfield": False
        },
        {
            "username": "kritika_marketing_28",
            "full_name": "Kritika Gurung",
            "email": "kritika.gurung@example.com",
            "target_score": 28.0,
            "base_text": "Kritika Gurung - Digital Marketing Associate\nEducation: Bachelor's in Business Studies\nExperience: 2 years in social media marketing\nSkills: Canva, social campaigns, advertising, basic graphics\nDuties: Campaign scheduling, social posts, analytics.",
            "is_nonfield": False
        },
        {
            "username": "pradeep_frontend_22",
            "full_name": "Pradeep Bhandari",
            "email": "pradeep.bhandari@example.com",
            "target_score": 22.0,
            "base_text": "Pradeep Bhandari - Junior Web Developer\nEducation: Bachelor's in Computer Science\nExperience: 1 year in front-end development\nSkills: HTML5, CSS3, JavaScript, Figma layout inspection\nProjects: Responsive landing pages, website UI.",
            "is_nonfield": False
        },
        {
            "username": "sunita_assistant_16",
            "full_name": "Sunita Rai",
            "email": "sunita.rai@example.com",
            "target_score": 16.0,
            "base_text": "Sunita Rai - Office Administrative Assistant\nEducation: Bachelor's in Business Administration\nExperience: 3 years in office documentation\nSkills: MS Office, Word, Excel, PowerPoint presentation design\nTasks: Document formatting, reports, email coordination.",
            "is_nonfield": False
        },
        {
            "username": "deepak_data_10",
            "full_name": "Deepak Poudel",
            "email": "deepak.poudel@example.com",
            "target_score": 10.0,
            "base_text": "Deepak Poudel - Data Entry Operator\nEducation: 10+2 Commerce\nExperience: 2 years in computerized accounting\nSkills: Tally, MS Excel, data transcription, office filing\nDuties: Database entry, spreadsheet updating.",
            "is_nonfield": False
        },
        {
            "username": "nabin_accounts_6",
            "full_name": "Nabin Magar",
            "email": "nabin.magar@example.com",
            "target_score": 6.0,
            "base_text": "Nabin Magar - Junior Accountant\nEducation: Bachelor's in Business Studies (Accounting)\nExperience: 2 years in tax audit and ledger bookkeeping\nSkills: Financial accounting, VAT reconciliation, payroll\nDuties: Ledger maintenance, voucher verification.",
            "is_nonfield": False
        },
        # Exactly 2 nonfield persons matching ~2%
        {
            "username": "ram_mechanic_2",
            "full_name": "Ram Bahadur Thapa",
            "email": "ram.thapa.mechanic@example.com",
            "target_score": 2.0,
            "base_text": "Ram Bahadur Thapa - Heavy Machinery & Diesel Excavator Mechanic\nEducation: Technical Vocational Diploma in Heavy Mechanical Engineering\nExperience: 8 years industrial site maintenance\nSpecialization: Diesel engine overhaul, hydraulic cylinder repair, caterpillar bulldozer track servicing, pneumatic pumps, transmission gearboxes.",
            "is_nonfield": True
        },
        {
            "username": "gopal_fisherman_2",
            "full_name": "Gopal Singh",
            "email": "gopal.singh.deck@example.com",
            "target_score": 2.0,
            "base_text": "Gopal Singh - Commercial Deep Sea Fishing Trawler Deckhand\nEducation: Maritime Safety and Seamanship Vocational Certificate\nExperience: 6 years oceanic vessel operations\nSpecialization: Net deployment, marine winch handling, trawler engine room assistance, seafood cold storage preservation, marine navigation safety protocols.",
            "is_nonfield": True
        }
    ]

    media_dir = os.path.join("media", "resumes", "2026", "10")
    os.makedirs(media_dir, exist_ok=True)

    results_table = []

    for spec in candidates_spec:
        # Create or update user
        user, _ = User.objects.get_or_create(
            username=spec["username"],
            defaults={
                "first_name": spec["full_name"].split()[0],
                "last_name": " ".join(spec["full_name"].split()[1:]),
                "email": spec["email"]
            }
        )
        if not user.check_password("CandidatePass123!"):
            user.set_password("CandidatePass123!")
            user.save()

        # Calibrate resume text
        final_text, calculated_score = calibrate_text_to_score(
            spec["base_text"],
            job.description,
            job.required_skills,
            job.qualification,
            job.experience,
            spec["target_score"],
            is_nonfield=spec["is_nonfield"]
        )

        # Generate PDF file
        pdf_filename = f"{spec['username']}_CV.pdf"
        pdf_path = os.path.join(media_dir, pdf_filename)
        text_lines = [l.strip() for l in final_text.splitlines() if l.strip()]
        pdf_bytes = create_pdf_bytes(text_lines)

        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # Create Application
        rel_pdf_path = f"resumes/2026/10/{pdf_filename}"
        app = Application.objects.create(
            job=job,
            applicant=user,
            cv=rel_pdf_path,
            status=Application.STATUS_APPLIED
        )

        # Process CV text extraction & screening
        extraction = ResumeExtraction.process_application_cv(app)
        screening = getattr(app, 'resume_screening', None)

        results_table.append({
            "name": spec["full_name"],
            "username": spec["username"],
            "target": spec["target_score"],
            "actual_score": screening.match_percentage if screening else calculated_score,
            "ml_class": screening.ml_predicted_class if screening else "N/A",
            "ml_prob": f"{screening.ml_relevance_percentage}%" if (screening and screening.ml_relevance_probability is not None) else "N/A",
            "confidence": screening.ml_confidence_tier if screening else "N/A",
            "is_nonfield": spec["is_nonfield"]
        })

    print("\n" + "="*85)
    print(f"{'CANDIDATE NAME':<22} | {'TARGET':<7} | {'ACTUAL':<8} | {'ML CLASS':<12} | {'ML PROB':<8} | {'TIER':<8}")
    print("="*85)
    for r in results_table:
        print(f"{r['name']:<22} | {r['target']:>5.1f}% | {r['actual_score']:>6.2f}% | {r['ml_class']:<12} | {r['ml_prob']:<8} | {r['confidence']:<8}")
    print("="*85)
    print("Successfully populated all 15 applicants with valid PDF CVs!")

if __name__ == "__main__":
    main()
