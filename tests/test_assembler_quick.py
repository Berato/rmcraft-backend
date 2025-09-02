from app.agents.resume.strategic.schema_assembler import create_resume_from_fragments

fragments = {
    'experiences': [{'id': 'exp_1', 'company': 'TestCo', 'position': 'Dev', 'startDate': '2020-01', 'endDate': '2021-01', 'responsibilities': ['did X']}],
    'skills': {'skills': [{'id': 'skill_1', 'name': 'Python', 'level': 3}], 'additional_skills': ['Agile']},
    'projects': [{'id': 'proj_1', 'name': 'Proj', 'description': 'desc', 'url': 'http://example.com'}],
    'education': {'education': [{'id': 'edu_1', 'institution': 'Uni', 'degree': 'BS', 'startDate': '2010-01', 'endDate': '2014-01'}]},
    'contact_info': {'contact_info': [{'email': 'a@b.com', 'phone': '123'}]},
    'summary': 'Test summary',
    'design_brief': {'layout_description': 'two-column', 'color_palette': {'primary':'#000'}, 'google_fonts': ['Open Sans'], 'design_prompt_for_developer': 'test'},
    'jinja_template': {'jinja_template': '<div>{{ resume.summary }}</div>', 'css_styles': 'body{}'},
    'css_styles': ''
}

final, diagnostics = create_resume_from_fragments(fragments)
print('Final keys:', final.keys())
print('Experiences length:', len(final.get('experiences', [])))
print('Design brief present:', 'design_brief' in final and final['design_brief'])
print('Jinja template present:', bool(final.get('jinja_template')))
print('Diagnostics:', [(d.field, d.status) for d in diagnostics])
