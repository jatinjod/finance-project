# backend/ml_models/category_suggester.py
# Suggests expense categories based on transaction notes
# Uses keyword matching + frequency-based rules

import re
from collections import defaultdict


class CategorySuggester:
    """
    Suggests a category for a new expense based on its note/description.
    Uses keyword matching with a comprehensive financial keyword dictionary.
    """

    # Keyword → Category mapping
    KEYWORD_MAP = {
        # Food
        'Food': [
            'food', 'grocery', 'groceries', 'supermarket', 'restaurant',
            'lunch', 'dinner', 'breakfast', 'meal', 'eat', 'pizza', 'burger',
            'cafe', 'coffee', 'tea', 'snack', 'fruits', 'vegetables', 'meat',
            'chicken', 'rice', 'bread', 'milk', 'eggs', 'sweets', 'bakery',
            'hotel', 'dhaba', 'tiffin', 'canteen', 'mess', 'zomato', 'swiggy'
        ],
        # Transport
        'Transport': [
            'transport', 'travel', 'bus', 'auto', 'cab', 'taxi', 'uber',
            'ola', 'metro', 'train', 'fuel', 'petrol', 'diesel', 'parking',
            'toll', 'bike', 'cycle', 'rickshaw', 'fare', 'ticket'
        ],
        # Rent
        'Rent': [
            'rent', 'house rent', 'flat rent', 'room rent',
            'accommodation', 'pg', 'paying guest', 'hostel fee'
        ],
        # Shopping
        'Shopping': [
            'shopping', 'clothes', 'shirt', 'pant', 'shoes', 'dress',
            'amazon', 'flipkart', 'myntra', 'meesho', 'online shopping',
            'store', 'mall', 'purchase', 'bought', 'accessories'
        ],
        # Entertainment
        'Entertainment': [
            'entertainment', 'movie', 'cinema', 'netflix', 'hotstar',
            'prime', 'spotify', 'youtube premium', 'gaming', 'game',
            'concert', 'event', 'party', 'outing', 'picnic', 'tour',
            'travel', 'weekend', 'fun', 'amusement'
        ],
        # Healthcare
        'Healthcare': [
            'health', 'doctor', 'hospital', 'clinic', 'medicine',
            'medical', 'pharmacy', 'chemist', 'tablet', 'injection',
            'test', 'lab', 'scan', 'xray', 'blood test', 'checkup',
            'dentist', 'gym', 'fitness'
        ],
        # Education
        'Education': [
            'education', 'school', 'college', 'university', 'fees',
            'tuition', 'coaching', 'course', 'book', 'notebook', 'stationary',
            'study', 'exam', 'udemy', 'coursera', 'online course', 'tutorial'
        ],
        # Utilities
        'Utilities': [
            'utility', 'electricity', 'water', 'gas', 'internet', 'wifi',
            'mobile', 'recharge', 'phone bill', 'broadband', 'cable', 'dth',
            'bill', 'maintenance', 'society'
        ],
        # Travel
        'Travel': [
            'flight', 'hotel booking', 'trip', 'holiday', 'vacation',
            'airport', 'visa', 'passport', 'luggage', 'suitcase',
            'tourism', 'foreign', 'international'
        ]
    }

    def __init__(self):
        # Build reverse index: keyword → category
        self.keyword_index = {}
        for category, keywords in self.KEYWORD_MAP.items():
            for keyword in keywords:
                self.keyword_index[keyword.lower()] = category

    def suggest(self, note, available_categories=None):
        """
        Suggest a category based on the note/description text.

        Returns:
            dict with suggested category and confidence score.
        """
        if not note:
            return {
                'suggested':    None,
                'confidence':   0,
                'method':       'no_input',
                'alternatives': []
            }

        note_lower = note.lower()
        scores     = defaultdict(int)

        # Score each keyword match
        for keyword, category in self.keyword_index.items():
            if keyword in note_lower:
                # Exact word match scores higher
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = len(re.findall(pattern, note_lower))
                scores[category] += (2 if matches > 0 else 1)

        if not scores:
            # Fallback: check for partial matches
            for keyword, category in self.keyword_index.items():
                if any(
                    k in note_lower
                    for k in keyword.split()
                    if len(k) > 3
                ):
                    scores[category] += 1

        if not scores:
            return {
                'suggested':    'Other Expense',
                'confidence':   10,
                'method':       'default',
                'alternatives': []
            }

        # Sort by score
        sorted_cats = sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )

        top_category = sorted_cats[0][0]
        top_score    = sorted_cats[0][1]
        total_score  = sum(s for _, s in sorted_cats)
        confidence   = round(
            (top_score / total_score * 100) if total_score > 0 else 0, 1
        )

        # Filter to available categories if provided
        if available_categories:
            available_names = [
                c.get('name', c) if isinstance(c, dict) else c
                for c in available_categories
            ]
            if top_category not in available_names:
                for cat, _ in sorted_cats:
                    if cat in available_names:
                        top_category = cat
                        break
                else:
                    top_category = 'Other Expense'

        alternatives = [
            cat for cat, _ in sorted_cats[1:4]
            if cat != top_category
        ]

        return {
            'suggested':    top_category,
            'confidence':   confidence,
            'method':       'keyword_matching',
            'alternatives': alternatives,
            'note_analyzed': note
        }

    def learn_from_history(self, expense_df):
        """
        Learn from user's historical note → category patterns.
        Adds user-specific keyword associations.
        """
        if expense_df is None or expense_df.empty:
            return

        # Build frequency map of note words → categories
        word_category_freq = defaultdict(lambda: defaultdict(int))

        for _, row in expense_df.iterrows():
            note     = str(row.get('note', '')).lower()
            category = str(row.get('category_name', ''))

            if note and category:
                words = re.findall(r'\b\w{3,}\b', note)
                for word in words:
                    word_category_freq[word][category] += 1

        # Add high-confidence patterns to keyword index
        for word, cat_counts in word_category_freq.items():
            if word in self.keyword_index:
                continue  # Don't override built-in keywords

            total = sum(cat_counts.values())
            for cat, count in cat_counts.items():
                if count >= 3 and (count / total) >= 0.7:
                    # This word reliably predicts this category
                    self.keyword_index[word] = cat


def suggest_category(note, available_categories=None, expense_data=None):
    """
    Standalone function interface.
    """
    suggester = CategorySuggester()

    if expense_data:
        df = __import__('pandas').DataFrame(expense_data)
        suggester.learn_from_history(df)

    return suggester.suggest(note, available_categories)