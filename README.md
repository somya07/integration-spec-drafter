# Integration Spec Drafter

An agent that turns a plain-English integration requirement into a technical spec and a stakeholder-facing summary — automating the first-draft translation work I used to do manually at Moba BV (TIBCO Scribe / Infor integrations).

## Problem

Integration work usually starts the same way: a business stakeholder describes a need in plain language ("when an order comes in from our ecommerce platform, add it to the ERP"), and an engineer has to turn that into a scoped technical spec — trigger conditions, field mappings, error handling — plus a plain-English version stakeholders can actually sign off on.

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

✅ Working end to end

## Example

Input:
> "Orders come from our Ecommerce Platform and need to be added to our ERP via webhook. Each order includes an order number, date requested, shipping address, billing address, and the ordered product SKUs with quantities."

Reference fields: [`sample_data/ecommerce_platform_fields.txt`](./sample_data/ecommerce_platform_fields.txt), [`sample_data/erp_fields.txt`](./sample_data/erp_fields.txt)

Output: [`examples/integration_spec.md`](./examples/integration_spec.md), [`examples/stakeholder_summary.md`](./examples/stakeholder_summary.md)

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env             # then add your real ANTHROPIC_API_KEY
python agent.py
```

## What I'd extend next

- Auto-generate the field-mapping table directly from two system schemas
- Add a subagent that checks for similar existing integrations before drafting a new one
