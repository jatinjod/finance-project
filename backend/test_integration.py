# backend/test_integration.py
# Quick integration test to verify everything is connected
# Run from backend folder:
# python test_integration.py

import requests
from datetime import date

BASE = "http://localhost:5000"
TIMEOUT = 10

PASS = "✅"
FAIL = "❌"


def test(name, condition, detail=""):
    status = PASS if condition else FAIL
    message = f"  {status} {name}"

    if detail:
        message += f" — {detail}"

    print(message)
    return bool(condition)


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {}


def request(method, url, **kwargs):
    try:
        return requests.request(
            method,
            url,
            timeout=TIMEOUT,
            **kwargs
        )
    except requests.RequestException as error:
        print(f"  {FAIL} Request failed — {error}")
        return None


def get_token(response):
    if response is None:
        return None

    data = safe_json(response)

    return (
        data.get("data", {})
        .get("access_token")
        if isinstance(data.get("data"), dict)
        else None
    )


def login(email, password):
    response = request(
        "POST",
        f"{BASE}/api/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    if response is None:
        return None, None

    token = get_token(response)

    return response, token


def register_if_needed(email, password, name):
    response, token = login(email, password)

    if response is not None and response.status_code == 200:
        return response, token

    register_response = request(
        "POST",
        f"{BASE}/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password
        }
    )

    if register_response is None:
        return None, None

    if register_response.status_code not in [200, 201, 409]:
        return register_response, None

    return login(email, password)


def get_category_ids(headers):
    response = request(
        "GET",
        f"{BASE}/api/categories",
        headers=headers
    )

    if response is None or response.status_code != 200:
        return None, None

    body = safe_json(response)
    categories = body.get("data", [])

    if not isinstance(categories, list):
        return None, None

    income_category_id = None
    expense_category_id = None

    for category in categories:
        if not isinstance(category, dict):
            continue

        category_type = category.get("type")
        category_id = category.get("id")

        if category_id is None:
            continue

        if category_type == "income" and income_category_id is None:
            income_category_id = category_id

        if category_type == "expense" and expense_category_id is None:
            expense_category_id = category_id

    return income_category_id, expense_category_id


print("\n" + "=" * 55)
print("  FinanceAI Integration Test")
print("=" * 55 + "\n")

all_passed = True

today = date.today().isoformat()


# =========================================================
# 1. HEALTH
# =========================================================

print("1. Health Check")

r = request(
    "GET",
    f"{BASE}/api/health"
)

if r is None:
    all_passed &= test(
        "Server running",
        False
    )
    all_passed &= test(
        "Database connected",
        False
    )
else:
    health_data = safe_json(r)

    all_passed &= test(
        "Server running",
        r.status_code == 200
    )

    all_passed &= test(
        "Database connected",
        health_data.get("database") == "connected"
    )

    all_passed &= test(
        "CORS enabled",
        health_data.get("cors") == "enabled"
    )


# =========================================================
# 2. AUTHENTICATION
# =========================================================

print("\n2. Authentication")

test_email = "integration_test_user@example.com"
SECRET_VALUE = os.getenv("SECRET_VALUE")

login_response, token = register_if_needed(
    test_email,
    test_password,
    "Integration Test User"
)

all_passed &= test(
    "Login",
    login_response is not None
    and login_response.status_code == 200
)

all_passed &= test(
    "JWT token received",
    bool(token)
)

headers = (
    {
        "Authorization": f"Bearer {token}"
    }
    if token
    else {}
)


# =========================================================
# 3. JWT PROTECTION
# =========================================================

print("\n3. JWT Authentication")

r = request(
    "GET",
    f"{BASE}/api/user/profile",
    headers=headers
)

all_passed &= test(
    "Profile protected route",
    r is not None and r.status_code == 200
)

r = request(
    "GET",
    f"{BASE}/api/user/profile"
)

all_passed &= test(
    "Rejected without token",
    r is not None and r.status_code in [401, 422]
)


# =========================================================
# 4. CATEGORIES
# =========================================================

print("\n4. Categories")

income_category_id, expense_category_id = get_category_ids(
    headers
)

r = request(
    "GET",
    f"{BASE}/api/categories",
    headers=headers
)

all_passed &= test(
    "Get categories",
    r is not None and r.status_code == 200
)

categories = []

if r is not None and r.status_code == 200:
    categories = safe_json(r).get("data", [])

all_passed &= test(
    "Default categories exist",
    isinstance(categories, list)
    and len(categories) >= 5,
    f"{len(categories)} found"
)

all_passed &= test(
    "Income category available",
    income_category_id is not None
)

all_passed &= test(
    "Expense category available",
    expense_category_id is not None
)


# =========================================================
# 5. INCOME
# =========================================================

print("\n5. Income")

income_id = None

if income_category_id is not None:

    income_data = {
        "category_id": income_category_id,
        "amount": 50000,
        "date": today,
        "note": "Integration test income"
    }

    r = request(
        "POST",
        f"{BASE}/api/income",
        json=income_data,
        headers=headers
    )

    all_passed &= test(
        "Add income",
        r is not None and r.status_code == 201
    )

    if r is not None and r.status_code == 201:
        income_id = (
            safe_json(r)
            .get("data", {})
            .get("id")
        )

    all_passed &= test(
        "Income ID returned",
        income_id is not None
    )

    r = request(
        "GET",
        f"{BASE}/api/income",
        headers=headers
    )

    all_passed &= test(
        "Get income",
        r is not None and r.status_code == 200
    )

    if (
        income_id is not None
        and r is not None
        and r.status_code == 200
    ):
        income_records = safe_json(r).get(
            "data",
            []
        )

        found_income = any(
            item.get("id") == income_id
            for item in income_records
            if isinstance(item, dict)
        )

        all_passed &= test(
            "Added income appears in list",
            found_income
        )

else:
    all_passed &= test(
        "Income tests skipped",
        False,
        "No income category available"
    )


# =========================================================
# 6. EXPENSES
# =========================================================

print("\n6. Expenses")

expense_id = None

if expense_category_id is not None:

    expense_data = {
        "category_id": expense_category_id,
        "amount": 5000,
        "date": today,
        "note": "Integration test expense"
    }

    r = request(
        "POST",
        f"{BASE}/api/expenses",
        json=expense_data,
        headers=headers
    )

    all_passed &= test(
        "Add expense",
        r is not None and r.status_code == 201
    )

    if r is not None and r.status_code == 201:
        expense_id = (
            safe_json(r)
            .get("data", {})
            .get("id")
        )

    all_passed &= test(
        "Expense ID returned",
        expense_id is not None
    )

    if expense_id is not None:

        r = request(
            "PUT",
            f"{BASE}/api/expenses/{expense_id}",
            json={
                "amount": 5500
            },
            headers=headers
        )

        all_passed &= test(
            "Edit expense",
            r is not None and r.status_code == 200
        )

        r = request(
            "DELETE",
            f"{BASE}/api/expenses/{expense_id}",
            headers=headers
        )

        all_passed &= test(
            "Delete expense",
            r is not None and r.status_code == 200
        )

else:
    all_passed &= test(
        "Expense tests skipped",
        False,
        "No expense category available"
    )


# =========================================================
# 7. BUDGET
# =========================================================

print("\n7. Budget")

budget_data = {
    "month": date.today().month,
    "year": date.today().year,
    "amount": 30000
}

r = request(
    "POST",
    f"{BASE}/api/budget",
    json=budget_data,
    headers=headers
)

all_passed &= test(
    "Set budget",
    r is not None and r.status_code in [200, 201]
)

r = request(
    "GET",
    f"{BASE}/api/budget/status",
    headers=headers
)

all_passed &= test(
    "Get budget status",
    r is not None and r.status_code == 200
)


# =========================================================
# 8. DASHBOARD
# =========================================================

print("\n8. Dashboard")

r = request(
    "GET",
    f"{BASE}/api/dashboard/summary",
    headers=headers
)

all_passed &= test(
    "Dashboard loads",
    r is not None and r.status_code == 200
)

if r is not None and r.status_code == 200:

    dashboard_body = safe_json(r)
    dashboard_data = dashboard_body.get(
        "data",
        {}
    )

    all_passed &= test(
        "Has summary data",
        isinstance(
            dashboard_data.get("summary"),
            dict
        )
    )

    all_passed &= test(
        "Has monthly chart",
        isinstance(
            dashboard_data.get("monthly_chart"),
            list
        )
    )

    all_passed &= test(
        "Has recent transactions",
        isinstance(
            dashboard_data.get("recent_transactions"),
            list
        )
    )


# =========================================================
# 9. REPORTS
# =========================================================

print("\n9. Reports")

current_month = date.today().month
current_year = date.today().year

r = request(
    "GET",
    (
        f"{BASE}/api/reports/monthly"
        f"?month={current_month}"
        f"&year={current_year}"
    ),
    headers=headers
)

all_passed &= test(
    "Monthly report",
    r is not None and r.status_code == 200
)

r = request(
    "GET",
    f"{BASE}/api/reports/trend?months=6",
    headers=headers
)

all_passed &= test(
    "Trend report",
    r is not None and r.status_code == 200
)

r = request(
    "GET",
    (
        f"{BASE}/api/reports/category"
        f"?month={current_month}"
        f"&year={current_year}"
    ),
    headers=headers
)

all_passed &= test(
    "Category report",
    r is not None and r.status_code == 200
)


# =========================================================
# 10. AI INSIGHTS
# =========================================================

print("\n10. AI Insights")

r = request(
    "GET",
    f"{BASE}/api/ai/insights",
    headers=headers
)

all_passed &= test(
    "AI endpoint responds",
    r is not None and r.status_code == 200
)

if r is not None and r.status_code == 200:

    ai_body = safe_json(r)
    ai_data = ai_body.get(
        "data",
        {}
    )

    ai_status = ai_data.get(
        "status"
    )

    ai_valid_response = ai_status in [
        "success",
        "insufficient_data"
    ]

    all_passed &= test(
        "AI response structure valid",
        ai_valid_response,
        ai_status or "unknown"
    )

    if ai_status == "success":

        all_passed &= test(
            "AI prediction available",
            isinstance(
                ai_data.get("prediction"),
                dict
            )
        )

        all_passed &= test(
            "Budget recommendation available",
            isinstance(
                ai_data.get("recommendations"),
                dict
            )
        )

        all_passed &= test(
            "Spending patterns available",
            isinstance(
                ai_data.get("patterns"),
                dict
            )
        )

        all_passed &= test(
            "Anomaly analysis available",
            isinstance(
                ai_data.get("anomalies"),
                dict
            )
        )

        all_passed &= test(
            "AI tips available",
            isinstance(
                ai_data.get("tips"),
                list
            )
        )

    elif ai_status == "insufficient_data":

        all_passed &= test(
            "AI correctly reports insufficient data",
            True,
            "Add more expenses for full AI analysis"
        )


# =========================================================
# 11. NOTIFICATIONS
# =========================================================

print("\n11. Notifications")

r = request(
    "GET",
    f"{BASE}/api/notifications",
    headers=headers
)

all_passed &= test(
    "Get notifications",
    r is not None and r.status_code == 200
)

if r is not None and r.status_code == 200:

    notification_data = safe_json(r)

    all_passed &= test(
        "Notification data valid",
        isinstance(
            notification_data.get("data"),
            list
        )
    )

r = request(
    "PUT",
    f"{BASE}/api/notifications/read-all",
    headers=headers
)

all_passed &= test(
    "Mark all read",
    r is not None and r.status_code == 200
)


# =========================================================
# 12. ADMIN
# =========================================================

print("\n12. Admin")

admin_login, admin_token = login(
    "admin@finance.com",
    "admin123"
)

all_passed &= test(
    "Admin login",
    admin_login is not None
    and admin_login.status_code == 200
)

admin_headers = (
    {
        "Authorization": f"Bearer {admin_token}"
    }
    if admin_token
    else {}
)

r = request(
    "GET",
    f"{BASE}/api/admin/users",
    headers=admin_headers
)

all_passed &= test(
    "Admin get users",
    r is not None and r.status_code == 200
)

if r is not None and r.status_code == 200:

    admin_users_data = safe_json(r)

    all_passed &= test(
        "Admin pagination available",
        isinstance(
            admin_users_data.get("pagination"),
            dict
        )
    )

r = request(
    "GET",
    f"{BASE}/api/admin/stats",
    headers=admin_headers
)

all_passed &= test(
    "Admin get stats",
    r is not None and r.status_code == 200
)

r = request(
    "GET",
    f"{BASE}/api/admin/users",
    headers=headers
)

all_passed &= test(
    "Normal user blocked from admin",
    r is not None and r.status_code == 403
)


# =========================================================
# 13. DATA ISOLATION
# =========================================================

print("\n13. Data Isolation")

isolation_email = (
    "isolation_test_user@example.com"
)

isolation_password = "password123"

isolation_login, isolation_token = (
    register_if_needed(
        isolation_email,
        isolation_password,
        "Isolation Test User"
    )
)

all_passed &= test(
    "Isolation user login",
    isolation_login is not None
    and isolation_login.status_code == 200
)

isolation_headers = (
    {
        "Authorization": f"Bearer {isolation_token}"
    }
    if isolation_token
    else {}
)

# Add one income to isolation user
isolation_income_id = None

if (
    isolation_token
    and income_category_id is not None
):

    r = request(
        "POST",
        f"{BASE}/api/income",
        json={
            "category_id": income_category_id,
            "amount": 1111,
            "date": today,
            "note": "Isolation test income"
        },
        headers=isolation_headers
    )

    if r is not None and r.status_code == 201:
        isolation_income_id = (
            safe_json(r)
            .get("data", {})
            .get("id")
        )

# Get both users' income
r1 = request(
    "GET",
    f"{BASE}/api/income",
    headers=headers
)

r2 = request(
    "GET",
    f"{BASE}/api/income",
    headers=isolation_headers
)

if (
    r1 is not None
    and r2 is not None
    and r1.status_code == 200
    and r2.status_code == 200
):

    user1_income = safe_json(r1).get(
        "data",
        []
    )

    user2_income = safe_json(r2).get(
        "data",
        []
    )

    user1_ids = {
        item.get("user_id")
        for item in user1_income
        if isinstance(item, dict)
        and item.get("user_id") is not None
    }

    user2_ids = {
        item.get("user_id")
        for item in user2_income
        if isinstance(item, dict)
        and item.get("user_id") is not None
    }

    isolation_passed = (
        user1_ids.isdisjoint(user2_ids)
    )

    all_passed &= test(
        "Users see only own data",
        isolation_passed,
        (
            f"User 1: {len(user1_income)} records, "
            f"User 2: {len(user2_income)} records"
        )
    )

else:

    all_passed &= test(
        "Users see only own data",
        False,
        "Could not fetch both users' income"
    )


# =========================================================
# 14. CLEANUP
# =========================================================

print("\n14. Test Cleanup")

if income_id is not None:

    r = request(
        "DELETE",
        f"{BASE}/api/income/{income_id}",
        headers=headers
    )

    all_passed &= test(
        "Cleanup integration income",
        r is not None and r.status_code == 200
    )

if isolation_income_id is not None:

    r = request(
        "DELETE",
        f"{BASE}/api/income/{isolation_income_id}",
        headers=isolation_headers
    )

    all_passed &= test(
        "Cleanup isolation income",
        r is not None and r.status_code == 200
    )


# =========================================================
# FINAL RESULT
# =========================================================

print("\n" + "=" * 55)
print("  Integration Test Complete")
print("=" * 55)

if all_passed:
    print("\n  Overall Result: ✅ ALL TESTS PASSED")
else:
    print("\n  Overall Result: ❌ SOME TESTS FAILED")

print(f"\n  Backend URL: {BASE}")
print("\n  If a test fails, check the exact ❌ line above.")
print("=" * 55 + "\n")