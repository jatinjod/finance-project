# backend/routes/investment_routes.py
# FinanceAI — Educational Investment Planner
#
# This is a transparent financial-planning simulator.
# It is NOT a SEBI-registered investment advisory service.

from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from models.income import Income
from models.expense import Expense
from models.savings_goal import SavingsGoal


investment_bp = Blueprint(
    "investment",
    __name__
)


# ============================================================
# HELPERS
# ============================================================

def clamp(value, minimum, maximum):
    return max(
        minimum,
        min(
            value,
            maximum
        )
    )


def safe_float(value, default=0.0):
    try:
        number = float(value)
        if number != number:
            return default
        return number
    except (TypeError, ValueError):
        return default


def get_last_six_months():
    """Return six calendar months ending with the current month."""

    today = date.today()

    months = []

    year = today.year
    month = today.month

    for _ in range(6):

        months.append(
            (year, month)
        )

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    months.reverse()

    return months


def build_monthly_totals(records):
    """
    Build totals for the latest six calendar months.
    Months with no records are kept as zero.
    """

    months = get_last_six_months()

    totals = {
        key: 0.0
        for key in months
    }

    for record in records:

        if not record.date:
            continue

        key = (
            record.date.year,
            record.date.month
        )

        if key in totals:
            totals[key] += safe_float(
                record.amount
            )

    return [
        round(
            totals[key],
            2
        )
        for key in months
    ]


def get_profile_base(profile):
    return {
        "conservative": 20,
        "balanced": 50,
        "growth": 75,
        "aggressive": 90
    }.get(
        profile,
        50
    )


def get_base_allocation(profile):

    allocations = {

        "conservative": {
            "equity": 20,
            "debt": 60,
            "gold": 10,
            "cash": 10
        },

        "balanced": {
            "equity": 45,
            "debt": 40,
            "gold": 10,
            "cash": 5
        },

        "growth": {
            "equity": 65,
            "debt": 25,
            "gold": 5,
            "cash": 5
        },

        "aggressive": {
            "equity": 80,
            "debt": 15,
            "gold": 3,
            "cash": 2
        }
    }

    return dict(
        allocations.get(
            profile,
            allocations["balanced"]
        )
    )


def adjust_allocation(
    allocation,
    horizon_years,
    monthly_expense,
    emergency_fund
):
    """
    Reduce equity exposure for short horizons or weak
    emergency-fund readiness.

    This is an educational scenario adjustment.
    """

    result = dict(
        allocation
    )

    # Short-term goals should not be heavily equity-oriented.
    if horizon_years <= 2 and result["equity"] > 30:

        reduction = result["equity"] - 30

        result["equity"] = 30
        result["debt"] += reduction

    # Weak emergency fund -> keep more liquid/capital-preserving.
    emergency_target = (
        monthly_expense * 3
    )

    if (
        monthly_expense > 0
        and emergency_fund < emergency_target
        and result["equity"] > 40
    ):

        reduction = result["equity"] - 40

        result["equity"] = 40
        result["cash"] += reduction

    return result


def calculate_readiness_score(
    profile,
    horizon_years,
    monthly_income,
    monthly_expense,
    emergency_fund
):

    score = get_profile_base(
        profile
    )

    surplus = (
        monthly_income -
        monthly_expense
    )

    # Longer horizons improve the planner's readiness signal.
    if horizon_years >= 10:
        score += 8
    elif horizon_years >= 5:
        score += 4
    elif horizon_years <= 2:
        score -= 12

    # Negative surplus is a strong warning.
    if surplus <= 0:

        score -= 15

    elif (
        monthly_income > 0
        and surplus >= monthly_income * 0.25
    ):

        score += 5

    # Emergency-fund readiness.
    if monthly_expense > 0:

        months_covered = (
            emergency_fund /
            monthly_expense
        )

        if months_covered >= 6:
            score += 5

        elif months_covered < 3:
            score -= 8

    score = int(
        clamp(
            score,
            0,
            100
        )
    )

    if score >= 80:
        grade = "Excellent"
    elif score >= 65:
        grade = "Strong"
    elif score >= 45:
        grade = "Moderate"
    elif score >= 30:
        grade = "Needs Attention"
    else:
        grade = "High Risk"

    return score, grade


def calculate_sip_required(
    target_amount,
    annual_rate,
    years
):
    """
    Educational monthly-contribution calculation.
    Returns required monthly contribution.
    """

    target_amount = safe_float(
        target_amount
    )

    annual_rate = safe_float(
        annual_rate
    )

    years = safe_float(
        years
    )

    if (
        target_amount <= 0
        or years <= 0
    ):
        return 0.0

    months = int(
        years * 12
    )

    monthly_rate = (
        annual_rate / 100
    ) / 12

    if monthly_rate <= 0:
        return round(
            target_amount / months,
            2
        )

    factor = (
        (1 + monthly_rate) ** months
    )

    required = (
        target_amount *
        monthly_rate /
        (factor - 1)
    )

    return round(
        required,
        2
    )


def calculate_future_value(
    monthly_investment,
    annual_rate,
    years
):
    """
    Educational future-value calculation.
    """

    monthly_investment = safe_float(
        monthly_investment
    )

    annual_rate = safe_float(
        annual_rate
    )

    years = safe_float(
        years
    )

    if (
        monthly_investment <= 0
        or years <= 0
    ):
        return 0.0

    months = int(
        years * 12
    )

    monthly_rate = (
        annual_rate / 100
    ) / 12

    if monthly_rate <= 0:

        return round(
            monthly_investment * months,
            2
        )

    future_value = (
        monthly_investment *
        (
            ((1 + monthly_rate) ** months - 1)
            / monthly_rate
        )
    )

    return round(
        future_value,
        2
    )


def build_action_plan(
    profile,
    horizon_years,
    monthly_income,
    monthly_expense,
    emergency_fund,
    monthly_investment
):

    actions = []

    surplus = (
        monthly_income -
        monthly_expense
    )

    emergency_target = (
        monthly_expense * 6
    )

    emergency_gap = max(
        emergency_target -
        emergency_fund,
        0
    )

    if surplus <= 0:

        actions.append({
            "priority": "high",
            "title": "Fix monthly cash flow",
            "message": (
                "Your current average expenses are "
                "equal to or above your average income. "
                "Build positive monthly surplus before "
                "increasing investment contributions."
            )
        })

    if (
        emergency_gap > 0
        and monthly_expense > 0
    ):

        actions.append({
            "priority": "high",
            "title": "Build an emergency fund",
            "message": (
                f"Illustrative six-month emergency "
                f"target: ₹{emergency_target:,.0f}. "
                f"Current shortfall: ₹{emergency_gap:,.0f}."
            )
        })

    if horizon_years <= 2:

        actions.append({
            "priority": "high",
            "title": "Protect short-term goals",
            "message": (
                "For short horizons, the planner keeps "
                "the educational allocation more "
                "capital-preserving and liquid."
            )
        })

    if monthly_investment <= 0:

        actions.append({
            "priority": "medium",
            "title": "Set an investment budget",
            "message": (
                "Enter a monthly investment amount to "
                "see an illustrative allocation and "
                "goal projection."
            )
        })

    if profile in (
        "growth",
        "aggressive"
    ):

        actions.append({
            "priority": "medium",
            "title": "Review volatility tolerance",
            "message": (
                "Higher-growth profiles can experience "
                "larger drawdowns. Keep the time horizon "
                "long enough for the plan's risk level."
            )
        })

    actions.append({
        "priority": "info",
        "title": "Diversify",
        "message": (
            "Avoid concentrating the entire portfolio "
            "in one asset class."
        )
    })

    actions.append({
        "priority": "info",
        "title": "Review periodically",
        "message": (
            "Re-check the plan whenever your income, "
            "expenses, goals or time horizon changes."
        )
    })

    return actions


# ============================================================
# INVESTMENT PLANNER
# POST /api/investment/planner
# ============================================================

@investment_bp.route(
    "/api/investment/planner",
    methods=["POST"]
)
@jwt_required()
def investment_planner():

    user_id = int(
        get_jwt_identity()
    )

    data = request.get_json(
        silent=True
    ) or {}

    profile = str(
        data.get(
            "risk_profile",
            "balanced"
        )
    ).strip().lower()

    allowed_profiles = {
        "conservative",
        "balanced",
        "growth",
        "aggressive"
    }

    if profile not in allowed_profiles:

        return jsonify({
            "error": (
                "Invalid risk profile. "
                "Use conservative, balanced, "
                "growth or aggressive."
            )
        }), 400

    horizon_years = int(
        safe_float(
            data.get(
                "horizon_years",
                5
            ),
            5
        )
    )

    horizon_years = int(
        clamp(
            horizon_years,
            1,
            30
        )
    )

    goal_amount = safe_float(
        data.get(
            "goal_amount",
            0
        )
    )

    monthly_investment = safe_float(
        data.get(
            "monthly_investment",
            0
        )
    )

    emergency_fund = safe_float(
        data.get(
            "emergency_fund",
            0
        )
    )

    if goal_amount < 0:
        goal_amount = 0

    if monthly_investment < 0:
        monthly_investment = 0

    if emergency_fund < 0:
        emergency_fund = 0

    # --------------------------------------------------------
    # Read user's existing financial data.
    # --------------------------------------------------------

    income_records = (
        Income.query
        .filter_by(
            user_id=user_id
        )
        .all()
    )

    expense_records = (
        Expense.query
        .filter_by(
            user_id=user_id
        )
        .all()
    )

    savings_goals = (
        SavingsGoal.query
        .filter_by(
            user_id=user_id
        )
        .all()
    )

    monthly_income_values = (
        build_monthly_totals(
            income_records
        )
    )

    monthly_expense_values = (
        build_monthly_totals(
            expense_records
        )
    )

    monthly_income = round(
        sum(monthly_income_values) / 6,
        2
    )

    monthly_expense = round(
        sum(monthly_expense_values) / 6,
        2
    )

    monthly_surplus = round(
        monthly_income -
        monthly_expense,
        2
    )

    savings_goal_count = len(
        savings_goals
    )

    # --------------------------------------------------------
    # Readiness score.
    # --------------------------------------------------------

    readiness_score, readiness_grade = (
        calculate_readiness_score(
            profile=profile,
            horizon_years=horizon_years,
            monthly_income=monthly_income,
            monthly_expense=monthly_expense,
            emergency_fund=emergency_fund
        )
    )

    # --------------------------------------------------------
    # Educational allocation.
    # --------------------------------------------------------

    allocation = get_base_allocation(
        profile
    )

    allocation = adjust_allocation(
        allocation=allocation,
        horizon_years=horizon_years,
        monthly_expense=monthly_expense,
        emergency_fund=emergency_fund
    )

    # Re-normalize to 100.
    total_percentage = sum(
        allocation.values()
    )

    if total_percentage != 100:

        for key in allocation:
            allocation[key] = round(
                allocation[key] *
                100 /
                total_percentage,
                2
            )

    # Fix floating rounding residue.
    residue = round(
        100 -
        sum(allocation.values()),
        2
    )

    allocation["cash"] = round(
        allocation["cash"] +
        residue,
        2
    )

    monthly_allocation = {}

    for asset_class, percentage in allocation.items():

        monthly_allocation[asset_class] = round(
            monthly_investment *
            percentage /
            100,
            2
        )

    # --------------------------------------------------------
    # Emergency fund status.
    # --------------------------------------------------------

    emergency_target = round(
        monthly_expense * 6,
        2
    )

    emergency_gap = round(
        max(
            emergency_target -
            emergency_fund,
            0
        ),
        2
    )

    emergency_months = round(
        emergency_fund /
        monthly_expense,
        1
    ) if monthly_expense > 0 else 0

    # --------------------------------------------------------
    # Goal projection scenarios.
    # These returns are hypothetical, not promised.
    # --------------------------------------------------------

    scenarios = []

    for rate in (
        6,
        8,
        10
    ):

        required_monthly = (
            calculate_sip_required(
                target_amount=goal_amount,
                annual_rate=rate,
                years=horizon_years
            )
            if goal_amount > 0
            else 0
        )

        projected_value = (
            calculate_future_value(
                monthly_investment=monthly_investment,
                annual_rate=rate,
                years=horizon_years
            )
            if monthly_investment > 0
            else 0
        )

        gap = round(
            max(
                goal_amount -
                projected_value,
                0
            ),
            2
        )

        scenarios.append({
            "assumed_annual_rate": rate,
            "required_monthly_investment": required_monthly,
            "projected_value": projected_value,
            "goal_gap": gap
        })

    # --------------------------------------------------------
    # Action plan.
    # --------------------------------------------------------

    action_plan = build_action_plan(
        profile=profile,
        horizon_years=horizon_years,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        emergency_fund=emergency_fund,
        monthly_investment=monthly_investment
    )

    return jsonify({
        "status": "success",

        "data": {

            "planner_type": (
                "educational_financial_planner"
            ),

            "risk_profile": profile,

            "horizon_years": horizon_years,

            "financial_snapshot": {
                "average_monthly_income": monthly_income,
                "average_monthly_expense": monthly_expense,
                "average_monthly_surplus": monthly_surplus,
                "months_analyzed": 6,
                "income_records": len(income_records),
                "expense_records": len(expense_records),
                "savings_goal_count": savings_goal_count
            },

            "readiness": {
                "score": readiness_score,
                "grade": readiness_grade
            },

            "emergency_fund": {
                "current": round(
                    emergency_fund,
                    2
                ),
                "illustrative_target": emergency_target,
                "shortfall": emergency_gap,
                "months_covered": emergency_months
            },

            "educational_allocation": allocation,

            "monthly_allocation": monthly_allocation,

            "monthly_investment": round(
                monthly_investment,
                2
            ),

            "goal_projection": {
                "goal_amount": round(
                    goal_amount,
                    2
                ),
                "scenarios": scenarios
            },

            "action_plan": action_plan,

            "monthly_history": {
                "income": monthly_income_values,
                "expenses": monthly_expense_values
            },

            "disclaimer": (
                "Educational planning only. "
                "Illustrative asset allocations and "
                "return scenarios are not guarantees, "
                "personalized securities recommendations "
                "or a substitute for advice from a "
                "SEBI-registered Investment Adviser."
            )
        }
    }), 200