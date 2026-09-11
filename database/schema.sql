-- ============================================================
-- AI-Powered Personal Finance & Expense Management System
-- Database Schema
-- Version: 1.0
-- ============================================================

-- Create and select the database
CREATE DATABASE IF NOT EXISTS finance_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE finance_db;

-- ============================================================
-- TABLE 1: users
-- ============================================================
CREATE TABLE users (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(100)  NOT NULL,
    email            VARCHAR(150)  NOT NULL UNIQUE,
    password_hash    VARCHAR(255)  NOT NULL,
    role             ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    profile_picture  VARCHAR(255)  NULL,
    is_active        BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE 2: categories
-- ============================================================
CREATE TABLE categories (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT           NULL,
    name         VARCHAR(100)  NOT NULL,
    type         ENUM('income', 'expense') NOT NULL,
    is_default   BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_categories_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- TABLE 3: income
-- ============================================================
CREATE TABLE income (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT              NOT NULL,
    category_id  INT              NOT NULL,
    amount       DECIMAL(12, 2)   NOT NULL CHECK (amount > 0),
    date         DATE             NOT NULL,
    note         VARCHAR(255)     NULL,
    created_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_income_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_income_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_income_user_date ON income (user_id, date);

-- ============================================================
-- TABLE 4: expenses
-- ============================================================
CREATE TABLE expenses (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT              NOT NULL,
    category_id  INT              NOT NULL,
    amount       DECIMAL(12, 2)   NOT NULL CHECK (amount > 0),
    date         DATE             NOT NULL,
    note         VARCHAR(255)     NULL,
    created_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_expenses_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_expenses_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_expenses_user_date ON expenses (user_id, date);

-- ============================================================
-- TABLE 5: budgets
-- ============================================================
CREATE TABLE budgets (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT              NOT NULL,
    category_id  INT              NULL,
    month        DATE             NOT NULL,
    amount       DECIMAL(12, 2)   NOT NULL CHECK (amount > 0),
    created_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_budgets_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_budgets_category
        FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE SET NULL,

    CONSTRAINT uq_budget_user_category_month
        UNIQUE (user_id, category_id, month)
);

-- ============================================================
-- TABLE 6: savings_goals
-- ============================================================
CREATE TABLE savings_goals (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT              NOT NULL,
    name           VARCHAR(150)     NOT NULL,
    target_amount  DECIMAL(12, 2)   NOT NULL CHECK (target_amount > 0),
    saved_amount   DECIMAL(12, 2)   NOT NULL DEFAULT 0.00
                                    CHECK (saved_amount >= 0),
    deadline       DATE             NULL,
    is_complete    BOOLEAN          NOT NULL DEFAULT FALSE,
    created_at     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_savings_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- ============================================================
-- TABLE 7: notifications
-- ============================================================
CREATE TABLE notifications (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL,
    message     VARCHAR(255) NOT NULL,
    type        ENUM(
                    'budget_warning',
                    'budget_exceeded',
                    'anomaly',
                    'goal_achieved',
                    'general'
                ) NOT NULL DEFAULT 'general',
    is_read     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_notifications_user_read
    ON notifications (user_id, is_read);

-- ============================================================
-- TABLE 8: ai_predictions
-- ============================================================
CREATE TABLE ai_predictions (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT          NOT NULL,
    prediction_type  ENUM(
                         'expense_pred',
                         'budget_rec',
                         'pattern',
                         'anomaly',
                         'tip'
                     ) NOT NULL,
    prediction_data  JSON         NOT NULL,
    generated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ai_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_ai_user_type
    ON ai_predictions (user_id, prediction_type, generated_at);

-- ============================================================
-- SEED DATA: Default Categories
-- ============================================================
INSERT INTO categories (user_id, name, type, is_default) VALUES
-- Income categories
(NULL, 'Salary',        'income',  TRUE),
(NULL, 'Freelance',     'income',  TRUE),
(NULL, 'Business',      'income',  TRUE),
(NULL, 'Investment',    'income',  TRUE),
(NULL, 'Gift',          'income',  TRUE),
(NULL, 'Other Income',  'income',  TRUE),
-- Expense categories
(NULL, 'Food',          'expense', TRUE),
(NULL, 'Transport',     'expense', TRUE),
(NULL, 'Rent',          'expense', TRUE),
(NULL, 'Shopping',      'expense', TRUE),
(NULL, 'Entertainment', 'expense', TRUE),
(NULL, 'Healthcare',    'expense', TRUE),
(NULL, 'Education',     'expense', TRUE),
(NULL, 'Utilities',     'expense', TRUE),
(NULL, 'Travel',        'expense', TRUE),
(NULL, 'Other Expense', 'expense', TRUE);