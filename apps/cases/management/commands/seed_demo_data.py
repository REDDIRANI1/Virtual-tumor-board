from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.cases.models import Case, Comment, Invitation
from apps.cases.services import (
    structure_case,
    transition_case,
    invite_doctor,
    create_comment,
    publish_answer
)
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seeds the database with pure fake data for users and a case lifecycle'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding demo data...')

        # 1. Create Users
        warrior = User.objects.create_user(
            username='warrior_jane',
            email='jane@example.fake',
            password='Password123!',
            role='warrior',
            first_name='Jane',
            last_name='Doe'
        )

        mod = User.objects.create_user(
            username='mod_smith',
            email='smith@example.fake',
            password='Password123!',
            role='moderator',
            first_name='Admin',
            last_name='Smith'
        )

        doc1 = User.objects.create_user(
            username='doc_jones',
            email='jones@example.fake',
            password='Password123!',
            role='doctor',
            first_name='Dr. Jones',
            last_name='Oncologist'
        )

        doc2 = User.objects.create_user(
            username='doc_lee',
            email='lee@example.fake',
            password='Password123!',
            role='doctor',
            first_name='Dr. Lee',
            last_name='Surgeon'
        )

        # 2. Warrior submits a case
        case = Case.objects.create(
            title='Newly diagnosed stage 2 breast cancer',
            original_question='What are my treatment options and should I get a lumpectomy or mastectomy?',
            warrior=warrior
        )
        self.stdout.write(f'Created case: {case.id}')

        # 3. Moderator structures the case
        case = structure_case(
            case_id=case.id,
            actor=mod,
            structured_summary='Patient is a 45yo female with ER+ PR+ HER2- invasive ductal carcinoma...',
            expected_version=1
        )
        self.stdout.write('Moderator structured case')

        # 4. Moderator transitions to UNDER_DISCUSSION
        case = transition_case(
            case_id=case.id,
            actor=mod,
            new_status='UNDER_DISCUSSION',
            expected_version=2
        )

        # 5. Moderator invites Doctors
        invite_doctor(case_id=case.id, doctor_id=doc1.id, actor=mod)
        invite_doctor(case_id=case.id, doctor_id=doc2.id, actor=mod)
        self.stdout.write('Invited doctors')

        # 7. Doctors comment
        c1 = create_comment(
            case_id=case.id,
            author=doc1,
            content='Given the ER+ status, endocrine therapy is highly recommended post-surgery.',
            is_anonymous=True
        )

        c2 = create_comment(
            case_id=case.id,
            author=doc2,
            content='I agree, and lumpectomy with radiation is a standard approach here.',
            is_anonymous=True,
            parent_id=c1.id
        )

        # 8. Moderator publishes answer
        published_answer = publish_answer(
            case_id=case.id,
            actor=mod,
            content='The consensus is that lumpectomy followed by radiation and endocrine therapy is a strong option for your profile. Please consult your local care team.',
            expected_version=3
        )
        self.stdout.write('Published answer')

        self.stdout.write(self.style.SUCCESS('Successfully seeded demo data!'))
