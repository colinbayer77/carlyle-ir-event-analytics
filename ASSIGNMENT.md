# AI / BI Analytics Take-Home Assessment

## Business Context

An Investor Relations organization participates in investor conferences and relationship events throughout the year. These events require financial investment and significant time from relationship and investment teams.

Leadership would like a consistent analytical view of what happens following these events, the business outcomes associated with them, and what can be learned when planning future events.

The supplied data is synthetic/mock data created solely for this assessment.

## Your Assignment

Using the provided data, design and build an analytical solution that helps leadership answer:

**What happened following our investor events, what business outcomes are associated with them, and what should we learn for future events?**

The problem is intentionally open-ended. We have not prescribed the KPIs, attribution methodology, data model, or visualization approach.

We would like you to determine:

- What metrics and KPIs are most meaningful
- How you would measure or associate event-related outcomes
- How the underlying data should be modeled
- How leadership should explore the information
- What insights and actions can be derived from the data

Please distinguish association from causation where appropriate.

## Expected Deliverables

### 1. Interactive analytics experience

Build an interactive analytical experience using the format and technology you believe best solves the problem. Examples include an HTML/web experience, Streamlit application, Tableau/BI solution, or another appropriate format.

**We are not evaluating proficiency in any specific BI tool.** Choose the format that best communicates the analysis and makes the underlying data explorable.

At minimum, a user should be able to understand overall event performance and investigate underlying firms and business outcomes.

### 2. Analysis and data model

Include the SQL, Python, notebooks, transformations, calculations, or other code used to create the analysis. Document important assumptions, metric definitions, and material data-quality decisions.

### 3. Executive readout

Provide a short executive summary - maximum 3 slides or 1 page.

Assume you have five minutes with the Head of Investor Relations: **What are the most important things you would tell them based on your analysis?**

### 4. AI usage

Use of AI tools is encouraged. Briefly describe:

- Where AI helped you
- How it accelerated your work
- How you validated the output
- At least one example where you changed, corrected, or challenged AI-generated work

## Submission

Please submit a GitHub repository containing your solution and supporting materials. Include clear instructions for running or reviewing the solution.

If an artifact cannot be rendered directly in GitHub, include the relevant project file plus screenshots or a short recording demonstrating the experience.

## Time Expectation

Please spend no more than approximately **two working days** on the assessment. We are not looking for a production-ready application. We are primarily evaluating analytical thinking, hands-on technical execution, product judgment, AI usage, and ability to communicate insights.

## Provided Data

- `data/events.csv` - events, dates, types, locations, and costs
- `data/firms.csv` - investor firms, segments, priority, and historical relationship information
- `data/event_attendees.csv` - event attendance by firm/contact
- `data/meetings.csv` - investor interactions before and after events
- `data/opportunity_stage_history.csv` - fundraising opportunities and stage changes over time

The data intentionally contains realistic imperfections and ambiguous cases. Make reasonable assumptions and document them.
