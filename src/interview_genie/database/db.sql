-- =========================================================
-- 1. CREATE DATABASE
-- =========================================================
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'InterviewGenie')
BEGIN
    CREATE DATABASE InterviewGenie;
END
GO

USE InterviewGenie

-- =========================================================
-- 3. CANDIDATES
-- =========================================================
CREATE TABLE candidates (
    candidate_id        UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    full_name           NVARCHAR(255) NOT NULL,
    email                NVARCHAR(255) UNIQUE,
    phone                NVARCHAR(50),
    password_hash        NVARCHAR(255) NULL,
    created_at           DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- =========================================================
-- 4. RESUME_INFO
-- =========================================================
CREATE TABLE resume_info (
    resume_id             UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    candidate_id           UNIQUEIDENTIFIER NOT NULL,
    resume_pdf_path          NVARCHAR(1000),
    resume_text                NVARCHAR(MAX) NOT NULL,
    resume_parsed                NVARCHAR(MAX) NOT NULL,
    created_at                    DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_resume_info_candidate FOREIGN KEY (candidate_id)
        REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    CONSTRAINT CK_resume_parsed_json CHECK (ISJSON(resume_parsed) = 1)
);
GO

GO

-- =========================================================
-- 5. INTERVIEW
-- =========================================================
CREATE TABLE interview (
    interview_id              UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    candidate_id                UNIQUEIDENTIFIER NOT NULL,
    resume_id                     UNIQUEIDENTIFIER NOT NULL,
    thread_id                       NVARCHAR(255) NOT NULL UNIQUE,
    target_role                       NVARCHAR(255) NOT NULL,
    interview_prep_topic                 NVARCHAR(MAX),
    interview_script                       NVARCHAR(MAX),
    status                                    NVARCHAR(20) NOT NULL DEFAULT 'not_started'
                                              CONSTRAINT CK_interview_status
                                              CHECK (status IN ('not_started', 'in_progress', 'completed')),
    total_score                                DECIMAL(5,2) NOT NULL DEFAULT 0,
    question_count                               INT NOT NULL DEFAULT 0,
    interview_feed_back                            NVARCHAR(MAX),
    started_at                                      DATETIME2,
    completed_at                                     DATETIME2,
    created_at                                        DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_interview_candidate FOREIGN KEY (candidate_id)
        REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    CONSTRAINT FK_interview_resume FOREIGN KEY (resume_id)
        REFERENCES resume_info(resume_id) ON DELETE NO ACTION,
    CONSTRAINT CK_interview_prep_json CHECK (interview_prep_topic IS NULL OR ISJSON(interview_prep_topic) = 1),
    CONSTRAINT CK_interview_script_json CHECK (interview_script IS NULL OR ISJSON(interview_script) = 1),
    CONSTRAINT CK_interview_feedback_json CHECK (interview_feed_back IS NULL OR ISJSON(interview_feed_back) = 1)
);
GO

