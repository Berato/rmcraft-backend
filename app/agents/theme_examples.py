"""
Example theme templates for resume and cover letter agents.

These examples demonstrate proper proportions, spacing, and layout for PDF rendering.
They should be used as reference examples in agent instructions.
"""

# Example Resume Template with proper proportions
EXAMPLE_RESUME_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Resume</title>
</head>
<body>
    <!-- HEADER SECTION: ~15% of page height -->
    <div class="header">
        <h1 class="name">{{ resume.personalInfo.firstName }} {{ resume.personalInfo.lastName }}</h1>
        <div class="contact-info">
            <span class="contact-item">{{ resume.personalInfo.email }}</span>
            <span class="contact-item">{{ resume.personalInfo.phone }}</span>
            {% if resume.personalInfo.location %}
            <span class="contact-item">{{ resume.personalInfo.location }}</span>
            {% endif %}
            {% if resume.personalInfo.linkedin %}
            <span class="contact-item">{{ resume.personalInfo.linkedin }}</span>
            {% endif %}
        </div>
    </div>

    <!-- SUMMARY SECTION: ~10-12% of page height, COMPACT styling -->
    {% if resume.summary %}
    <div class="summary-section">
        <h2 class="section-title">Professional Summary</h2>
        <p class="summary-text">{{ resume.summary }}</p>
    </div>
    {% endif %}

    <!-- EXPERIENCE SECTION: ~50-60% of page height -->
    {% if resume.experience and resume.experience|length > 0 %}
    <div class="experience-section">
        <h2 class="section-title">Experience</h2>
        {% for job in resume.experience %}
        <div class="experience-item section-keep">
            <div class="job-header">
                <div class="job-title-company">
                    <strong class="position">{{ job.position }}</strong>
                    <span class="company">{{ job.company }}</span>
                </div>
                <div class="job-dates">
                    {{ job.startDate }} - {{ job.endDate }}
                </div>
            </div>
            {% if job.responsibilities and job.responsibilities|length > 0 %}
            <ul class="responsibilities">
                {% for resp in job.responsibilities %}
                <li>{{ resp }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <!-- SKILLS SECTION: ~8-10% of page height -->
    {% if resume.skills and resume.skills|length > 0 %}
    <div class="skills-section">
        <h2 class="section-title">Skills</h2>
        <div class="skills-list">
            {% for skill in resume.skills %}
            <span class="skill-tag">{{ skill.name }}</span>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- EDUCATION SECTION: ~8-10% of page height -->
    {% if resume.education and resume.education|length > 0 %}
    <div class="education-section">
        <h2 class="section-title">Education</h2>
        {% for edu in resume.education %}
        <div class="education-item">
            <strong>{{ edu.degree }}</strong> - {{ edu.institution }}
            {% if edu.startDate or edu.endDate %}
            <span class="edu-dates">({{ edu.startDate }} - {{ edu.endDate }})</span>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
</body>
</html>"""

EXAMPLE_RESUME_STYLES = """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* PAGE SETUP - A4/Letter size with safe margins */
@page {
    size: Letter;
    margin: 0.5in; /* Safe padding for printing */
}

/* BASE STYLES */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', sans-serif;
    font-size: 10pt; /* Compact base size for print */
    line-height: 1.4; /* Moderate line height */
    color: #2c3e50;
}

/* UTILITY CLASSES for page break control */
.section-keep {
    page-break-inside: avoid;
    break-inside: avoid;
}

.header {
    page-break-after: avoid;
}

/* HEADER: Compact at ~15% of page */
.header {
    text-align: center;
    padding-bottom: 0.15in; /* Minimal bottom spacing */
    border-bottom: 2pt solid #3498db;
    margin-bottom: 0.15in; /* Minimal gap to next section */
}

.name {
    font-size: 18pt; /* Large but not excessive */
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 0.08in; /* Tight spacing */
    letter-spacing: 0.5pt;
}

.contact-info {
    font-size: 9pt; /* Smaller for compactness */
    color: #555;
}

.contact-item {
    margin: 0 0.1in;
    white-space: nowrap;
}

.contact-item:first-child {
    margin-left: 0;
}

/* SUMMARY: COMPACT at ~10-12% of page - KEY TO PREVENTING OVERFLOW */
.summary-section {
    margin-bottom: 0.15in; /* Minimal spacing */
}

.section-title {
    font-size: 11pt; /* Moderate section header size */
    font-weight: 700;
    color: #3498db;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    margin-bottom: 0.08in; /* Tight spacing */
    border-bottom: 1pt solid #ecf0f1;
    padding-bottom: 0.05in;
}

.summary-text {
    font-size: 10pt; /* Same as body - not larger */
    line-height: 1.4; /* Moderate line height */
    color: #34495e;
    text-align: justify;
    padding: 0; /* No extra padding */
    margin: 0; /* No extra margin */
}

/* EXPERIENCE: Main content ~50-60% of page */
.experience-section {
    margin-bottom: 0.15in;
}

.experience-item {
    margin-bottom: 0.15in;
}

.job-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.08in;
}

.position {
    font-size: 11pt;
    font-weight: 600;
    color: #2c3e50;
}

.company {
    font-size: 10pt;
    color: #555;
    margin-left: 0.1in;
}

.job-dates {
    font-size: 9pt;
    color: #777;
    font-style: italic;
}

.responsibilities {
    margin-left: 0.2in;
    padding-left: 0;
}

.responsibilities li {
    margin-bottom: 0.05in;
    line-height: 1.3;
    font-size: 9.5pt;
}

/* SKILLS: Compact horizontal layout */
.skills-section {
    margin-bottom: 0.15in;
}

.skills-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.08in;
}

.skill-tag {
    background-color: #ecf0f1;
    color: #2c3e50;
    padding: 0.04in 0.1in;
    border-radius: 3pt;
    font-size: 9pt;
    font-weight: 500;
}

/* EDUCATION: Compact */
.education-section {
    margin-bottom: 0.1in;
}

.education-item {
    margin-bottom: 0.08in;
    font-size: 10pt;
}

.edu-dates {
    color: #777;
    font-size: 9pt;
    font-style: italic;
}

/* ORPHAN/WIDOW CONTROL */
p, li {
    orphans: 2;
    widows: 2;
}

/* DYNAMIC SCALING FALLBACK - can be triggered if content overflows */
/* Reduce by 2-3% steps if needed, max 6% reduction */
html.scale-1 {
    font-size: 9.8pt; /* 2% reduction */
}

html.scale-2 {
    font-size: 9.6pt; /* 4% reduction */
}

html.scale-3 {
    font-size: 9.4pt; /* 6% reduction - max */
}"""

# Example Cover Letter Template
EXAMPLE_COVER_LETTER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cover Letter</title>
</head>
<body>
    <!-- HEADER: Keep with opening paragraph -->
    <div class="header-and-next">
        <div class="header">
            {% if cover_letter.title and cover_letter.title != "STRATEGIC COVER LETTER" %}
            <h1 class="recipient-name">{{ cover_letter.title }}</h1>
            {% endif %}
        </div>

        <!-- OPENING: Stay with header -->
        {% if cover_letter.openingParagraph %}
        <p class="paragraph opening">{{ cover_letter.openingParagraph }}</p>
        {% endif %}
    </div>

    <!-- BODY PARAGRAPHS: Can flow naturally -->
    {% if cover_letter.bodyParagraphs and cover_letter.bodyParagraphs|length > 0 %}
    {% for para in cover_letter.bodyParagraphs %}
    <p class="paragraph">{{ para }}</p>
    {% endfor %}
    {% endif %}

    <!-- COMPANY CONNECTION -->
    {% if cover_letter.companyConnection %}
    <p class="paragraph emphasis">{{ cover_letter.companyConnection }}</p>
    {% endif %}

    <!-- CLOSING -->
    {% if cover_letter.closingParagraph %}
    <p class="paragraph closing">{{ cover_letter.closingParagraph }}</p>
    {% endif %}

    <div class="signature">
        <p>Sincerely,</p>
        <p class="signature-line"></p>
    </div>
</body>
</html>"""

EXAMPLE_COVER_LETTER_STYLES = """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

/* PAGE SETUP */
@page {
    size: Letter;
    margin: 0.5in;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', sans-serif;
    font-size: 11pt; /* Slightly larger for readability in prose */
    line-height: 1.6; /* More generous for paragraph text */
    color: #2c3e50;
}

/* UTILITY: Keep header with opening */
.header-and-next {
    page-break-inside: avoid;
    break-inside: avoid;
}

.header {
    text-align: center;
    padding-bottom: 0.2in;
    border-bottom: 2pt solid #3498db;
    margin-bottom: 0.25in;
}

.recipient-name {
    font-size: 16pt;
    font-weight: 600;
    color: #2c3e50;
}

/* PARAGRAPHS: Allow natural flow */
.paragraph {
    margin-bottom: 0.18in;
    text-align: justify;
    orphans: 2;
    widows: 2;
}

.paragraph.opening {
    margin-top: 0;
}

.paragraph.emphasis {
    font-weight: 500;
    color: #34495e;
}

.paragraph.closing {
    margin-bottom: 0.25in;
}

/* SIGNATURE */
.signature {
    margin-top: 0.3in;
}

.signature p {
    margin-bottom: 0.15in;
}

.signature-line {
    border-top: 1pt solid #2c3e50;
    width: 2in;
    margin-top: 0.4in;
}"""

# Explanation text for agents
EXAMPLE_EXPLANATION = """
## REFERENCE EXAMPLE: Well-Proportioned Resume Theme

This example demonstrates CRITICAL principles for PDF resume layouts:

### HEIGHT PROPORTIONS (Letter size: ~11in height):
- Header (name + contact): ~15% (1.5-1.7in) - COMPACT
- Summary: ~10-12% (1.0-1.3in) - COMPACT & TIGHT
- Experience: ~50-60% (5.5-6.5in) - MAIN CONTENT
- Skills: ~8-10% (0.8-1.1in)
- Education: ~8-10% (0.8-1.1in)

### SPACING PRINCIPLES:
1. **Summary MUST be compact**: 10pt font, 1.4 line-height, minimal margins (0.15in)
2. **Section headers**: 11pt, not 14-16pt
3. **Body text**: 9.5-10pt for print
4. **Margins**: 0.05-0.15in between sections (not 0.3-0.5in)
5. **Summary does NOT get larger font than body text**

### PAGE BREAK RULES:
- Only wrap `.experience-item` in `.section-keep`
- Do NOT wrap entire summary+experience in one container
- Header stays separate from summary
- Summary can be split if absolutely necessary (though avoid)

### WHY THIS WORKS:
- Summary with 4-5 sentences fits in ~1.2in of vertical space
- Experience starts on same page around 3.5in mark
- Content flows naturally without forced page breaks
- Professional appearance without wasteful spacing

Study this example's CSS values for spacing, font-sizes, and margins.
"""

def get_resume_example_for_agent() -> dict:
    """Returns the example resume theme formatted for agent instruction."""
    return {
        "template": EXAMPLE_RESUME_TEMPLATE,
        "styles": EXAMPLE_RESUME_STYLES,
        "explanation": EXAMPLE_EXPLANATION
    }

def get_cover_letter_example_for_agent() -> dict:
    """Returns the example cover letter theme formatted for agent instruction."""
    return {
        "template": EXAMPLE_COVER_LETTER_TEMPLATE,
        "styles": EXAMPLE_COVER_LETTER_STYLES,
        "explanation": "This cover letter template demonstrates proper header grouping with opening paragraph, natural paragraph flow, and appropriate typography for long-form content."
    }
