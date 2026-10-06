# AI Interaction Log

This log documents how I used AI tools, primarily Google Gemini, ChatGPT, and Google Antigravity, during the development of the Document Intake Assistant. AI was mainly used for requirements analysis, architecture exploration, prompt design, code scaffolding, debugging, edge-case analysis, testing, and UI/document improvements. I reviewed the generated suggestions and retained control over the application architecture, state management, validation, and final implementation.

## 1. Requirements Analysis
Before implementing the application, I used AI to understand the technical-test requirements and identify the expected conversation flow, structured information, document generation requirements, and reliability expectations.

**My Prompt:**
> Analyse the technical test requirements for the Document Intake Assistant. Identify all required fields, conversation requirements, structured state requirements, document-generation requirements, validation requirements, edge cases, and engineering expectations. Do not write code yet.

**What the AI generated:**
The AI identified the required information including:
- Full name
- Home address
- Whether the document covers worldwide assets
- Whether the user has children
- Children's names when applicable
- Executor name and relationship
- Specific gifts
- Additional wishes

It also identified the requirement for a conversational interface, live structured information, a document preview, corrections, ambiguity handling, and validation of LLM output.

**My Review & Action:**
I used this analysis to define the application's core conversation flow and structured document state. I also treated the structured state as the source of truth rather than relying only on the conversation history.

## 2. Identifying Conversation Ambiguities
Because the application accepts natural-language responses, I wanted to identify situations where a short answer could be interpreted incorrectly.

**My Prompt:**
> Analyse the Document Intake Assistant conversation flow for ambiguous user responses. Consider answers such as "yes", "no", "both of them", "2", corrections, incomplete answers, and answers containing multiple pieces of information. Explain how the application should handle these cases without inventing information.

**What the AI generated:**
The AI highlighted that responses such as "no" or "yes" cannot always be interpreted correctly without knowing the current question or conversation step.
For example:
- "no" while answering the children question should update the children field.
- "no" while discussing worldwide assets should update the assets field.
- "no" while discussing the executor should not modify the children information.
- "both of them" requires the application to use previously confirmed children rather than asking for their names again.

**My Review & Action:**
I agreed with this approach and introduced explicit conversation-step/state awareness. The backend determines which field is currently being collected before interpreting short contextual responses.

## 3. Architecture Design
I wanted to separate the user interface, application logic, AI processing, state management, and document generation.

**My Prompt:**
> Design a simple architecture for a React + Vite frontend and FastAPI backend for a conversational document-intake application. The LLM should extract information from natural language, but the backend should remain the source of truth. Keep the architecture simple and testable.

**What the AI generated:**
The suggested architecture separated the application into:
- React + Vite frontend
- FastAPI REST API
- Conversation service
- LLM extraction
- State management
- State machine
- LLM response generation
- Document generation
- Memory/session storage

**My Review & Action:**
I adopted this architecture because it clearly separates responsibilities.
The final flow became:
```
User
  ↓
React Frontend
  ↓
FastAPI REST API
  ↓
Conversation Service
  ↓
LLM Extractor
  ↓
Validated Structured Update
  ↓
State Manager
  ↓
State Machine
  ↓
LLM Responder
  ↓
React Frontend
```
The important architectural decision was that the LLM proposes structured updates, while the application validates and applies those updates.

## 4. Structured State Design
One of the main risks I identified was allowing the LLM to directly control the entire document state.

**My Prompt:**
> Design a structured state model for the required Personal Wishes Document. The LLM should return partial updates rather than replacing the entire state. Include appropriate statuses for missing, confirmed, unknown, declined, and not decided information.

**What the AI generated:**
The AI suggested representing the document as structured state containing fields such as:
- `full_name`
- `home_address`
- `covers_worldwide_assets`
- `children`
- `executor`
- `specific_gifts`
- `additional_wishes`

It also suggested distinguishing between missing information and explicitly provided negative information.

**My Review & Action:**
I adopted this principle because values such as False, None, and an empty list can have completely different meanings.
For example:
`children = false` means the user explicitly said they have no children.
Whereas:
`children = null` means the application has not yet determined whether they have children.
This distinction was important for both the conversation flow and document generation.

## 5. LLM Extraction and State Updates
I wanted the LLM to understand natural-language responses while preventing it from becoming the source of truth.

**My Prompt:**
> Design an LLM extraction process where the model receives the current conversation state and user message and returns only structured updates. Do not allow the model to replace the complete application state.

**What the AI generated:**
The AI recommended a PATCH-style approach where the model returns only fields that can be extracted from the current message.
For example, a response such as:
"No, I only have one car."
could result in updates similar to:
```json
{
  "covers_worldwide_assets": false,
  "specific_assets": ["one car"]
}
```

**My Review & Action:**
I implemented the application so that the extracted information is validated and merged into the existing state rather than replacing it.
This prevented previously collected information, such as the user's name or children's names, from disappearing after a later response.

## 6. Conversation State Machine
I wanted the application to ask questions in the correct order instead of allowing the LLM to decide the entire conversation flow.

**My Prompt:**
> Design a deterministic state machine for the Document Intake Assistant. It should determine the next missing piece of information from the structured state and should not rely on the LLM to decide which question comes next.

**What the AI generated:**
The AI suggested checking the required fields sequentially and moving to the next step only after the current information is sufficiently resolved.
The flow was approximately:
`Full Name → Home Address → Worldwide Assets → Children → Children Names → Executor → Specific Gifts → Additional Wishes → Final Confirmation → Document Generation`

**My Review & Action:**
I adopted the deterministic state-machine approach.
The LLM is responsible for understanding the user's language, while the backend determines what information is still required.
This made the conversation more predictable and easier to test.

## 7. Handling Multiple Fields in One Response
During testing, I found that users may provide multiple pieces of information in one message.

**My Prompt:**
> The user may answer multiple questions in one message. Explain how the application should extract and preserve all relevant information instead of processing only one field.

**What the AI generated:**
The AI recommended extracting multiple independent updates from a single response.
For example:
"My name is Harshad and I live in Pune."
should update both:
`Full Name → Harshad`
`Home Address → Pune`

Similarly:
"I have two children, John and Mia."
should update the children state with the count and names.

**My Review & Action:**
I updated the extraction and state-management flow to support multiple updates from one user message while still validating each update before applying it.

## 8. Debugging the Children and Executor Flow
One of the major issues discovered during testing involved children and executor information.
For example, after entering two children and later answering "no" to an executor-related question, the application could incorrectly modify the children state.

**My Prompt:**
> Debug this conversation flow. The user has already provided two children, but a later "no" related to the executor is changing or re-opening the children state. Identify the root cause and propose a fix without changing unrelated functionality.

**What the AI generated:**
The AI identified that the application was not consistently using the current conversation step when interpreting short answers.

**My Review & Action:**
I changed the logic so that short contextual responses are interpreted according to the current state-machine step.
I also ensured that the children information remains persistent after confirmation.

## 9. Handling "Both of Them"
Another important conversational edge case occurred when the user selected both previously provided children as executors.
For example:
"I have two children, John and Mia."
followed by:
"Both of them."

**My Prompt:**
> If the user previously confirmed two children and, when asked about the executor, says "both of them", determine how this should be interpreted. Do not ask the user for names again if the required information already exists in the structured state.

**What the AI generated:**
The AI interpreted "both of them" as referring to the previously confirmed children.

**My Review & Action:**
I updated the application so that:
Children: `John`, `Mia`
followed by:
Executor: `John`, `Mia`
Relationship: `Children`
does not require the user to enter the names again.
This also reinforced the principle that conversational references should resolve against the existing structured state.

## 10. Handling Corrections
The application must allow users to correct information they previously provided.

**My Prompt:**
> Design the correction behaviour for the Document Intake Assistant. If the user says something such as "Actually my address is Mumbai, not Pune", update the existing value without affecting unrelated fields.

**What the AI generated:**
The AI recommended treating explicit corrections as updates to the relevant field rather than creating duplicate information.

**My Review & Action:**
I implemented corrections as state updates.
For example:
Previous: `Address = Pune`
User: "Actually, my address is Mumbai."
Updated: `Address = Mumbai`
Other confirmed fields remain unchanged.

## 11. Handling Ambiguous or Unusual Information
I wanted to make sure the application does not silently invent or alter information when users provide unusual claims.

**My Prompt:**
> How should the application handle unusual or potentially implausible user claims without inventing facts or silently modifying the user's input?

**What the AI generated:**
The AI recommended distinguishing between:
- Valid input format
- Potentially unusual information
- Missing information
- Ambiguous information

Rather than silently changing unusual claims, the application should ask the user to confirm when appropriate.

**My Review & Action:**
I followed this approach. The application does not automatically replace unusual user-provided information with a guessed value.
The LLM is used for interpretation, not factual invention.

## 12. Document Generation
After the structured state was complete, I needed to generate the Personal Wishes Document from the collected information.

**My Prompt:**
> Design a document-generation flow where the final Personal Wishes Document is generated only from the validated structured state. Ensure that information is not invented during document generation.

**What the AI generated:**
The AI recommended keeping document generation separate from conversational logic and generating the document directly from the structured state.

**My Review & Action:**
I kept document generation separate from the chatbot logic.
The document preview is based on the structured application state rather than the raw conversation history.
I also included the required fictional-document and non-legal-advice context.

## 13. PDF Rendering Issues
During testing, I discovered visual problems in the generated PDF, including overlapping characters and incorrect text rendering.

**My Prompt:**
> Inspect the PDF rendering implementation for character overlap, incorrect spacing, line-height problems, table layout issues, and page-break problems. Fix the visual rendering without changing the chatbot or state-management logic.

**What the AI generated:**
The AI identified that the problem was related to the document/PDF rendering layer rather than the conversation logic.
It recommended checking:
- Font rendering
- Letter spacing
- Line height
- Padding
- Table widths
- Page breaks
- Text wrapping
- PDF generation configuration

**My Review & Action:**
I kept the fix isolated to the document-rendering layer.
I did not modify the chatbot/state-management logic to solve a PDF rendering problem.
I also visually reviewed the generated PDF after the changes.

## 14. PDF Content and State Validation
I also tested whether information entered during the conversation actually appeared in the final document.

**My Prompt:**
> Review the complete flow from user input → structured state → document generation. Identify any fields that could be correctly acknowledged by the chatbot but accidentally omitted from the final document.

**What the AI generated:**
The AI suggested checking each required field independently between the structured state and document renderer.

**My Review & Action:**
I verified that fields such as additional wishes are stored in the structured state and passed to the document generator.
For example, when the user provided:
"I want to play golf."
the value was stored as an additional wish and subsequently rendered in the document.

## 15. Handling Children Yes/No in the PDF
During testing, I found that the children Yes/No checkboxes could incorrectly appear unchecked even though the conversation state correctly contained false.

**My Prompt:**
> Fix the document checkbox rendering. The children field has three possible states: unknown, yes, or no. Map the structured state correctly to the PDF checkboxes.

**What the AI generated:**
The AI recommended explicit three-state handling:
- `null` → neither checked
- `true` → Yes checked
- `false` → No checked

**My Review & Action:**
I applied explicit boolean-state mapping rather than relying on truthy/falsy checks.
This prevents `false` from being treated as missing information.

## 16. API and Frontend Integration
I used AI to review the communication between the React frontend and FastAPI backend.

**My Prompt:**
> Review the React frontend and FastAPI backend integration for the Document Intake Assistant. Identify potential issues with API contracts, state synchronization, errors, loading states, and direct user edits.

**What the AI generated:**
The AI highlighted the importance of keeping the API contract consistent and ensuring that frontend updates are synchronized with backend structured state.

**My Review & Action:**
I kept the frontend responsible for presentation and user interaction, while the backend remains responsible for conversation processing and state management.
The frontend communicates with the backend using JSON over HTTP.

## 17. AI Code Review
After implementing the main functionality, I used AI as a code reviewer rather than asking it to rewrite the project.

**My Prompt:**
> Act as a senior software engineer and review this Document Intake Assistant implementation. Focus on separation of concerns, state management, LLM reliability, validation, error handling, testability, and maintainability. Do not rewrite the project immediately. Identify concrete problems first.

**What the AI generated:**
The review highlighted areas including:
- LLM output validation
- Separation of AI logic from application state
- Handling malformed model responses
- Session/state persistence
- Conversation-step management
- Document generation separation
- Testing edge cases

**My Review & Action:**
I selectively adopted the recommendations that improved reliability without unnecessarily increasing the complexity of the project.
I avoided adding unnecessary frameworks or architecture patterns that were not required for the technical test.

## 18. Final End-to-End Testing
Before finalizing the project, I used AI to identify scenarios that should be tested from the beginning of the conversation to final document generation.

**My Prompt:**
> Perform a final end-to-end review of the Document Intake Assistant. Create a test checklist covering normal conversations, multiple fields in one response, corrections, ambiguous answers, children/executor relationships, missing information, malformed LLM responses, document generation, and final confirmation.

**What the AI generated:**
The AI produced scenarios covering:
- Normal sequential conversation
- Multiple fields in one message
- No children
- Multiple children
- Children as executors
- Executor not decided
- Corrections
- Ambiguous responses
- Missing information
- Explicit "no" answers
- Malformed LLM output
- PDF generation
- Final confirmation

**My Review & Action:**
I manually tested the important scenarios and used the results to fix issues discovered during development.
The final implementation keeps the structured application state as the source of truth, uses the LLM primarily for language understanding and response generation, and keeps the deterministic conversation flow and document generation under application control.

## 19. Final Architecture Decision
One of the most important decisions from the AI-assisted development process was to avoid treating the LLM as the application's database or state machine.
The final approach is:
```
User Message
      ↓
LLM Extraction
      ↓
Structured JSON Update
      ↓
Validation
      ↓
State Manager
      ↓
Structured Application State
      ↓
State Machine
      ↓
Next Required Information
      ↓
LLM Response Generation
      ↓
User
```
This approach allowed me to use AI for natural-language understanding while keeping the important application rules deterministic, testable, and under my control.

## 20. Final Reflection
AI significantly accelerated the development process, particularly for architecture exploration, boilerplate, debugging, edge-case discovery, prompt design, and code review. However, I did not treat generated code or suggestions as automatically correct.
Throughout development, I reviewed AI-generated solutions against the assignment requirements, manually tested important scenarios, rejected unnecessary complexity, and modified the implementation when AI suggestions did not match the desired behaviour.
The most important lesson from the process was that LLM output should be treated as an untrusted proposal, while the application's validated structured state should remain the source of truth.
