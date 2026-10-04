"""
Script to set the 15 Graphic Designer applicants with exact match scores:
- 5 CVs matching 82%, 80%, 80%, 75%, 60%
- Other CVs below them (48%, 42%, 35%, 28%, 20%, 15%, 10%, 6%)
- 2 CVs matching 2% due to being completely non-field persons
"""

import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurukul.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job
from applications.models import Application
from resume_ai.models import ResumeExtraction, ResumeScreening, ResumeAnalysis
from resume_ai.service import clean_text

def create_pdf_bytes(lines):
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
    offsets.append(pos); pos += len(obj1)
    offsets.append(pos); pos += len(obj2)
    offsets.append(pos); pos += len(obj3)
    offsets.append(pos); pos += len(obj4)
    offsets.append(pos); pos += len(obj5)

    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode('latin1')

    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF\n".encode('latin1')
    return header + obj1 + obj2 + obj3 + obj4 + obj5 + xref + trailer

def apply():
    print("Setting up Job 15: Graphic Designer & Visual Media Specialist...")
    job, _ = Job.objects.get_or_create(
        id=15,
        defaults={
            "title": "Graphic Designer & Visual Media Specialist",
            "department": "Curriculum & Content",
            "description": "Looking for a creative Graphic Designer to create Loksewa preparation diagrams, visual learning infographics, course banners, and academic publishing layouts.",
            "required_skills": "Photoshop, Illustrator, Figma, Canva, After Effects, Typography",
            "qualification": "Bachelor's in Graphic Design, Fine Arts, or Multimedia",
            "experience": "2+ Years",
            "job_type": "Full Time",
            "location": "Kathmandu (Putalisadak) / Hybrid",
            "deadline": timezone.now().date() + timedelta(days=30)
        }
    )
    job.title = "Graphic Designer & Visual Media Specialist"
    job.department = "Curriculum & Content"
    job.description = "Looking for a creative Graphic Designer to create Loksewa preparation diagrams, visual learning infographics, course banners, and academic publishing layouts."
    job.required_skills = "Photoshop, Illustrator, Figma, Canva, After Effects, Typography"
    job.qualification = "Bachelor's in Graphic Design, Fine Arts, or Multimedia"
    job.experience = "2+ Years"
    job.deadline = timezone.now().date() + timedelta(days=30)
    job.save()

    # Clear existing applications to ensure exactly 15 applicants
    Application.objects.filter(job=job).delete()

    media_dir = os.path.join("media", "resumes", "2026", "10")
    os.makedirs(media_dir, exist_ok=True)

    applicants_data = [
        # Top 5 matching: 82%, 80%, 80%, 75%, 60%
        {
            "username": "aarav_designer_82",
            "name": "Aarav Sharma",
            "email": "aarav.sharma@example.com",
            "match_pct": 82.00,
            "ml_class": "Relevant",
            "ml_prob": 0.8845,
            "ml_tier": "High",
            "qual_match": "Matched",
            "exp_match": "Matched",
            "matched_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "After Effects", "Typography"],
            "missing_skills": [],
            "resume_lines": [
                "Aarav Sharma - Lead Graphic Designer & Visual Media Specialist",
                "Email: aarav.sharma@example.com | Phone: +977-9841000001 | Kathmandu, Nepal",
                "Summary: Senior Creative Graphic Designer with 4 years of experience in visual design.",
                "Education: Bachelor in Graphic Design (Tribhuvan University)",
                "Skills: Photoshop, Illustrator, Figma, Canva, After Effects, Typography",
                "Experience: Created Loksewa preparation diagrams, visual learning infographics, course banners, and academic publishing layouts."
            ]
        },
        {
            "username": "pooja_visual_80",
            "name": "Pooja Shrestha",
            "email": "pooja.shrestha@example.com",
            "match_pct": 80.00,
            "ml_class": "Relevant",
            "ml_prob": 0.8420,
            "ml_tier": "High",
            "qual_match": "Matched",
            "exp_match": "Matched",
            "matched_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "Typography"],
            "missing_skills": ["After Effects"],
            "resume_lines": [
                "Pooja Shrestha - Senior Visual Designer",
                "Email: pooja.shrestha@example.com | Phone: +977-9841000002 | Lalitpur, Nepal",
                "Summary: Creative Graphic Designer with 3.5 years of experience in infographics and academic layouts.",
                "Education: Bachelor in Graphic Design & Multimedia Arts",
                "Skills: Photoshop, Illustrator, Figma, Canva, Typography",
                "Experience: Designed Loksewa study diagrams, promotional course banners, and interactive educational infographics."
            ]
        },
        {
            "username": "rohan_graphics_80",
            "name": "Rohan Adhikari",
            "email": "rohan.adhikari@example.com",
            "match_pct": 80.00,
            "ml_class": "Relevant",
            "ml_prob": 0.8350,
            "ml_tier": "High",
            "qual_match": "Matched",
            "exp_match": "Matched",
            "matched_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "After Effects"],
            "missing_skills": ["Typography"],
            "resume_lines": [
                "Rohan Adhikari - Graphic & Layout Designer",
                "Email: rohan.adhikari@example.com | Phone: +977-9841000003 | Bhaktapur, Nepal",
                "Summary: Fine Arts graduate with 4 years experience in publishing layouts and digital media.",
                "Education: Bachelor in Fine Arts (Graphic Design Major)",
                "Skills: Illustrator, Photoshop, Figma, Canva, After Effects",
                "Experience: Produced academic publishing layouts, Loksewa exam diagrams, and multimedia banners."
            ]
        },
        {
            "username": "sneha_ui_75",
            "name": "Sneha Karki",
            "email": "sneha.karki@example.com",
            "match_pct": 75.00,
            "ml_class": "Relevant",
            "ml_prob": 0.7830,
            "ml_tier": "High",
            "qual_match": "Matched",
            "exp_match": "Matched",
            "matched_skills": ["Photoshop", "Illustrator", "Figma", "Canva"],
            "missing_skills": ["After Effects", "Typography"],
            "resume_lines": [
                "Sneha Karki - Graphic & Digital Media Specialist",
                "Email: sneha.karki@example.com | Phone: +977-9841000004 | Kathmandu, Nepal",
                "Summary: Graphic Designer with 3 years experience creating digital media and infographics.",
                "Education: Bachelor in Multimedia and Computer Applications",
                "Skills: Photoshop, Illustrator, Figma, Canva",
                "Experience: Created visual learning infographics, course banners, and educational diagrams."
            ]
        },
        {
            "username": "bibek_media_60",
            "name": "Bibek Thapa",
            "email": "bibek.thapa@example.com",
            "match_pct": 60.00,
            "ml_class": "Relevant",
            "ml_prob": 0.6840,
            "ml_tier": "Moderate",
            "qual_match": "Matched",
            "exp_match": "Matched",
            "matched_skills": ["Photoshop", "Canva", "Typography"],
            "missing_skills": ["Illustrator", "Figma", "After Effects"],
            "resume_lines": [
                "Bibek Thapa - Junior Graphic Designer",
                "Email: bibek.thapa@example.com | Phone: +977-9841000005 | Pokhara, Nepal",
                "Summary: Graphic Designer with 2 years of experience in advertising and digital content.",
                "Education: Bachelor in Arts (Graphic Communication)",
                "Skills: Photoshop, Canva, Typography",
                "Experience: Designed marketing banners, social media infographics, and poster layouts."
            ]
        },
        # Other CVs below 60%
        {
            "username": "manish_arts_48",
            "name": "Manish Tamang",
            "email": "manish.tamang@example.com",
            "match_pct": 48.00,
            "ml_class": "Relevant",
            "ml_prob": 0.6120,
            "ml_tier": "Moderate",
            "qual_match": "Needs Verification",
            "exp_match": "Matched",
            "matched_skills": ["Photoshop", "Canva"],
            "missing_skills": ["Illustrator", "Figma", "After Effects", "Typography"],
            "resume_lines": [
                "Manish Tamang - Digital Art & Visual Content Assistant",
                "Email: manish.tamang@example.com | Kathmandu, Nepal",
                "Education: Bachelor in Humanities with Graphic Art certification",
                "Experience: 2 years in advertising and print media",
                "Skills: Photoshop, Canva, basic digital sketching",
                "Experience: Designed promotional banners and visual posters."
            ]
        },
        {
            "username": "anjali_web_42",
            "name": "Anjali Basnet",
            "email": "anjali.basnet@example.com",
            "match_pct": 42.00,
            "ml_class": "Relevant",
            "ml_prob": 0.5540,
            "ml_tier": "Moderate",
            "qual_match": "Needs Verification",
            "exp_match": "Matched",
            "matched_skills": ["Canva", "Figma"],
            "missing_skills": ["Photoshop", "Illustrator", "After Effects", "Typography"],
            "resume_lines": [
                "Anjali Basnet - Web Graphics & Content Coordinator",
                "Email: anjali.basnet@example.com | Lalitpur, Nepal",
                "Education: Bachelor of Science in Information Technology",
                "Experience: 2 years in website content management",
                "Skills: Canva, Figma basics, HTML, CSS",
                "Experience: Formatted website banners and blog graphics."
            ]
        },
        {
            "username": "suman_print_35",
            "name": "Suman Maharjan",
            "email": "suman.maharjan@example.com",
            "match_pct": 35.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.4680,
            "ml_tier": "Low",
            "qual_match": "Needs Verification",
            "exp_match": "Matched",
            "matched_skills": ["Photoshop", "Typography"],
            "missing_skills": ["Illustrator", "Figma", "Canva", "After Effects"],
            "resume_lines": [
                "Suman Maharjan - Desktop Publishing (DTP) Operator",
                "Email: suman.maharjan@example.com | Kathmandu, Nepal",
                "Education: 10+2 Intermediate with Diploma in Computer Applications",
                "Experience: 3 years in commercial press and offset printing",
                "Skills: PageMaker, InDesign, Photoshop, Typography",
                "Experience: Book typesetting and exam paper layouts."
            ]
        },
        {
            "username": "kritika_marketing_28",
            "name": "Kritika Gurung",
            "email": "kritika.gurung@example.com",
            "match_pct": 28.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.3820,
            "ml_tier": "Low",
            "qual_match": "Not Matched",
            "exp_match": "Matched",
            "matched_skills": ["Canva"],
            "missing_skills": ["Photoshop", "Illustrator", "Figma", "After Effects", "Typography"],
            "resume_lines": [
                "Kritika Gurung - Digital Marketing & Social Media Executive",
                "Email: kritika.gurung@example.com | Pokhara, Nepal",
                "Education: Bachelor in Business Studies (Marketing)",
                "Experience: 2.5 years in digital campaign management",
                "Skills: Canva, Social Media Advertising, Content Writing",
                "Experience: Designed basic social graphics and managed campaigns."
            ]
        },
        {
            "username": "pradeep_frontend_20",
            "name": "Pradeep Bhandari",
            "email": "pradeep.bhandari@example.com",
            "match_pct": 20.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.3150,
            "ml_tier": "Low",
            "qual_match": "Needs Verification",
            "exp_match": "Needs Verification",
            "matched_skills": ["Figma"],
            "missing_skills": ["Photoshop", "Illustrator", "Canva", "After Effects", "Typography"],
            "resume_lines": [
                "Pradeep Bhandari - Junior Front-End Web Developer",
                "Email: pradeep.bhandari@example.com | Chitwan, Nepal",
                "Education: Bachelor in Computer Applications (BCA)",
                "Experience: 1 year in front-end web development",
                "Skills: HTML5, CSS3, JavaScript, Bootstrap, basic Figma inspection",
                "Experience: Developed responsive landing pages."
            ]
        },
        {
            "username": "sunita_admin_15",
            "name": "Sunita Rai",
            "email": "sunita.rai@example.com",
            "match_pct": 15.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.2460,
            "ml_tier": "Low",
            "qual_match": "Not Matched",
            "exp_match": "Matched",
            "matched_skills": [],
            "missing_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "After Effects", "Typography"],
            "resume_lines": [
                "Sunita Rai - Executive Administrative Assistant",
                "Email: sunita.rai@example.com | Dharan, Nepal",
                "Education: Bachelor in Business Administration",
                "Experience: 3 years in academic administration",
                "Skills: MS Word, MS Excel, PowerPoint presentation formatting",
                "Experience: Managed student records and correspondence."
            ]
        },
        {
            "username": "deepak_data_10",
            "name": "Deepak Poudel",
            "email": "deepak.poudel@example.com",
            "match_pct": 10.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.1740,
            "ml_tier": "Low",
            "qual_match": "Not Matched",
            "exp_match": "Matched",
            "matched_skills": [],
            "missing_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "After Effects", "Typography"],
            "resume_lines": [
                "Deepak Poudel - Computer Data Entry & Documentation Operator",
                "Email: deepak.poudel@example.com | Butwal, Nepal",
                "Education: 10+2 Higher Secondary in Commerce",
                "Experience: 2 years in data entry and office filing",
                "Skills: Typing 55 WPM, MS Excel, spreadsheet reporting",
                "Experience: Maintained records and updated spreadsheets."
            ]
        },
        {
            "username": "nabin_accounts_6",
            "name": "Nabin Magar",
            "email": "nabin.magar@example.com",
            "match_pct": 6.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.1120,
            "ml_tier": "Low",
            "qual_match": "Not Matched",
            "exp_match": "Matched",
            "matched_skills": [],
            "missing_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "After Effects", "Typography"],
            "resume_lines": [
                "Nabin Magar - Assistant Accountant & Bookkeeper",
                "Email: nabin.magar@example.com | Hetauda, Nepal",
                "Education: Bachelor in Business Studies (Accounting)",
                "Experience: 2 years in ledger accounting and taxation",
                "Skills: Tally ERP, VAT auditing, balance sheet preparation",
                "Experience: Maintained ledgers and processed payroll payments."
            ]
        },
        # Exactly 2 nonfield persons matching 2%
        {
            "username": "ram_mechanic_2",
            "name": "Ram Bahadur Thapa",
            "email": "ram.thapa.mechanic@example.com",
            "match_pct": 2.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.0450,
            "ml_tier": "Low",
            "qual_match": "Not Matched",
            "exp_match": "Matched",
            "matched_skills": [],
            "missing_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "After Effects", "Typography"],
            "resume_lines": [
                "Ram Bahadur Thapa - Heavy Machinery & Diesel Excavator Mechanic",
                "Email: ram.thapa.mechanic@example.com | Birgunj, Nepal",
                "Summary: 8 years industrial experience repairing heavy caterpillar excavators, diesel bulldozers, hydraulic valves, pneumatic compressors, transmission gearboxes, quarry haulage trucks.",
                "Education: Technical Vocational Diploma in Heavy Mechanical Engineering",
                "Skills: Diesel engine overhaul, hydraulic cylinder repair, machinery chassis servicing, mechanical welding, workshop fleet safety course training."
            ]
        },
        {
            "username": "gopal_fisherman_2",
            "name": "Gopal Singh",
            "email": "gopal.singh.deck@example.com",
            "match_pct": 2.00,
            "ml_class": "Not Relevant",
            "ml_prob": 0.0380,
            "ml_tier": "Low",
            "qual_match": "Not Matched",
            "exp_match": "Matched",
            "matched_skills": [],
            "missing_skills": ["Photoshop", "Illustrator", "Figma", "Canva", "After Effects", "Typography"],
            "resume_lines": [
                "Gopal Singh - Commercial Deep Sea Fishing Trawler Deckhand & Marine Crew",
                "Email: gopal.singh.deck@example.com | Jhapa, Nepal",
                "Summary: 7 years maritime sea experience operating offshore fishing trawler winches, ocean trawl netting, marine navigation sonar, cold storage freezing, vessel hull maintenance.",
                "Education: Maritime Safety and Seamanship Vocational Certificate",
                "Skills: Trawler net winch handling, marine navigation safety, vessel hull maintenance, seamanship course training."
            ]
        }
    ]

    for item in applicants_data:
        # User
        user, _ = User.objects.get_or_create(
            username=item["username"],
            defaults={
                "first_name": item["name"].split()[0],
                "last_name": " ".join(item["name"].split()[1:]),
                "email": item["email"]
            }
        )
        if not user.check_password("CandidatePass123!"):
            user.set_password("CandidatePass123!")
            user.save()

        # PDF file
        pdf_filename = f"{item['username']}_CV.pdf"
        pdf_path = os.path.join(media_dir, pdf_filename)
        pdf_bytes = create_pdf_bytes(item["resume_lines"])
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # Application
        rel_pdf = f"resumes/2026/10/{pdf_filename}"
        app = Application.objects.create(
            job=job,
            applicant=user,
            cv=rel_pdf,
            status=Application.STATUS_APPLIED
        )

        # ResumeExtraction
        raw_text = "\n".join(item["resume_lines"])
        ResumeExtraction.objects.update_or_create(
            application=app,
            defaults={
                "extracted_text": raw_text,
                "page_count": 1,
                "status": ResumeExtraction.STATUS_SUCCESS,
                "error_message": ""
            }
        )

        # ResumeScreening
        sim_score = round(item["match_pct"] / 100.0, 4)
        ResumeScreening.objects.update_or_create(
            application=app,
            defaults={
                "similarity_score": sim_score,
                "match_percentage": item["match_pct"],
                "status": ResumeScreening.STATUS_SUCCESS,
                "error_message": "",
                "matched_keywords_json": json.dumps([{"term": s.lower(), "contribution": 0.15} for s in item["matched_skills"]]),
                "job_vector_json": json.dumps({"graphic": 0.35, "designer": 0.35, "photoshop": 0.25}),
                "resume_vector_json": json.dumps({"graphic": 0.35, "designer": 0.35, "photoshop": 0.25}),
                "matched_skills_json": json.dumps(item["matched_skills"]),
                "missing_skills_json": json.dumps(item["missing_skills"]),
                "qualification_match": item["qual_match"],
                "qualification_detail": f"Evaluation for {item['name']}.",
                "experience_match": item["exp_match"],
                "experience_detail": "Experience verified from CV.",
                "ml_predicted_class": item["ml_class"],
                "ml_relevance_probability": item["ml_prob"],
                "ml_confidence_tier": item["ml_tier"],
                "ml_model_version": "1.0.0",
                "ml_prediction_status": "SUCCESS"
            }
        )

        # ResumeAnalysis
        ResumeAnalysis.objects.update_or_create(
            application=app,
            defaults={
                "match_percentage": item["match_pct"],
                "matched_skills": json.dumps(item["matched_skills"]),
                "missing_skills": json.dumps(item["missing_skills"]),
                "qualification_match": item["qual_match"],
                "experience_match": item["exp_match"],
                "explanation": f"Match evaluation for Graphic Designer position: {item['match_pct']}% match score with {item['ml_class']} ML prediction."
            }
        )

    print("\n" + "="*95)
    print(f"{'#':<3} | {'CANDIDATE NAME':<22} | {'MATCH %':<9} | {'ML CLASS':<12} | {'ML PROB':<9} | {'TIER':<8} | {'STATUS':<10}")
    print("="*95)
    for i, app in enumerate(job.applications.all().order_by('-resume_screening__match_percentage'), 1):
        sc = app.resume_screening
        print(f"{i:<3} | {app.applicant.get_full_name():<22} | {sc.match_percentage:>6.2f}%   | {sc.ml_predicted_class:<12} | {sc.ml_relevance_percentage}%     | {sc.ml_confidence_tier:<8} | {sc.status:<10}")
    print("="*95)
    print(f"Total Applicants for '{job.title}': {job.applications.count()}")

if __name__ == "__main__":
    apply()
