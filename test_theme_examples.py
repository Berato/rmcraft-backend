"""
Quick test to verify theme examples are properly formatted and can be used in agent instructions.
"""

from app.agents.theme_examples import get_resume_example_for_agent, get_cover_letter_example_for_agent

def test_resume_example():
    """Verify resume example has all required components."""
    example = get_resume_example_for_agent()
    
    assert 'template' in example, "Resume example missing 'template' key"
    assert 'styles' in example, "Resume example missing 'styles' key"
    assert 'explanation' in example, "Resume example missing 'explanation' key"
    
    # Check template has key sections
    template = example['template']
    assert '{{ resume.personalInfo.firstName }}' in template, "Template missing name field"
    assert '{{ resume.summary }}' in template, "Template missing summary field"
    assert 'resume.experience' in template, "Template missing experience iteration"
    assert 'class="summary-section"' in template, "Template missing summary section"
    assert 'section-keep' in template, "Template missing page-break control"
    
    # Check styles have critical spacing rules
    styles = example['styles']
    assert 'font-size: 10pt' in styles or 'font-size: 9.5pt' in styles, "Styles missing compact font size"
    assert '.summary-text' in styles, "Styles missing summary-specific styling"
    assert 'margin-bottom: 0.15in' in styles or 'margin-bottom: 0.1in' in styles, "Styles missing compact margins"
    assert '@page' in styles, "Styles missing page setup"
    assert 'page-break-inside: avoid' in styles, "Styles missing page break control"
    
    # Check explanation has key guidance
    explanation = example['explanation']
    assert 'COMPACT' in explanation, "Explanation missing compact emphasis"
    assert 'Summary' in explanation, "Explanation missing summary guidance"
    assert '10-12%' in explanation, "Explanation missing percentage guidance"
    
    print("✅ Resume example is properly formatted")
    print(f"   - Template length: {len(template)} chars")
    print(f"   - Styles length: {len(styles)} chars")
    print(f"   - Explanation length: {len(explanation)} chars")
    return True

def test_cover_letter_example():
    """Verify cover letter example has all required components."""
    example = get_cover_letter_example_for_agent()
    
    assert 'template' in example, "Cover letter example missing 'template' key"
    assert 'styles' in example, "Cover letter example missing 'styles' key"
    assert 'explanation' in example, "Cover letter example missing 'explanation' key"
    
    # Check template has key sections
    template = example['template']
    assert 'cover_letter.openingParagraph' in template, "Template missing opening paragraph"
    assert 'cover_letter.bodyParagraphs' in template, "Template missing body paragraphs"
    assert 'class="header-and-next"' in template, "Template missing header grouping"
    
    # Check styles
    styles = example['styles']
    assert 'font-size: 11pt' in styles, "Styles missing appropriate font size for prose"
    assert 'line-height: 1.6' in styles, "Styles missing readable line height"
    assert '@page' in styles, "Styles missing page setup"
    
    explanation = example['explanation']
    print("✅ Cover letter example is properly formatted")
    print(f"   - Template length: {len(template)} chars")
    print(f"   - Styles length: {len(styles)} chars")
    print(f"   - Explanation length: {len(explanation)} chars")
    return True

def test_examples_can_be_injected():
    """Verify examples can be formatted into agent instructions."""
    resume_ex = get_resume_example_for_agent()
    
    # Simulate how it would be injected into instructions
    instruction_fragment = (
        f"\n\n## REFERENCE EXAMPLE ##"
        f"\n{resume_ex['explanation']}"
        f"\n\n### Template:\n```html\n{resume_ex['template']}\n```"
        f"\n\n### CSS:\n```css\n{resume_ex['styles']}\n```"
    )
    
    assert len(instruction_fragment) > 1000, "Instruction fragment seems too short"
    assert '```html' in instruction_fragment, "Template not properly code-fenced"
    assert '```css' in instruction_fragment, "Styles not properly code-fenced"
    
    print("✅ Examples can be properly injected into agent instructions")
    print(f"   - Total instruction fragment length: {len(instruction_fragment)} chars")
    return True

if __name__ == "__main__":
    print("Testing theme examples...\n")
    
    try:
        test_resume_example()
        print()
        test_cover_letter_example()
        print()
        test_examples_can_be_injected()
        print("\n🎉 All tests passed! Theme examples are ready to use.")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
