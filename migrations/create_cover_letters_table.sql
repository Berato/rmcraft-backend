-- Migration to create cover_letters table
-- Run this against your database to add the table

CREATE TABLE cover_letters (
  id VARCHAR PRIMARY KEY,
  title VARCHAR,
  jobDetails JSON,
  openingParagraph TEXT,
  bodyParagraphs JSON,
  companyConnection TEXT,
  closingParagraph TEXT,
  tone VARCHAR,
  finalContent TEXT,
  resumeId VARCHAR,
  jobProfileId VARCHAR,
  wordCount INTEGER,
  atsScore INTEGER,
  metadata JSON,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cover_letters_resumeId ON cover_letters(resumeId);
CREATE INDEX idx_cover_letters_jobProfileId ON cover_letters(jobProfileId);
