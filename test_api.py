import unittest
from main import app 


class FlaskApiTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_home(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.get_json(), "Welcome to the Shop API!")


if __name__ == '__main__':
    unittest.main()















