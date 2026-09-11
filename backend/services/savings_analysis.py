# backend/services/savings_analysis.py
# Savings goal progress and projection analysis

import numpy as np
from datetime import date
from models.savings_goal import SavingsGoal


def get_savings_overview(user_id):
    """
    Complete overview of all savings goals with projections.
    """
    goals = SavingsGoal.query.filter_by(user_id=user_id).all()

    if not goals:
        return {
            'goals':           [],
            'summary':         {},
            'overall_progress': 0
        }

    active    = [g for g in goals if not g.is_complete]
    completed = [g for g in goals if g.is_complete]

    total_target  = sum(float(g.target_amount) for g in goals)
    total_saved   = sum(float(g.saved_amount)  for g in goals)
    overall_progress = round(
        (total_saved / total_target * 100), 2
    ) if total_target > 0 else 0

    goals_data = []
    for g in goals:
        target   = float(g.target_amount)
        saved    = float(g.saved_amount)
        progress = round((saved / target * 100), 2) if target > 0 else 0
        remaining = round(max(target - saved, 0), 2)

        # Days calculation
        days_until_deadline = None
        is_overdue          = False
        if g.deadline and not g.is_complete:
            today               = date.today()
            delta               = (g.deadline - today).days
            days_until_deadline = delta
            is_overdue          = delta < 0

        # Monthly saving needed to hit goal on time
        monthly_needed = None
        if g.deadline and not g.is_complete and days_until_deadline \
                and days_until_deadline > 0 and remaining > 0:
            months_left    = max(1, days_until_deadline / 30)
            monthly_needed = round(remaining / months_left, 2)

        goals_data.append({
            'id':                   g.id,
            'name':                 g.name,
            'target_amount':        target,
            'saved_amount':         round(saved, 2),
            'remaining_amount':     remaining,
            'progress_percentage':  min(progress, 100),
            'deadline':             g.deadline.isoformat() if g.deadline else None,
            'days_until_deadline':  days_until_deadline,
            'is_complete':          g.is_complete,
            'is_overdue':           is_overdue,
            'monthly_needed':       monthly_needed,
            'created_at':           g.created_at.isoformat() if g.created_at else None
        })

    goals_data.sort(
        key=lambda x: (x['is_complete'], -x['progress_percentage'])
    )

    return {
        'goals': goals_data,
        'summary': {
            'total_goals':     len(goals),
            'active_goals':    len(active),
            'completed_goals': len(completed),
            'total_target':    round(total_target, 2),
            'total_saved':     round(total_saved, 2),
            'total_remaining': round(max(total_target - total_saved, 0), 2),
            'overall_progress': overall_progress
        },
        'overall_progress': overall_progress
    }


def get_savings_projection(user_id, goal_id, monthly_saving):
    """
    Project when a savings goal will be reached
    given a monthly saving amount.
    """
    goal = SavingsGoal.query.filter_by(
        id=goal_id, user_id=user_id
    ).first()

    if not goal:
        return {'error': 'Goal not found'}

    target    = float(goal.target_amount)
    saved     = float(goal.saved_amount)
    remaining = max(target - saved, 0)

    if monthly_saving <= 0:
        return {'error': 'Monthly saving must be positive'}

    if remaining == 0:
        return {
            'status':             'already_complete',
            'months_to_complete': 0,
            'completion_date':    date.today().isoformat()
        }

    months_needed = int(np.ceil(remaining / monthly_saving))

    from datetime import date
    from dateutil.relativedelta import relativedelta

    try:
        completion_date = date.today() + relativedelta(months=months_needed)
    except Exception:
        from datetime import timedelta
        completion_date = date.today() + timedelta(days=months_needed * 30)

    # Monthly milestones
    milestones = []
    for m in range(1, min(months_needed + 1, 13)):
        projected_saved = min(saved + (monthly_saving * m), target)
        projected_pct   = round((projected_saved / target * 100), 1)
        milestones.append({
            'month':      m,
            'saved':      round(projected_saved, 2),
            'percentage': projected_pct
        })

    return {
        'status':             'projected',
        'goal_name':          goal.name,
        'target':             target,
        'currently_saved':    round(saved, 2),
        'remaining':          round(remaining, 2),
        'monthly_saving':     round(monthly_saving, 2),
        'months_to_complete': months_needed,
        'completion_date':    completion_date.isoformat(),
        'milestones':         milestones
    }