DB schema notes — Theme and ThemePackage (complete context for LLM and Python app)

-----
1) High-level plan
- Summarize the Prisma schema for Theme and ThemePackage exactly as it appears in the DB.
- Explain the root cause of the error seen by the Python app.
- Provide explicit, copy-paste-ready SQLAlchemy model suggestions and quick fixes.
- List concrete next steps the agent must take to be compliant with the DB.

-----
2) Prisma schema excerpt (truth source)

model ThemePackage {
  id          String   @id @default(cuid())
  name        String
  description String?
  coverLetterTemplateId String
  resumeTemplateId String
  // Referential actions: prevent deleting a Theme that's in use by a package
  coverLetterTemplate Theme @relation("CoverLetterTheme", fields: [coverLetterTemplateId], references: [id], onDelete: Restrict, onUpdate: Cascade)
  resumeTemplate Theme @relation("ResumeTheme", fields: [resumeTemplateId], references: [id], onDelete: Restrict, onUpdate: Cascade)

  // Timestamps for auditing
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  // Ensure the same pair cannot be duplicated
  @@unique([resumeTemplateId, coverLetterTemplateId])
  // Helpful lookup indexes
  @@index([resumeTemplateId])
  @@index([coverLetterTemplateId])
  @@map("theme_packages")
}

model Theme {
  id              String       @id @default(cuid())
  name            String       @unique
  description     String?
  type            ThemeType
  template        String
  styles          String
  previewImageUrl String?
  createdAt       DateTime     @default(now())
  updatedAt       DateTime     @updatedAt
  resumes         Resume[]
  coverLetters    CoverLetter[]
  coverLetterThemePackages ThemePackage[] @relation("CoverLetterTheme")
  resumeThemePackages ThemePackage[] @relation("ResumeTheme")

  @@index([type])
  @@map("themes")
}

enum ThemeType {
  RESUME
  COVER_LETTER
}

-----
3) Key facts the Python app must respect
- Table names in the database (as mapped by Prisma):
  - themes
  - theme_packages

- Column names (Prisma uses camelCase field names and by default the DB columns keep the same names):
  For `theme_packages` table the expected column names are exactly:
    - id
    - name
    - description
    - coverLetterTemplateId   <-- NOTE: camelCase
    - resumeTemplateId        <-- NOTE: camelCase
    - createdAt
    - updatedAt

  For `themes` table the expected column names are exactly:
    - id
    - name
    - description
    - type                    <-- enum text: 'RESUME' or 'COVER_LETTER'
    - template
    - styles
    - previewImageUrl         <-- camelCase
    - createdAt
    - updatedAt

- Constraints and referential behavior:
  - `coverLetterTemplateId` and `resumeTemplateId` are FOREIGN KEYS to `themes.id` with onDelete=RESTRICT and onUpdate=CASCADE.
  - Unique constraint on (resumeTemplateId, coverLetterTemplateId).
  - `Theme.name` is UNIQUE.
  - `Theme.type` must be one of the enum values: 'RESUME' or 'COVER_LETTER'.

-----
4) Root cause of the error you saw
- The Python app attempted to INSERT into `theme_packages` using snake_case column names: `resume_template_id` and `cover_letter_template_id`.
- The actual DB columns (from the Prisma schema) are camelCase: `resumeTemplateId`, `coverLetterTemplateId`.
- Result: PostgreSQL raises `UndefinedColumn: column "resume_template_id" of relation "theme_packages" does not exist`.

-----
5) Two safe ways to fix the Python app (pick one)

Option A — Update the Python/SQLAlchemy models to use the exact camelCase column names used by the DB (recommended quick fix):
- Define SQLAlchemy columns with explicit column names matching the DB, e.g. Column('resumeTemplateId', String, ForeignKey('themes.id', ondelete='RESTRICT', onupdate='CASCADE')).
- This avoids schema migrations.

Example SQLAlchemy models (copy-paste-ready):

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Theme(Base):
    __tablename__ = 'themes'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    type = Column(String, nullable=False)  # values: 'RESUME' or 'COVER_LETTER'
    template = Column(String, nullable=False)
    styles = Column(String, nullable=False)
    previewImageUrl = Column('previewImageUrl', String)

    createdAt = Column('createdAt', DateTime, server_default=func.now())
    updatedAt = Column('updatedAt', DateTime, onupdate=func.now())

    # relationships if needed
    resume_packages = relationship('ThemePackage', back_populates='resume_template', foreign_keys='ThemePackage.resumeTemplateId')
    cover_letter_packages = relationship('ThemePackage', back_populates='cover_letter_template', foreign_keys='ThemePackage.coverLetterTemplateId')

class ThemePackage(Base):
    __tablename__ = 'theme_packages'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)

    # Use explicit DB column names (camelCase) to match the Prisma-managed DB
    resumeTemplateId = Column('resumeTemplateId', String, ForeignKey('themes.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    coverLetterTemplateId = Column('coverLetterTemplateId', String, ForeignKey('themes.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)

    createdAt = Column('createdAt', DateTime, server_default=func.now())
    updatedAt = Column('updatedAt', DateTime, onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('resumeTemplateId', 'coverLetterTemplateId', name='uq_resume_cover_pair'),
        Index('idx_resume_template', 'resumeTemplateId'),
        Index('idx_cover_letter_template', 'coverLetterTemplateId'),
    )

    # relationships
    resume_template = relationship('Theme', foreign_keys=[resumeTemplateId])
    cover_letter_template = relationship('Theme', foreign_keys=[coverLetterTemplateId])

Notes for Option A:
- Keep the column name string exactly as shown: 'resumeTemplateId' and 'coverLetterTemplateId'.
- Make sure any raw SQL or ORM insert uses those exact column names or uses model attributes above.

Option B — Change the DB column names to snake_case or map fields explicitly in Prisma and migrate (more invasive):
- If you want snake_case column names in the DB, you must either:
  1) Update the Prisma schema to map field names using @map("resume_template_id") for each field and run a migration / prisma db push; OR
  2) Create a DB migration that renames columns to snake_case.
- This is higher risk and unnecessary unless you standardize on snake_case across the entire DB.

-----
6) Other checks the agent should make before inserting
- Ensure the referenced Theme rows exist (the theme IDs you insert into resumeTemplateId and coverLetterTemplateId must be present in `themes.id`). Because onDelete=RESTRICT, insert will fail if foreign key constraint not satisfied.
- Ensure `Theme.type` uses one of: 'RESUME' or 'COVER_LETTER'.
- Handle unique constraint on (resumeTemplateId, coverLetterTemplateId): either catch duplicate key errors or check for existence before insert.
- Handle uniqueness of `Theme.name` when inserting Themes.

-----
7) Quick, concrete fixes for the error log you posted
- The error SQL shows this attempted INSERT:
  INSERT INTO theme_packages (id, name, description, resume_template_id, cover_letter_template_id, "createdAt", "updatedAt") VALUES (...)

  Fix: change the INSERT to use camelCase column names:
  INSERT INTO theme_packages (id, name, description, resumeTemplateId, coverLetterTemplateId, "createdAt", "updatedAt") VALUES (...)

- Or update the SQLAlchemy Column definitions to map to the correct DB column names (see Option A models above).

-----
8) Minimal test plan the agent can run locally
- Query `
  SELECT column_name FROM information_schema.columns WHERE table_name='theme_packages' ORDER BY ordinal_position;
  `
  to verify actual column names.
- Insert a theme row first, then insert a theme_package row that references that theme id.
- Verify SELECT * FROM theme_packages returns the new row.

-----
9) Short checklist (for the agent)
- [ ] Confirm actual DB column names for `theme_packages` (likely camelCase). If you cannot query, assume camelCase because Prisma uses camelCase by default.
- [ ] Update SQLAlchemy models to use exact DB column names (use Column('resumeTemplateId', ...)).
- [ ] Ensure foreign key values reference existing `themes.id` rows.
- [ ] Use enum values 'RESUME' or 'COVER_LETTER' for Theme.type.
- [ ] Handle UNIQUE constraints (name on Theme, pair on ThemePackage).

-----
10) Final notes
- The simplest, lowest-risk change is to adjust the Python ORM column names to match the DB (camelCase). This will immediately fix the "UndefinedColumn" error.
- If you prefer snake_case columns everywhere, perform an explicit schema migration and update Prisma and all consumers.

If you want, I can also produce a migration SQL snippet or a small script that checks the column names and patches a SQLAlchemy model automatically; tell me which you'd prefer as the next step.
