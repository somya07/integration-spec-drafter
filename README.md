# Integration Spec Drafter

An agent that turns a plain-English integration requirement into a technical spec and a stakeholder-facing summary — automating the first-draft translation work I used to do manually at Moba BV (TIBCO Scribe / Infor integrations).

## Problem

Integration work usually starts the same way: a business stakeholder describes a need in plain language ("when an order is created, update stock and notify the warehouse team"), and an engineer has to turn that into a scoped technical spec — trigger conditions, field mappings, error handling — plus a plain-English version stakeholders can actually sign off on.

## What this agent does

1. Takes a plain-English integration requirement
2. Reads reference field lists for the two systems involved
3. **Plans** the integration (trigger, mapping, error handling, logging) using the agent's built-in planning tool
4. Writes two output files:
   - `integration_spec.md` — technical spec for engineers
   - `stakeholder_summary.md` — plain-English version for business stakeholders

## Stack

- [Deep Agents](https://github.com/langchain-ai/deepagents)
- Claude (Anthropic API)
- Python 3.11+

## Status

🚧 In progress

## Example

Input:
> "When a new order is created in the Orders system, update stock in the Warehouse system and notify the fulfillment team by email."

Output: see [`examples/`](./examples) once available.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
python agent.py
```

## What I'd extend next

- Auto-generate the field-mapping table directly from two system schemas
- Add a subagent that checks for similar existing integrations before drafting a new one
