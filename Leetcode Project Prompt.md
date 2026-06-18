## Project Details: LeetCode Local IDE Integration



### 🎯 Core Functionality Requirements

Input 
The tool must accept a **LeetCode question number** (e.g., `1`, `42`, `238`) as the primary input argument. It should resolve this number to the corresponding question slug (e.g., `two-sum`, `truncate-sentence`) using the LeetCode problem list mapping.

Data Retrieval
Upon resolving the slug, the system must query the **LeetCode GraphQL API** (`https://leetcode.com/graphql`) to fetch:
*   **Question Content:** Title, description, examples, and constraints, images (returned as HTML, needs parsing to Markdown).
*   **Code Stub:** The boilerplate code specific to the user's configured language (Python, Java, C++, etc.).
*   **Test Cases:** 
    *   *Sample Cases:* Public examples provided in the description.
    *   *Hidden Cases:* Note that full hidden test cases are **not** accessible via public API for security reasons. The tool should only pull sample cases for local validation.

### 🏗️ Architecture Options

You must implement one of the following two workflows for code validation:

#### Option A: Local Validation (Pull Test Cases)
This approach runs code entirely on the user's machine.
1.  **Fetch:** Retrieve the question stub and **sample test cases** (inputs and expected outputs).
2.  **Generate Harness:** Automatically generate a local runner script (e.g., `test_runner.py`) that:
    *   Imports the user's solution function.
    *   Iterates through the sample test cases.
    *   Asserts the output matches the expected result.
3.  **Limitation:** Users can only verify against sample cases locally. Hidden test cases cannot be run locally.

#### Option B: Remote Execution (Submit to LeetCode)
This approach mimics the "Submit" button functionality.
1.  **Fetch:** Retrieve only the question stub and description.
2.  **Authenticate:** Require the user to provide a valid `LEETCODE_SESSION` cookie and `csrf_token`.
3.  **Submit:** When the user triggers a "Run" command in the IDE:
    *   The tool packages the local code.
    *   Sends a `POST` request to the LeetCode GraphQL `interpretSolution` or `submitCode` endpoint.
    *   Polls the submission ID until results are ready.
    *   Returns the **full test result** (Pass/Fail, runtime, memory, failed test case details) to the IDE console.

### 📝 Detailed Implementation Prompt

**Project Title:** LeetCode Local Sync & Run CLI

**Objective:** Create a Command Line Interface (CLI) and IDE extension that allows developers to solve LeetCode problems in their local environment (VS Code, Vim, etc.) with seamless synchronization.

**Key Features to Implement:**

1.  **Authentication Module:**
    *   Implement a login flow that extracts `LEETCODE_SESSION` and `csrftoken` from the user's browser or accepts manual input.
    *   Securely store these credentials locally (e.g., in a config file with restricted permissions).

2.  **Question Fetcher:**
    *   Input: Question Number (Int).
    *   Process: Map Number → Slug → GraphQL Query (`questionData`).
    *   Output: Create a local directory `./leetcode/<number>-<slug>/` containing:
        *   `question.md` (Parsed description).
        *   `solution.<ext>` (Code stub).
        *   `test_cases.json` (Sample inputs/outputs).

3.  **Local Runner (Option A):**
    *   Command: `lc run <number>`
    *   Action: Executes `solution.<ext>` against `test_cases.json`.
    *   Output: Pass/Fail status for sample cases only.

4.  **Remote Submitter (Option B):**
    *   Command: `lc submit <number>`
    *   Action: Sends code to LeetCode servers via GraphQL `submitCode` mutation.
    *   Output: Real-time feedback on all test cases (including hidden ones), runtime beats, and memory usage.

5.  **IDE Integration:**
    *   Provide tasks/snippets for VS Code (in `tasks.json`) to trigger `lc run` and `lc submit` via keyboard shortcuts.

**Technical Constraints:**
*   Must handle rate limiting from LeetCode API.
*   Must parse HTML content from API into clean Markdown.
*   Must support multiple languages (Python, JavaScript, C++, Java) by detecting the file extension or config setting.

