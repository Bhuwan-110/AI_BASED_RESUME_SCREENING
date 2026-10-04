"""
Populate Graphic Designer Job and 15 Applicants with genuine PDF CVs.
Target scores:
1. 82% (81.5% - 82.5%)
2. 80% (79.5% - 80.6%)
3. 80% (79.5% - 80.6%)
4. 75% (74.5% - 76.0%)
5. 60% (59.5% - 61.0%)
6-13. Below 60% (descending: ~48%, ~42%, ~35%, ~28%, ~20%, ~15%, ~10%, ~6%)
14-15. ~2% (non-field persons: 2.0%)
"""

import os
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

def run():
    print("Initializing Graphic Designer Vacancy...")
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

    print(f"Target Vacancy ID {job.id}: {job.title}")

    # Remove existing applications to provide a clean set of 15 applicants
    Application.objects.filter(job=job).delete()

    desc = job.description
    skills = job.required_skills
    qual = job.qualification
    exp = job.experience

    # Pre-calculated text templates to hit the requested scores
    # 22 job terms:
    # ['looking', 'creative', 'graphic', 'designer', 'create', 'loksewa', 'preparation', 'diagrams', 'visual', 'learning', 'infographics', 'course', 'banners', 'academic', 'publishing', 'layouts', 'photoshop', 'illustrator', 'figma', 'canva', 'effects', 'typography']
    
    jt = ['creative', 'graphic', 'designer', 'create', 'loksewa', 'preparation', 'diagrams', 'visual', 'learning', 'infographics', 'course', 'banners', 'academic', 'publishing', 'layouts', 'photoshop', 'illustrator', 'figma', 'canva', 'effects', 'typography']
    fillers = ['bachelor', 'experience', 'portfolio', 'kathmandu', 'nepal', 'university', 'responsible', 'client', 'communication', 'teamwork', 'leadership', 'delivery', 'presentation', 'documentation', 'quality', 'strategy', 'planning', 'workflow', 'operations', 'evaluation', 'student', 'assessment', 'curriculum', 'education', 'management', 'office', 'headquarters', 'review', 'schedule', 'reporting', 'interface', 'branding']

    # We will build 15 structured candidate profiles:
    specs = [
        # 1. Target 82%
        {
            "username": "aarav_designer_82",
            "full_name": "Aarav Sharma",
            "email": "aarav.sharma@example.com",
            "target": "82%",
            "resume_lines": [
                "Aarav Sharma - Lead Graphic Designer & Visual Media Specialist",
                "Email: aarav.sharma@example.com | Phone: +977-9841000001 | Kathmandu, Nepal",
                "Professional Summary:",
                "Creative Graphic Designer with 4 years of professional experience in graphic design and academic publishing.",
                "Proven track record creating Loksewa preparation diagrams, visual learning infographics, and course banners.",
                "Education: Bachelor in Graphic Design, Tribhuvan University (2020)",
                "Technical Skills:",
                "Photoshop, Illustrator, Figma, Canva, After Effects, Typography",
                "Key Responsibilities:",
                "- Looking for innovative ways to create high-impact course banners and academic publishing layouts.",
                "- Designed over 250+ visual learning infographics and Loksewa exam preparation diagrams.",
                "- Portfolio includes full branding, vector illustrations, and responsive media graphics."
            ]
        },
        # 2. Target 80%
        {
            "username": "pooja_visual_80",
            "full_name": "Pooja Shrestha",
            "email": "pooja.shrestha@example.com",
            "target": "80%",
            "resume_lines": [
                "Pooja Shrestha - Senior Visual Designer",
                "Email: pooja.shrestha@example.com | Phone: +977-9841000002 | Lalitpur, Nepal",
                "Professional Summary:",
                "Creative Graphic Designer with 3.5 years of experience in visual design, course banners, and layouts.",
                "Education: Bachelor in Graphic Design & Multimedia Arts (2021)",
                "Technical Competencies:",
                "Photoshop, Illustrator, Figma, Canva, After Effects, Typography",
                "Key Achievements:",
                "- Created comprehensive visual learning infographics and educational diagrams for Loksewa preparation.",
                "- Developed publishing layouts, digital banners, and interactive course materials.",
                "- Coordinated with academic content teams to deliver vector illustrations and infographics."
            ]
        },
        # 3. Target 80%
        {
            "username": "rohan_graphics_80",
            "full_name": "Rohan Adhikari",
            "email": "rohan.adhikari@example.com",
            "target": "80%",
            "resume_lines": [
                "Rohan Adhikari - Graphic & Layout Designer",
                "Email: rohan.adhikari@example.com | Phone: +977-9841000003 | Bhaktapur, Nepal",
                "Professional Summary:",
                "Creative Designer with Bachelor in Fine Arts and 4 years of hands-on experience in publishing layouts.",
                "Education: Bachelor in Fine Arts (Graphic Design Major)",
                "Core Skills:",
                "Illustrator, Photoshop, Figma, Canva, After Effects, Typography",
                "Work History:",
                "- Designed academic publishing layouts, Loksewa preparation study diagrams, and promotional course banners.",
                "- Produced digital learning infographics and vector assets for web and print.",
                "- Collaborated with educational authors to conceptualize and create visual teaching diagrams."
            ]
        },
        # 4. Target 75%
        {
            "username": "sneha_ui_75",
            "full_name": "Sneha Karki",
            "email": "sneha.karki@example.com",
            "target": "75%",
            "resume_lines": [
                "Sneha Karki - Graphic & Digital Media Specialist",
                "Email: sneha.karki@example.com | Phone: +977-9841000004 | Kathmandu, Nepal",
                "Professional Summary:",
                "Graphic Designer with 3 years experience creating digital media, infographics, and course banners.",
                "Education: Bachelor in Multimedia and Computer Applications",
                "Skills: Photoshop, Illustrator, Figma, Canva, Typography",
                "Experience:",
                "- Created visual learning diagrams and social course banners for educational programs.",
                "- Formatted academic study material layouts and vector illustrations.",
                "- Assisted academic mentors in preparing Loksewa infographics and diagrams."
            ]
        },
        # 5. Target 60%
        {
            "username": "bibek_media_60",
            "full_name": "Bibek Thapa",
            "email": "bibek.thapa@example.com",
            "target": "60%",
            "resume_lines": [
                "Bibek Thapa - Junior Graphic Designer",
                "Email: bibek.thapa@example.com | Phone: +977-9841000005 | Pokhara, Nepal",
                "Professional Summary:",
                "Enthusiastic Graphic Designer with 2 years of agency experience in digital illustrations and media design.",
                "Education: Bachelor in Arts (Communication & Design)",
                "Skills: Photoshop, Canva, Illustrator, Typography basics",
                "Work Experience:",
                "- Designed marketing banners, social media infographics, and poster layouts.",
                "- Prepared creative diagrams and presentation slides for student workshops.",
                "- Handled photo retouching and graphic design deliverables for multiple client projects."
            ]
        },
        # 6. Target ~48%
        {
            "username": "manish_arts_48",
            "full_name": "Manish Tamang",
            "email": "manish.tamang@example.com",
            "target": "48%",
            "resume_lines": [
                "Manish Tamang - Digital Art & Visual Content Assistant",
                "Email: manish.tamang@example.com | Phone: +977-9841000006 | Kathmandu",
                "Education: Bachelor in Humanities with Graphic Art certification",
                "Experience: 2 years in advertising and print media",
                "Skills: Photoshop, Canva, basic Illustrator, freehand sketching",
                "Duties: Prepared promotional banners, brochures, and visual event posters. Assisted with layout formatting."
            ]
        },
        # 7. Target ~42%
        {
            "username": "anjali_web_42",
            "full_name": "Anjali Basnet",
            "email": "anjali.basnet@example.com",
            "target": "42%",
            "resume_lines": [
                "Anjali Basnet - Web Graphics & Content Coordinator",
                "Email: anjali.basnet@example.com | Phone: +977-9841000007 | Patan",
                "Education: Bachelor of Science in Information Technology",
                "Experience: 2 years in website content management",
                "Skills: Canva, Figma basics, HTML, CSS, image cropping",
                "Responsibilities: Uploaded web banners, formatted blog graphics, coordinated social media assets."
            ]
        },
        # 8. Target ~35%
        {
            "username": "suman_print_35",
            "full_name": "Suman Maharjan",
            "email": "suman.maharjan@example.com",
            "target": "35%",
            "resume_lines": [
                "Suman Maharjan - Desktop Publishing (DTP) Operator",
                "Email: suman.maharjan@example.com | Phone: +977-9841000008 | Kathmandu",
                "Education: 10+2 Intermediate with Diploma in Computer Applications",
                "Experience: 3 years in commercial press and offset printing",
                "Skills: PageMaker, InDesign, Photoshop, Typography",
                "Tasks: Book typesetting, exam paper layouts, proofreading, offset printing coordination."
            ]
        },
        # 9. Target ~28%
        {
            "username": "kritika_marketing_28",
            "full_name": "Kritika Gurung",
            "email": "kritika.gurung@example.com",
            "target": "28%",
            "resume_lines": [
                "Kritika Gurung - Digital Marketing & Social Media Executive",
                "Email: kritika.gurung@example.com | Phone: +977-9841000009 | Pokhara",
                "Education: Bachelor in Business Studies (Marketing)",
                "Experience: 2.5 years in digital campaign management",
                "Skills: Canva, Social Media Advertising, Content Writing, SEO basics",
                "Experience: Coordinated promotional posts, designed basic social graphics, tracked ad performance."
            ]
        },
        # 10. Target ~22%
        {
            "username": "pradeep_frontend_22",
            "full_name": "Pradeep Bhandari",
            "email": "pradeep.bhandari@example.com",
            "target": "22%",
            "resume_lines": [
                "Pradeep Bhandari - Junior Front-End Web Developer",
                "Email: pradeep.bhandari@example.com | Phone: +977-9841000010 | Chitwan",
                "Education: Bachelor in Computer Applications (BCA)",
                "Experience: 1 year in front-end web development",
                "Skills: HTML5, CSS3, JavaScript, Bootstrap, basic Figma inspection",
                "Projects: Developed responsive website landing pages and inspected UI design prototypes."
            ]
        },
        # 11. Target ~16%
        {
            "username": "sunita_admin_16",
            "full_name": "Sunita Rai",
            "email": "sunita.rai@example.com",
            "target": "16%",
            "resume_lines": [
                "Sunita Rai - Executive Administrative Assistant",
                "Email: sunita.rai@example.com | Phone: +977-9841000011 | Dharan",
                "Education: Bachelor in Business Administration",
                "Experience: 3 years in academic administration and student support",
                "Skills: MS Word, MS Excel, PowerPoint presentation formatting, office management",
                "Responsibilities: Drafted official correspondence, created presentation slides, managed records."
            ]
        },
        # 12. Target ~10%
        {
            "username": "deepak_data_10",
            "full_name": "Deepak Poudel",
            "email": "deepak.poudel@example.com",
            "target": "10%",
            "resume_lines": [
                "Deepak Poudel - Computer Data Entry & Documentation Operator",
                "Email: deepak.poudel@example.com | Phone: +977-9841000012 | Butwal",
                "Education: 10+2 Higher Secondary in Commerce",
                "Experience: 2 years in data entry and database records",
                "Skills: Typing 55 WPM, MS Excel, spreadsheet reporting, filing",
                "Work: Maintained student enrollment database, verified application forms, produced spreadsheets."
            ]
        },
        # 13. Target ~6%
        {
            "username": "nabin_accounts_6",
            "full_name": "Nabin Magar",
            "email": "nabin.magar@example.com",
            "target": "6%",
            "resume_lines": [
                "Nabin Magar - Assistant Accountant & Bookkeeper",
                "Email: nabin.magar@example.com | Phone: +977-9841000013 | Hetauda",
                "Education: Bachelor in Business Studies (Accounting)",
                "Experience: 2 years in ledger accounting and taxation",
                "Skills: Tally ERP, VAT auditing, balance sheet preparation, invoice reconciliation",
                "Duties: Verified daily accounting vouchers, reconciled bank statements, processed payroll payments."
            ]
        },
        # 14. Target ~2% (Non-field person 1: Heavy Equipment Excavator Mechanic)
        {
            "username": "ram_mechanic_2",
            "full_name": "Ram Bahadur Thapa",
            "email": "ram.thapa.mechanic@example.com",
            "target": "2%",
            "resume_lines": [
                "Ram Bahadur Thapa - Senior Heavy Equipment Diesel Mechanic & Excavator Technician",
                "Email: ram.thapa.mechanic@example.com | Phone: +977-9841000014 | Birgunj, Nepal",
                "Summary: 8 years industrial experience repairing heavy caterpillar excavators, diesel bulldozers, hydraulic valves, pneumatic compressors, transmission gearboxes, quarry haulage trucks, engine cylinder overhaul, mechanical welding, workshop fleet safety. Completed specialized heavy equipment safety certification course training."
            ]
        },
        # 15. Target ~2% (Non-field person 2: Offshore Commercial Deep Sea Fishing Trawler Deckhand)
        {
            "username": "gopal_fisherman_2",
            "full_name": "Gopal Singh",
            "email": "gopal.singh.deck@example.com",
            "target": "2%",
            "resume_lines": [
                "Gopal Singh - Commercial Deep Sea Fishing Trawler Deckhand & Maritime Crew",
                "Email: gopal.singh.deck@example.com | Phone: +977-9841000015 | Jhapa, Nepal",
                "Summary: 7 years maritime sea experience operating offshore fishing trawler winches, ocean trawl netting, marine navigation sonar, cold storage freezing, vessel hull maintenance, maritime emergency drill safety protocols, diesel engine room assistance. Completed mandatory oceanic seamanship vessel safety certification course training."
            ]
        }
    ]

    media_dir = os.path.join("media", "resumes", "2026", "10")
    os.makedirs(media_dir, exist_ok=True)

    results = []

    for spec in specs:
        # Create user
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

        # Build PDF
        pdf_filename = f"{spec['username']}_CV.pdf"
        pdf_path = os.path.join(media_dir, pdf_filename)
        pdf_bytes = create_pdf_bytes(spec["resume_lines"])
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # Create application
        rel_pdf = f"resumes/2026/10/{pdf_filename}"
        app = Application.objects.create(
            job=job,
            applicant=user,
            cv=rel_pdf,
            status=Application.STATUS_APPLIED
        )

        # Trigger extraction & screening
        ResumeExtraction.process_application_cv(app)
        screening = getattr(app, 'resume_screening', None)

        score = screening.match_percentage if screening else 0.0
        ml_class = screening.ml_predicted_class if screening else "N/A"
        ml_prob = f"{screening.ml_relevance_percentage}%" if (screening and screening.ml_relevance_probability is not None) else "N/A"
        conf = screening.ml_confidence_tier if screening else "N/A"

        results.append({
            "name": spec["full_name"],
            "target": spec["target"],
            "score": score,
            "ml_class": ml_class,
            "ml_prob": ml_prob,
            "conf": conf
        })

    print("\n" + "="*88)
    print(f"{'#':<3} | {'CANDIDATE NAME':<22} | {'TARGET':<7} | {'ACTUAL COSINE':<13} | {'ML CLASS':<12} | {'ML PROB':<8}")
    print("="*88)
    for i, r in enumerate(results, 1):
        print(f"{i:<3} | {r['name']:<22} | {r['target']:<7} | {r['score']:>6.2f}%       | {r['ml_class']:<12} | {r['ml_prob']:<8}")
    print("="*88)
    print(f"Total Applications on Job {job.id}: {job.applications.count()}")

if __name__ == "__main__":
    run()
