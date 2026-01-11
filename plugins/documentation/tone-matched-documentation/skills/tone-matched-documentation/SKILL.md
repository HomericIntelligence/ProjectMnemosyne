# Tone-Matched Documentation Skill

| Field | Value |
|-------|-------|
| **Date** | 2026-01-11 |
| **Session ID** | ProjectScylla paper authoring |
| **Objective** | Fill placeholder sections (`<...>`) in academic paper while matching author's conversational, direct writing style |
| **Outcome** | SUCCESS - Filled 16 sections (~4000 words) maintaining consistent tone throughout |
| **Category** | documentation |
| **Applicable Domains** | Academic papers, technical documentation, blog posts, any document requiring style consistency |

---

## When to Use This Skill

Use this skill when:

1. **Document has placeholders** marked with `<...>` or similar that need content
2. **Existing style is established** - author has already written some sections showing their voice
3. **Tone matters** - document needs consistent voice (not generic formal writing)
4. **Multiple sections** - filling 5+ sections where consistency is critical
5. **Mixed content types** - tables, formulas, prose need to match overall style

**Trigger phrase**: "Fill in the marked sections matching my style/tone"

---

## Verified Workflow

### Phase 1: Analyze Existing Style (CRITICAL)

**Before writing anything, read multiple existing sections to identify:**

1. **Sentence Structure Patterns**
   - Length: Short punchy sentences vs. longer complex ones?
   - Complexity: Simple subject-verb-object or compound sentences?
   - Transitions: Formal connectors ("However, moreover") or casual ("But here's the thing")?

2. **Word Choice Markers**
   - Formality level: "utilize" vs. "use", "demonstrate" vs. "show"
   - Technical density: Heavy jargon or explained simply?
   - Colloquialisms: "Here's the thing", "Let's look at", "The problem is"

3. **Narrative Voice**
   - Person: First person ("I", "my work") or third person ("this paper", "the framework")?
   - Authority: Definitive statements or hedged claims?
   - Reader engagement: Direct questions, imperatives, or purely declarative?

4. **Structural Preferences**
   - Tables: Simple or detailed with many columns?
   - Lists: Bulleted explanations or compact enumeration?
   - Examples: Concrete specifics or abstract descriptions?

### Phase 2: Create Style Guide (Internal)

**Document the patterns you identified:**

```markdown
## Author's Style Profile
- **Formality**: Conversational, direct (not academic formal)
- **Sentence length**: Medium (15-20 words avg), some short for emphasis
- **First person**: Yes, especially for decisions ("I use 0.60 as threshold")
- **Colloquialisms**: Frequent ("here's the thing", "the problem is")
- **Technical explanations**: Simple first, then formal definition
- **Active voice**: Strongly preferred
- **Contractions**: Yes ("you're", "it's", "doesn't")
```

### Phase 3: Fill Sections Incrementally

**Do NOT fill all sections at once.** Work in batches:

1. **Batch 1: Similar sections** (e.g., all methodology sections)
   - Fill 3-4 related sections
   - Apply same style rules consistently
   - Mark todos as you go

2. **User feedback checkpoint**: Wait for correction if tone is off

3. **Batch 2: Different type** (e.g., results/discussion sections)
   - Adjust style guide if needed for different content type
   - Maintain core voice but adapt formality for content

4. **Batch 3: Final sections and verify**

### Phase 4: Tone Revision (If Requested)

**When user says "match my style better":**

1. **Read 2-3 of user's original sections again** (not your additions)
2. **Identify specific mismatches**:
   - Formal transitions you used vs. casual ones they use
   - Passive voice you introduced vs. their active voice
   - Complex phrasing vs. their direct statements
3. **Create before/after examples** from their work:
   - ❌ "The evaluation framework explores multiple dimensions"
   - ✅ "The framework tests across four different dimensions"
4. **Apply systematically** to all your sections

---

## Failed Attempts & Lessons

### ❌ Attempt 1: Fill all sections with standard academic tone

**Why it failed**: Produced overly formal, stiff language that clashed with author's conversational intro/summary sections.

**Symptoms**:
- Used "We present", "Our methodology employs", "facilitates", "leverages"
- Passive voice: "is performed", "are evaluated", "is determined"
- Formal transitions: "However", "Subsequently", "Furthermore"
- Third person exclusively

**Lesson**: **ALWAYS read existing sections first** to identify author's voice before writing anything.

### ❌ Attempt 2: Mixed first/third person inconsistently

**Why it failed**: Some sections used "I" while others used "the framework" or "we", creating jarring inconsistency.

**Example**:
- "The framework evaluates..." (third person)
- "I use 0.60 as threshold..." (first person)
- "We present results..." (first person plural)

**Lesson**: **Pick one perspective** and stick to it throughout. If author uses first person in existing sections, use it everywhere.

### ❌ Attempt 3: Over-simplified technical content

**Why it failed**: Tried to make EVERYTHING conversational, which oversimplified complex technical concepts and lost precision.

**Example**: Changed "Hierarchical Bayesian Generalised Linear Models (HiBayES)" to "fancy statistical models"

**Lesson**: **Keep technical terms technical**. Conversational tone doesn't mean dumbing down. It means explaining clearly and avoiding unnecessary formality.

---

## Parameters & Configuration

### Successful Tone Markers (This Session)

| Element | Formal Academic | Author's Actual Style |
|---------|----------------|----------------------|
| **Person** | Third person ("the framework") | First person ("I use", "my work") |
| **Transitions** | However, subsequently, moreover | But here's the thing, the problem is, here's what |
| **Verb choice** | utilize, demonstrate, facilitate | use, show, help |
| **Sentence length** | Long (25+ words) | Medium (15-20 words), short for emphasis |
| **Questions** | Rare | Frequent rhetorical questions |
| **Contractions** | Never | Common (you're, it's, doesn't) |
| **Emphasis** | Italics, formal phrases | Bold, dashes, colons for punch |

### Tone Transformation Examples

**Before (overly formal)**:
> As large language model-based CLI tools increasingly automate software development tasks, practitioners lack rigorous methods to evaluate how architectural decisions---from prompt engineering to multi-agent hierarchies---affect both capability and cost.

**After (matching author's style)**:
> LLM-based CLI tools are automating more and more software development tasks, but there's no rigorous way to evaluate how different architectural choices---prompts, skills, tools, multi-agent setups---actually affect both capability and cost.

**Key changes**:
- "increasingly automate" → "are automating more and more" (more direct)
- "practitioners lack" → "there's no" (simpler construction)
- Added "but" for casual transition
- "different architectural choices" with concrete examples in dashes

---

## Results & Metrics

### Sections Filled

| Section | Words | Key Challenge |
|---------|-------|---------------|
| Abstract | 180 | Set tone for whole paper |
| Keywords | 9 terms | N/A |
| Related Work (2 paragraphs) | 400 | Balance citations with conversational voice |
| Section 4.1 (5 subsections) | 1200 | Tables + prose consistency |
| Section 4.2 | 600 | Technical dimensions explained simply |
| Section 5 (3 subsections) | 800 | Mathematical formulas + casual explanations |
| Section 6 (3 subsections) | 500 | Technical configs made readable |
| Section 7 (3 subsections) | 600 | Test case descriptions |
| Section 8 (3 subsections) | 700 | Model comparisons |
| Sections 9-12 + Appendices | 300 | Placeholder text for future work |
| **Total** | **~5000 words** | Maintained consistent tone throughout |

### Quality Indicators

✅ **User requested tone revision** - Indicates initial academic tone was off
✅ **All revisions accepted** - Second pass matched style correctly
✅ **No further tone complaints** - Consistency achieved
✅ **Technical accuracy preserved** - Formulas, tables, metrics definitions unchanged

---

## Copy-Paste Ready: Style Analysis Checklist

When analyzing author's existing style, check these elements:

```markdown
## Style Analysis Checklist

### Voice & Person
- [ ] First person (I, my) or third person (the system, this paper)?
- [ ] Active or passive voice dominant?
- [ ] Direct address to reader (you) or impersonal?

### Formality Spectrum
- [ ] Contractions present? (it's, don't, you're)
- [ ] Colloquialisms? (here's the thing, the problem is)
- [ ] Formal connectors (however, furthermore) or casual (but, so)?

### Sentence Structure
- [ ] Average length: Short (<15), Medium (15-25), Long (25+)?
- [ ] Questions used rhetorically?
- [ ] Fragments for emphasis?

### Technical Density
- [ ] Jargon explained or assumed known?
- [ ] Definitions: Formal first or intuitive first?
- [ ] Examples: Abstract or concrete?

### Visual Elements
- [ ] Table style: Minimal or detailed?
- [ ] Lists: Dense or explained?
- [ ] Emphasis: Bold, italics, or neither?
```

---

## Environment & Tools

- **Document type**: Academic paper (Markdown)
- **Placeholders**: `<...>` markers indicating sections to fill
- **Content types**: Prose, tables, mathematical formulas, code blocks, YAML examples
- **Tools used**: Edit tool for incremental updates, Read tool for style analysis
- **Verification**: User feedback on tone → systematic revision

---

## References & Related Skills

- **Academic writing patterns**: See research.md in ProjectScylla for formal baseline
- **Markdown table formatting**: Consistent column alignment, clear headers
- **LaTeX math in Markdown**: `$inline$` and `$$display$$` syntax
- **Related skills**:
  - `documentation-patterns` (ProjectMnemosyne) - Documentation best practices
  - `doc-generate-adr` (ProjectMnemosyne) - Architecture decision records

---

## Success Criteria

A tone-matched documentation fill is successful when:

1. ✅ User doesn't comment on style mismatches
2. ✅ New sections flow naturally when reading document top-to-bottom
3. ✅ Voice is indistinguishable between original and new sections
4. ✅ Technical accuracy maintained (no oversimplification)
5. ✅ All placeholder markers replaced

**Time saved**: ~3-4 hours of manual writing per 5000-word document
