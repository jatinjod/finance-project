# backend/routes/analytics_routes.py
# All data analytics and export endpoints

import math
from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request, Response, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.monthly_analysis import (
    get_monthly_summary,
    get_monthly_trend,
    get_monthly_comparison
)

from services.category_analysis import (
    get_category_breakdown,
    get_category_trends,
    get_spending_velocity
)

from services.trend_analysis import (
    get_overall_trend,
    get_percentile_analysis,
    get_weekday_analysis,
    get_income_vs_expense_ratio
)

from services.budget_analysis import (
    get_budget_utilization,
    get_budget_adherence_score
)

from services.savings_analysis import (
    get_savings_overview,
    get_savings_projection
)

from services.export_service import (
    export_transactions_csv,
    export_monthly_report_csv,
    generate_pdf_report
)


analytics_bp = Blueprint('analytics', __name__)


# ============================================================
# JSON SAFETY
# ============================================================

def _json_safe(value):
    """
    Convert analytics values into strict JSON-safe values.

    Handles:
    - NaN
    - +Infinity
    - -Infinity
    - Decimal
    - datetime
    - date
    - nested dicts
    - nested lists
    - tuples
    """

    # --------------------------------------------------------
    # FLOAT
    # --------------------------------------------------------

    if isinstance(value, float):

        if math.isnan(value) or math.isinf(value):
            return 0.0

        return value


    # --------------------------------------------------------
    # DECIMAL
    # --------------------------------------------------------

    if isinstance(value, Decimal):

        number = float(value)

        if math.isnan(number) or math.isinf(number):
            return 0.0

        return number


    # --------------------------------------------------------
    # DATE / DATETIME
    # --------------------------------------------------------

    if isinstance(value, (datetime, date)):
        return value.isoformat()


    # --------------------------------------------------------
    # DICT
    # --------------------------------------------------------

    if isinstance(value, dict):

        return {
            key: _json_safe(val)
            for key, val in value.items()
        }


    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if isinstance(value, list):

        return [
            _json_safe(item)
            for item in value
        ]


    # --------------------------------------------------------
    # TUPLE
    # --------------------------------------------------------

    if isinstance(value, tuple):

        return [
            _json_safe(item)
            for item in value
        ]


    # --------------------------------------------------------
    # OTHER VALUES
    # --------------------------------------------------------

    return value


# ============================================================
# MONTH / YEAR HELPER
# ============================================================

def _month_year():
    """Extract month/year from query params."""

    today = date.today()

    month = request.args.get(
        'month',
        today.month,
        type=int
    )

    year = request.args.get(
        'year',
        today.year,
        type=int
    )

    if not (1 <= month <= 12):
        month = today.month

    return month, year


# ============================================================
# MONTHLY SUMMARY
# GET /api/analytics/monthly
# ============================================================

@analytics_bp.route(
    '/api/analytics/monthly',
    methods=['GET']
)
@jwt_required()
def monthly_summary():

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    try:

        data = get_monthly_summary(
            user_id,
            year,
            month
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# MONTHLY TREND
# GET /api/analytics/trend
# ============================================================

@analytics_bp.route(
    '/api/analytics/trend',
    methods=['GET']
)
@jwt_required()
def monthly_trend():

    user_id = int(
        get_jwt_identity()
    )

    months = request.args.get(
        'months',
        6,
        type=int
    )

    months = max(
        2,
        min(12, months)
    )

    try:

        data = get_monthly_trend(
            user_id,
            months
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# MONTH COMPARISON
# GET /api/analytics/comparison
# ============================================================

@analytics_bp.route(
    '/api/analytics/comparison',
    methods=['GET']
)
@jwt_required()
def monthly_comparison():

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    try:

        data = get_monthly_comparison(
            user_id,
            year,
            month
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# CATEGORY BREAKDOWN
# GET /api/analytics/categories
# ============================================================

@analytics_bp.route(
    '/api/analytics/categories',
    methods=['GET']
)
@jwt_required()
def category_breakdown():

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    try:

        data = get_category_breakdown(
            user_id,
            year,
            month
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# CATEGORY TRENDS
# GET /api/analytics/category-trends
# ============================================================

@analytics_bp.route(
    '/api/analytics/category-trends',
    methods=['GET']
)
@jwt_required()
def category_trends():

    user_id = int(
        get_jwt_identity()
    )

    months = request.args.get(
        'months',
        6,
        type=int
    )

    months = max(
        2,
        min(12, months)
    )

    try:

        data = get_category_trends(
            user_id,
            months
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# SPENDING VELOCITY
# GET /api/analytics/velocity
# ============================================================

@analytics_bp.route(
    '/api/analytics/velocity',
    methods=['GET']
)
@jwt_required()
def spending_velocity():

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    try:

        data = get_spending_velocity(
            user_id,
            year,
            month
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# OVERALL TREND
# GET /api/analytics/overall-trend
# ============================================================

@analytics_bp.route(
    '/api/analytics/overall-trend',
    methods=['GET']
)
@jwt_required()
def overall_trend():

    user_id = int(
        get_jwt_identity()
    )

    months = request.args.get(
        'months',
        6,
        type=int
    )

    months = max(
        2,
        min(12, months)
    )

    try:

        data = get_overall_trend(
            user_id,
            months
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# PERCENTILE ANALYSIS
# GET /api/analytics/percentiles
# ============================================================

@analytics_bp.route(
    '/api/analytics/percentiles',
    methods=['GET']
)
@jwt_required()
def percentile_analysis():

    user_id = int(
        get_jwt_identity()
    )

    try:

        data = get_percentile_analysis(
            user_id
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# WEEKDAY ANALYSIS
# GET /api/analytics/weekday
# ============================================================

@analytics_bp.route(
    '/api/analytics/weekday',
    methods=['GET']
)
@jwt_required()
def weekday_analysis():

    user_id = int(
        get_jwt_identity()
    )

    try:

        data = get_weekday_analysis(
            user_id
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# INCOME VS EXPENSE RATIO
# GET /api/analytics/ratio
# ============================================================

@analytics_bp.route(
    '/api/analytics/ratio',
    methods=['GET']
)
@jwt_required()
def income_expense_ratio():

    user_id = int(
        get_jwt_identity()
    )

    months = request.args.get(
        'months',
        6,
        type=int
    )

    months = max(
        2,
        min(12, months)
    )

    try:

        data = get_income_vs_expense_ratio(
            user_id,
            months
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# BUDGET UTILIZATION HISTORY
# GET /api/analytics/budget-utilization
# ============================================================

@analytics_bp.route(
    '/api/analytics/budget-utilization',
    methods=['GET']
)
@jwt_required()
def budget_utilization():

    user_id = int(
        get_jwt_identity()
    )

    months = request.args.get(
        'months',
        3,
        type=int
    )

    months = max(
        1,
        min(12, months)
    )

    try:

        data = get_budget_utilization(
            user_id,
            months
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# BUDGET ADHERENCE SCORE
# GET /api/analytics/adherence
# ============================================================

@analytics_bp.route(
    '/api/analytics/adherence',
    methods=['GET']
)
@jwt_required()
def budget_adherence():

    user_id = int(
        get_jwt_identity()
    )

    try:

        data = get_budget_adherence_score(
            user_id
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# SAVINGS OVERVIEW
# GET /api/analytics/savings
# ============================================================

@analytics_bp.route(
    '/api/analytics/savings',
    methods=['GET']
)
@jwt_required()
def savings_overview():

    user_id = int(
        get_jwt_identity()
    )

    try:

        data = get_savings_overview(
            user_id
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# SAVINGS PROJECTION
# GET /api/analytics/savings/projection/<goal_id>
# ============================================================

@analytics_bp.route(
    '/api/analytics/savings/projection/<int:goal_id>',
    methods=['GET']
)
@jwt_required()
def savings_projection(goal_id):

    user_id = int(
        get_jwt_identity()
    )

    monthly_saving = request.args.get(
        'monthly_saving',
        0,
        type=float
    )

    if monthly_saving <= 0:

        return jsonify({
            "error": "monthly_saving must be positive"
        }), 400

    try:

        data = get_savings_projection(
            user_id,
            goal_id,
            monthly_saving
        )

        return jsonify({
            "status": "success",
            "data": _json_safe(data)
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# FULL ANALYTICS BUNDLE
# GET /api/analytics/full
# ============================================================

@analytics_bp.route(
    '/api/analytics/full',
    methods=['GET']
)
@jwt_required()
def full_analytics():
    """
    Return all analytics in a single request.
    Used by the enhanced reports page.
    """

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    months = request.args.get(
        'months',
        6,
        type=int
    )

    months = max(
        2,
        min(12, months)
    )

    try:

        result = {

            'monthly_summary':
                get_monthly_summary(
                    user_id,
                    year,
                    month
                ),

            'monthly_trend':
                get_monthly_trend(
                    user_id,
                    months
                ),

            'comparison':
                get_monthly_comparison(
                    user_id,
                    year,
                    month
                ),

            'category_breakdown':
                get_category_breakdown(
                    user_id,
                    year,
                    month
                ),

            'category_trends':
                get_category_trends(
                    user_id,
                    months
                ),

            'spending_velocity':
                get_spending_velocity(
                    user_id,
                    year,
                    month
                ),

            'overall_trend':
                get_overall_trend(
                    user_id,
                    months
                ),

            'weekday_analysis':
                get_weekday_analysis(
                    user_id
                ),

            'ratio':
                get_income_vs_expense_ratio(
                    user_id,
                    months
                ),

            'percentiles':
                get_percentile_analysis(
                    user_id
                ),

            'budget_adherence':
                get_budget_adherence_score(
                    user_id
                ),

            'savings':
                get_savings_overview(
                    user_id
                )
        }


        # --------------------------------------------------------
        # IMPORTANT:
        # Sanitize the COMPLETE nested analytics result.
        # This prevents NaN / Infinity from breaking JSON.
        # --------------------------------------------------------

        safe_result = _json_safe(
            result
        )


        return jsonify({
            "status": "success",
            "data": safe_result
        }), 200


    except Exception as e:

        import traceback

        print(
            traceback.format_exc()
        )

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# EXPORT: TRANSACTIONS CSV
# GET /api/analytics/export/csv
# ============================================================

@analytics_bp.route(
    '/api/analytics/export/csv',
    methods=['GET']
)
@jwt_required()
def export_csv():

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    trans_type = request.args.get(
        'type',
        'all'
    )

    try:

        csv_io = export_transactions_csv(
            user_id,
            year,
            month,
            trans_type
        )

        filename = (
            f"transactions_{year}_{month:02d}.csv"
        )

        response = make_response(
            csv_io.read()
        )

        response.headers[
            'Content-Type'
        ] = 'text/csv'

        response.headers[
            'Content-Disposition'
        ] = (
            f'attachment; filename={filename}'
        )

        return response

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# EXPORT: MONTHLY REPORT CSV
# GET /api/analytics/export/report-csv
# ============================================================

@analytics_bp.route(
    '/api/analytics/export/report-csv',
    methods=['GET']
)
@jwt_required()
def export_report_csv():

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    try:

        csv_io = export_monthly_report_csv(
            user_id,
            year,
            month
        )

        filename = (
            f"report_{year}_{month:02d}.csv"
        )

        response = make_response(
            csv_io.read()
        )

        response.headers[
            'Content-Type'
        ] = 'text/csv'

        response.headers[
            'Content-Disposition'
        ] = (
            f'attachment; filename={filename}'
        )

        return response

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# EXPORT: PDF REPORT
# GET /api/analytics/export/pdf
# ============================================================

@analytics_bp.route(
    '/api/analytics/export/pdf',
    methods=['GET']
)
@jwt_required()
def export_pdf():

    user_id = int(
        get_jwt_identity()
    )

    month, year = _month_year()

    try:

        html = generate_pdf_report(
            user_id,
            year,
            month
        )

        return Response(
            html,
            mimetype='text/html'
        )

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500