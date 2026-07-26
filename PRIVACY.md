# U Money Privacy

## What is stored

- When signed out, ordinary records are stored in the current browser only.
- When signed in, records are stored in the Supabase project for the current account.
- The app does not ask users to send passwords, API keys, access tokens, or CSV exports to the project owner.

## Optional AI features

- Natural-language accounting sends the sentence entered by the user to the AI service and its configured model provider so it can return a draft. The user must review and confirm the draft before it is saved.
- Monthly summaries send only monthly aggregate data, such as totals and category totals. They do not send the complete list of records or notes.
- Users can turn off AI in the page. When it is off, the app does not call the AI service and ordinary manual accounting still works.
- AI output is informational and may be wrong. It is not investment, loan, insurance, medical, or other professional advice.

## Logs and feedback

- The AI service records request identifiers, a keyed user pseudonym, duration, prompt version, status, and candidate count. It does not intentionally log complete accounting sentences, notes, amounts, email addresses, or access tokens.
- Beta feedback must not contain passwords, real income, real bills, API information, access tokens, or CSV contents.

## Important limits

- Supabase, the deployment platform, and the chosen model provider each have their own privacy and retention settings. Review them before inviting real users.
- Clearing browser data may remove signed-out local records.
