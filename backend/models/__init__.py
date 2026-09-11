# backend/models/__init__.py
# Import all models so SQLAlchemy can find them

from .user         import User
from .category     import Category
from .income       import Income
from .expense      import Expense
from .budget       import Budget
from .savings_goal import SavingsGoal
from .notification import Notification
from .ai_prediction import AIPrediction