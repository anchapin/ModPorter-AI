# GitHub Issues & Project Board Plan

## Project Board Structure

### Milestones
1. **Milestone 1: MVP Block Conversion Demo** (Target: 2-3 weeks)
2. **Milestone 2: Add Item Conversion** (Target: 1-2 weeks after M1)
3. **Milestone 3: Add Basic Entity Conversion** (Target: 2-3 weeks after M2)

### Labels
- `priority-1` - Critical path items
- `priority-2` - Important but not blocking
- `priority-3` - Nice to have
- `good-first-issue` - Small, well-defined tasks
- `can-be-parallelized` - Can be worked on simultaneously
- `blocked` - Waiting on dependencies
- `epic` - Large stories broken into smaller issues
- `documentation` - Documentation updates
- `testing` - Test-related work
- `agent-improvement` - AI agent enhancements
- `bug` - Bug fixes
- `enhancement` - New features

### Kanban Columns
- **Backlog** - Planned but not started
- **Ready** - Defined and ready to start
- **In Progress** - Currently being worked on
- **Review** - Ready for review/testing
- **Done** - Completed

## Issue List for Milestone 1: MVP Block Conversion Demo

### Priority 1 Issues (Critical Path)

#### Issue #1: Documentation - Update PRD.md with Clear MVP Definition
**Labels**: `priority-1`, `documentation`, `epic`
**Milestone**: Milestone 1

**Description**: 
Update the Product Requirements Document to clearly define the MVP and success criteria for the first working demo.

**Tasks**:
- [ ] Define MVP scope: Simple Java block → Bedrock JSON conversion
- [ ] Document expected input format (simple Java block class)
- [ ] Document expected output format (Bedrock behavior pack files)
- [ ] Add success criteria and acceptance tests
- [ ] Update smart assumptions table with block-specific examples
- [ ] Remove or defer complex features to later milestones

**Acceptance Criteria**:
- PRD clearly states what the MVP will and won't do
- Success criteria are measurable and testable
- Examples of input/output are provided

---

#### Issue #2: Testing - Create End-to-End MVP Test Case
**Labels**: `priority-1`, `testing`, `good-first-issue`
**Milestone**: Milestone 1

**Description**:
Create a simple test case that validates the complete pipeline from Java block to Bedrock files.

**Tasks**:
- [ ] Create simple Java block example (e.g., custom stone block)
- [ ] Define expected Bedrock output files
- [ ] Write test that runs the complete agent pipeline
- [ ] Add assertions for file generation and content validation
- [ ] Document how to run the test

**Acceptance Criteria**:
- Test can be run with `pytest tests/test_mvp_conversion.py`
- Test fails initially (before implementation fixes)
- Test provides clear feedback on what's working/failing

---

#### Issue #3: Agent Enhancement - Improve Java Analyzer for Simple Blocks
**Labels**: `priority-1`, `agent-improvement`, `can-be-parallelized`
**Milestone**: Milestone 1

**Description**:
Enhance the Java Analyzer agent to reliably extract information from simple Java block classes.

**Tasks**:
- [ ] Add robust parsing for basic block properties (material, hardness, etc.)
- [ ] Handle common Java block patterns (extends Block, etc.)
- [ ] Add error handling for malformed Java files
- [ ] Add logging for analysis steps
- [ ] Create unit tests for the analyzer

**Acceptance Criteria**:
- Can extract block name, material, and basic properties
- Handles errors gracefully with clear error messages
- Logs analysis steps for debugging

---

#### Issue #4: Agent Enhancement - Improve Code Translator for Block Generation
**Labels**: `priority-1`, `agent-improvement`, `can-be-parallelized`
**Milestone**: Milestone 1

**Description**:
Enhance the Logic Translator agent to generate valid Bedrock block JSON files from Java block analysis.

**Tasks**:
- [ ] Create templates for basic Bedrock block JSON
- [ ] Map common Java block properties to Bedrock equivalents
- [ ] Use RAG tool to query Bedrock documentation
- [ ] Add validation for generated JSON
- [ ] Add logging for translation decisions

**Acceptance Criteria**:
- Generates valid Bedrock block JSON files
- Uses RAG tool to ensure accuracy
- Validates output against Bedrock schemas

---

#### Issue #5: Integration - Connect Agents for MVP Pipeline
**Labels**: `priority-1`, `epic`
**Milestone**: Milestone 1

**Description**:
Ensure the conversion crew properly orchestrates the Java Analyzer → Logic Translator pipeline for blocks.

**Tasks**:
- [ ] Update conversion_crew.py for block-focused workflow
- [ ] Add proper data passing between agents
- [ ] Add pipeline error handling
- [ ] Add progress tracking and logging
- [ ] Test with the MVP test case

**Acceptance Criteria**:
- Java block input produces Bedrock block output
- Pipeline handles errors gracefully
- Each step is logged for debugging
- MVP test case passes

---

### Priority 2 Issues (Important but not blocking)

#### Issue #6: Documentation - Create GitHub Project Board
**Labels**: `priority-2`, `documentation`, `good-first-issue`
**Milestone**: Milestone 1

**Description**:
Set up a GitHub Project board with proper columns, labels, and automation.

**Tasks**:
- [ ] Create new GitHub Project (v2)
- [ ] Set up Kanban columns (Backlog, Ready, In Progress, Review, Done)
- [ ] Add all issues to the project
- [ ] Configure automation rules (move to In Progress when assigned, etc.)
- [ ] Add milestone tracking

---

#### Issue #7: Logging - Add Comprehensive Agent Logging
**Labels**: `priority-2`, `agent-improvement`, `can-be-parallelized`
**Milestone**: Milestone 1

**Description**:
Add detailed logging throughout the agent system for debugging and monitoring.

**Tasks**:
- [ ] Add structured logging to all agents
- [ ] Log agent decisions and reasoning
- [ ] Log tool usage and results
- [ ] Add debug mode for verbose output
- [ ] Create log analysis tools

---

#### Issue #8: Testing - Add Unit Tests for Individual Agents
**Labels**: `priority-2`, `testing`, `can-be-parallelized`
**Milestone**: Milestone 1

**Description**:
Create comprehensive unit tests for each agent in isolation.

**Tasks**:
- [ ] Test JavaAnalyzer with various Java block types
- [ ] Test LogicTranslator with different conversion scenarios
- [ ] Test RAG tool responses
- [ ] Mock external dependencies (LLM APIs)
- [ ] Add test coverage reporting

---

### Priority 3 Issues (Nice to have)

#### Issue #9: Enhancement - Add Performance Monitoring
**Labels**: `priority-3`, `enhancement`
**Milestone**: Milestone 1

**Description**:
Add timing and performance metrics to track agent performance.

**Tasks**:
- [ ] Add timing decorators to agent methods
- [ ] Track LLM API usage and costs
- [ ] Create performance dashboard
- [ ] Add memory usage monitoring
- [ ] Set up alerts for slow operations

---

#### Issue #10: Documentation - Create Troubleshooting Guide
**Labels**: `priority-3`, `documentation`
**Milestone**: Milestone 1

**Description**:
Create a guide for common issues and debugging steps.

**Tasks**:
- [ ] Document common conversion failures
- [ ] Add debugging steps for each agent
- [ ] Create FAQ for users
- [ ] Add examples of successful conversions
- [ ] Document known limitations

---

## Commands to Set Up

1. Create labels in GitHub
2. Create milestones in GitHub  
3. Create issues using the GitHub CLI or web interface
4. Set up Project board
5. Link issues to milestones and add labels
