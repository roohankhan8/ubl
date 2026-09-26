from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


class DashboardSummaryTests(TestCase):
    def test_empty_dashboard_returns_zeroes(self):
        user = get_user_model().objects.create_user(username="viewer")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["transactions"], 0)
        self.assertEqual(response.data["imports"], 0)
        self.assertEqual(response.data["match_rate"], "0.00")
        self.assertEqual(response.data["recent_imports"], [])
