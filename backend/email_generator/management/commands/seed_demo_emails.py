"""Optional demo data.  Usage:  python manage.py seed_demo_emails

Creates (or reuses) a demo user and adds a few sample emails to their history.
The application itself starts with an empty database; this is only for demos.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from email_generator.models import GeneratedEmail

SAMPLES = [
    {
        "purpose": "Internship Application", "recipient_type": "HR", "tone": "Professional", "language": "English",
        "important_points": "B.Tech CSE student. Completed Python and Django training. Resume attached.",
        "subject": "Application for Python Development Internship",
        "body": "Dear Hiring Manager,\n\nI am a B.Tech Computer Science student and I am writing to apply for the Python Development Internship at your company. I have completed training in Python and Django and would like to apply these skills in a real project.\n\nMy resume is attached for your review. I would be grateful for the opportunity to discuss my application.\n\nThank you for your time.\n\nSincerely,\n[Your Name]",
    },
    {
        "purpose": "Leave Request", "recipient_type": "Manager", "tone": "Polite", "language": "English",
        "important_points": "Need leave on 15 and 16 of this month for a family function.",
        "subject": "Leave Request for 15th and 16th",
        "body": "Dear Sir/Madam,\n\nI would like to request leave on the 15th and 16th of this month to attend a family function. I will complete my pending work before leaving and remain reachable if anything urgent comes up.\n\nThank you for considering my request.\n\nRegards,\n[Your Name]",
    },
    {
        "purpose": "Meeting Request", "recipient_type": "Client", "tone": "Formal", "language": "English",
        "important_points": "Discuss project progress. Prefer a 30 minute call this week.",
        "subject": "Request for a Project Progress Meeting",
        "body": "Dear Client,\n\nI hope you are doing well. I would like to schedule a 30-minute call this week to discuss the progress of our project and agree on the next steps.\n\nPlease let me know a time that suits you.\n\nBest regards,\n[Your Name]",
    },
    {
        "purpose": "Thank You", "recipient_type": "Professor", "tone": "Friendly", "language": "Hinglish",
        "important_points": "Thank the professor for guidance on the final year project.",
        "subject": "Project guidance ke liye dhanyavaad",
        "body": "Dear Professor,\n\nAapne mere final year project mein jo guidance di, uske liye main dil se dhanyavaad kehna chahta hoon. Aapki suggestions se mujhe bahut kuch seekhne ko mila.\n\nThank you once again.\n\nRegards,\n[Your Name]",
    },
]


class Command(BaseCommand):
    help = "Adds a demo user and a few sample emails (does not call the AI API)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="Demo@12345")

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username=options["username"])
        if created:
            user.set_password(options["password"])
            user.save()
            self.stdout.write(f"Created user '{user.username}' with password '{options['password']}'.")

        added = 0
        for sample in SAMPLES:
            _, was_created = GeneratedEmail.objects.get_or_create(user=user, subject=sample["subject"], defaults=sample)
            added += was_created
        self.stdout.write(self.style.SUCCESS(f"Done. {added} new demo email(s) added for '{user.username}'."))
