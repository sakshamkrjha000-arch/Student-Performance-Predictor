-- ============================================================
--  AI-Based Student Performance & Placement Prediction System
--  MySQL Database Schema  (MySQL 8.0+)
--  Run inside the MySQL shell:  SOURCE database.sql;
-- ============================================================

DROP DATABASE IF EXISTS student_prediction_db;
CREATE DATABASE student_prediction_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE student_prediction_db;

-- ------------------------------------------------------------
-- 1. users  (student login accounts)
-- ------------------------------------------------------------
CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(100)  NOT NULL,
    email         VARCHAR(120)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    role          ENUM('student') NOT NULL DEFAULT 'student',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2. admins  (separate table for admin accounts)
-- ------------------------------------------------------------
CREATE TABLE admins (
    admin_id      INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)   NOT NULL UNIQUE,
    email         VARCHAR(120)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    role          ENUM('admin') NOT NULL DEFAULT 'admin',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 3. students  (academic profile, 1-to-1 with users)
-- ------------------------------------------------------------
CREATE TABLE students (
    student_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    roll_number    VARCHAR(30)  NOT NULL UNIQUE,
    course         VARCHAR(80)  NOT NULL,
    semester       INT          NOT NULL,
    cgpa           DECIMAL(3,2) NOT NULL,
    attendance     DECIMAL(5,2) NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_students_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_semester  CHECK (semester BETWEEN 1 AND 8),
    CONSTRAINT chk_cgpa      CHECK (cgpa      BETWEEN 0 AND 10),
    CONSTRAINT chk_attend    CHECK (attendance BETWEEN 0 AND 100)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 4. performance_records  (inputs used by the performance model)
-- ------------------------------------------------------------
CREATE TABLE performance_records (
    perf_id               INT AUTO_INCREMENT PRIMARY KEY,
    student_id            INT NOT NULL,
    attendance_pct        DECIMAL(5,2) NOT NULL,
    assignment_marks      DECIMAL(5,2) NOT NULL,
    internal_marks        DECIMAL(5,2) NOT NULL,
    prev_semester_marks   DECIMAL(5,2) NOT NULL,
    study_hours           DECIMAL(4,1) NOT NULL,
    assignments_completed INT          NOT NULL,
    participation_score   DECIMAL(5,2) NOT NULL,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_perf_student
        FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_perf_attend  CHECK (attendance_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_perf_assign  CHECK (assignment_marks BETWEEN 0 AND 100),
    CONSTRAINT chk_perf_intern  CHECK (internal_marks BETWEEN 0 AND 100),
    CONSTRAINT chk_perf_prev    CHECK (prev_semester_marks BETWEEN 0 AND 100),
    CONSTRAINT chk_perf_hours   CHECK (study_hours BETWEEN 0 AND 16),
    CONSTRAINT chk_perf_completed CHECK (assignments_completed BETWEEN 0 AND 50),
    CONSTRAINT chk_perf_part    CHECK (participation_score BETWEEN 0 AND 10)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 5. placement_records  (inputs used by the placement model)
-- ------------------------------------------------------------
CREATE TABLE placement_records (
    place_id            INT AUTO_INCREMENT PRIMARY KEY,
    student_id          INT NOT NULL,
    cgpa                DECIMAL(3,2) NOT NULL,
    attendance          DECIMAL(5,2) NOT NULL,
    technical_score     DECIMAL(5,2) NOT NULL,
    communication_score DECIMAL(5,2) NOT NULL,
    projects_completed  INT          NOT NULL,
    internship_months   INT          NOT NULL,
    certifications      INT          NOT NULL,
    aptitude_score      DECIMAL(5,2) NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_place_student
        FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_place_cgpa   CHECK (cgpa BETWEEN 0 AND 10),
    CONSTRAINT chk_place_attend CHECK (attendance BETWEEN 0 AND 100),
    CONSTRAINT chk_place_tech   CHECK (technical_score BETWEEN 0 AND 100),
    CONSTRAINT chk_place_comm   CHECK (communication_score BETWEEN 0 AND 100),
    CONSTRAINT chk_place_proj   CHECK (projects_completed BETWEEN 0 AND 30),
    CONSTRAINT chk_place_int    CHECK (internship_months BETWEEN 0 AND 24),
    CONSTRAINT chk_place_cert   CHECK (certifications BETWEEN 0 AND 20),
    CONSTRAINT chk_place_apt    CHECK (aptitude_score BETWEEN 0 AND 100)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 6. predictions  (every prediction result, student or placement)
-- ------------------------------------------------------------
CREATE TABLE predictions (
    prediction_id   INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT NOT NULL,
    prediction_type ENUM('performance','placement') NOT NULL,
    result_label    VARCHAR(30)  NOT NULL,
    probability     DECIMAL(6,4) NULL,
    inputs_json     TEXT         NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pred_student
        FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Helpful indexes
-- ------------------------------------------------------------
CREATE INDEX idx_predictions_student ON predictions(student_id, prediction_type, created_at);
CREATE INDEX idx_students_user       ON students(user_id);

-- ------------------------------------------------------------
-- Seed data
--  Default admin login:  admin / admin123
--  Default student login: rahul@student.com / student123
--  Passwords below are real werkzeug hashes, never plain text.
-- ------------------------------------------------------------
INSERT INTO admins (username, email, password_hash) VALUES
('admin', 'admin@college.edu',
 'scrypt:32768:8:1$jCXBezQfIP9TCxtU$40c4c3f7482737f7518dd2bb282efe675859980243a29f3673a723a8f40c1170eea7c743c9f7cd3647abaff1775f621429572f8df1faa7b7017e468815cc27a4');

INSERT INTO users (full_name, email, password_hash) VALUES
('Rahul Sharma', 'rahul@student.com',
 'scrypt:32768:8:1$rd5KAipfTlmbey8V$e4ac0756a74a6ee5c3d35c22f090c84e2664b9b8da894ce718ea383e2c61e98ea9b6a05eef0219d92efbe7c738f1a381ffa468b0f1d872c9cdf7e78183ca0408');

INSERT INTO students (user_id, roll_number, course, semester, cgpa, attendance) VALUES
(1, 'CS2023001', 'BSc Artificial Intelligence & Machine Learning', 4, 8.20, 87.50);
