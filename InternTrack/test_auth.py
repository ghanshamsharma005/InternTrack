import unittest
from werkzeug.security import generate_password_hash
from app import create_app
from database.db import db
from models import User, Student

class TestAuthenticationLayer(unittest.TestCase):
    def setUp(self):
        """
        Creates an isolated testing client in memory.
        """
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-2026'
        self.client = self.app.test_client()
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """
        Tears down database sessions and clears contexts.
        """
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_student_registration_flow(self):
        """
        1. Verifies that a valid student registration creates both User and Student database profiles.
        Also validates that passwords are encrypted using Werkzeug.
        """
        response = self.client.post('/register', data={
            'name': 'Bob Student',
            'email': 'bob@student.edu',
            'roll_no': 'ROLL001',
            'course': 'Software Engineering',
            'semester': '4',
            'phone': '1234567890',
            'password': 'safe_password123',
            'confirm_password': 'safe_password123'
        }, follow_redirects=True)
        
        # Verify user database record
        user = User.query.filter_by(email='bob@student.edu').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'student')
        self.assertNotEqual(user.password_hash, 'safe_password123')  # Verify encryption
        
        # Verify student database record
        student = Student.query.filter_by(roll_no='ROLL001').first()
        self.assertIsNotNone(student)
        self.assertEqual(student.user_id, user.id)
        self.assertEqual(student.course, 'Software Engineering')
        self.assertEqual(student.semester, 4)
        
    def test_registration_duplicate_email(self):
        """
        2. Validates that duplicate email registration attempts are caught.
        """
        user = User(name='Existing User', email='dup@test.com', password_hash='hash', role='student')
        db.session.add(user)
        db.session.commit()
        
        response = self.client.post('/register', data={
            'name': 'Bob Student',
            'email': 'dup@test.com',
            'roll_no': 'ROLL002',
            'course': 'IT',
            'semester': '2',
            'phone': '',
            'password': 'pass',
            'confirm_password': 'pass'
        })
        self.assertIn(b'Email already registered.', response.data)
        
    def test_registration_duplicate_roll_number(self):
        """
        3. Validates that duplicate roll number registrations are blocked.
        """
        user = User(name='User A', email='usera@test.com', password_hash='hash', role='student')
        db.session.add(user)
        db.session.commit()
        student = Student(user_id=user.id, roll_no='ROLL_DUP', course='CS', semester=2)
        db.session.add(student)
        db.session.commit()
        
        response = self.client.post('/register', data={
            'name': 'Student B',
            'email': 'userb@test.com',
            'roll_no': 'ROLL_DUP',
            'course': 'IT',
            'semester': '2',
            'phone': '',
            'password': 'pass',
            'confirm_password': 'pass'
        })
        self.assertIn(b'Roll number already registered.', response.data)

    def test_login_success_and_failures(self):
        """
        4. Checks that valid credentials logs a user in and sets session keys.
        5. Checks that incorrect passwords are rejected with validation alerts.
        """
        hashed = generate_password_hash('correct_password')
        user = User(name='John Doe', email='john@example.com', password_hash=hashed, role='student')
        db.session.add(user)
        db.session.commit()
        
        # Valid login trigger
        response = self.client.post('/login', data={
            'email': 'john@example.com',
            'password': 'correct_password'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/student/dashboard')
        
        # Verify session registration keys
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('user_id'), user.id)
            self.assertEqual(sess.get('role'), 'student')
            self.assertEqual(sess.get('user_name'), 'John Doe')
            
        # Clear active session before testing bad credentials login
        self.client.get('/logout')
            
        # Invalid password trigger
        response_bad = self.client.post('/login', data={
            'email': 'john@example.com',
            'password': 'wrong_password'
        })
        self.assertEqual(response_bad.status_code, 200)
        self.assertIn(b'Invalid email or password.', response_bad.data)


    def test_logout_session_clearing(self):
        """
        6. Verifies logout triggers complete session key removals.
        """
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'student'
            sess['user_name'] = 'Test User'
            
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')
        
        # Confirm cleared session
        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)
            self.assertNotIn('role', sess)
            self.assertNotIn('user_name', sess)

    def test_authorization_protection_walls(self):
        """
        7. Student accessing admin dashboard raises 403 Forbidden.
        8. Student accessing faculty dashboard raises 403 Forbidden.
        """
        hashed = generate_password_hash('pwd')
        user = User(name='Alice Student', email='alice@student.com', password_hash=hashed, role='student')
        db.session.add(user)
        db.session.commit()
        student = Student(user_id=user.id, roll_no='STU_AUTH', course='CS', semester=2)
        db.session.add(student)
        db.session.commit()

        # Log in student session
        self.client.post('/login', data={
            'email': 'alice@student.com',
            'password': 'pwd'
        })

        # Test Student accessing Admin dashboard
        response_admin = self.client.get('/admin/dashboard')
        self.assertEqual(response_admin.status_code, 403)
        self.assertIn(b'403 - Access Denied', response_admin.data)

        # Test Student accessing Faculty dashboard
        response_faculty = self.client.get('/faculty/dashboard')
        self.assertEqual(response_faculty.status_code, 403)
        self.assertIn(b'403 - Access Denied', response_faculty.data)

    def test_unauthenticated_access_protection(self):
        """
        9. Unauthenticated users trying to access dashboard endpoints are redirected to Login.
        """
        response = self.client.get('/student/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/login')

if __name__ == '__main__':
    unittest.main()
