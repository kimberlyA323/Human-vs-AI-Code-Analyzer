# Human vs. AI Code Analyzer Requirements
## 1. Customer Statement of Requirements

The Human vs. AI Code Analyzer will be a web application that allows users to compare human-written code with AI-generated code. The user will submit two pieces of Python code intended to solve the same programming problem. The application will compare both code samples based on test results, execution time, failed tests or errors, and code complexity.

The main purpose of the application is to help students and developers better understand how AI-generated code compares with code written by humans.

## 2. Requirements Specification

### Functional Requirements

1. The system shall allow users to create an account.
2. The system shall allow users to log in and log out.
3. The system shall allow users to enter human-written Python code.
4. The system shall allow users to enter AI-generated Python code.
5. The system shall allow users to submit both code samples for comparison.
6. The system shall run test cases on both code samples.
7. The system shall display the number of passed and failed test cases.
8. The system shall measure the execution time of both code samples.
9. The system shall calculate the code complexity of both code samples.
10. The system shall display the comparison results side by side.
11. The system shall save completed comparisons in the database.
12. The system shall allow users to view previous comparison results.

### Non-Functional Requirements

1. The application should have a simple and easy-to-use interface.
2. The application should work in common web browsers such as Chrome, Edge, and Firefox.
3. The application should respond to user actions within a reasonable amount of time.
4. User passwords should be stored securely.
5. The application should validate user input before processing it.
6. The application should handle invalid code without crashing.
7. The source code should be organized and maintained using GitHub.
8. The application should be designed so that more features can be added later.

## 3. Data and Storage Blueprint

### Data Input

The main data for the application will be entered manually by the user. The user will paste human-written Python code and AI-generated Python code into separate input fields.

The application will also generate data during the comparison process, including test results, execution time, failed tests or errors, and code complexity.

### Database or Storage

The application will use PostgreSQL as its relational database. PostgreSQL will store user account information, submitted code samples, comparison results, execution times, test results, code complexity results, and previous comparison history.

GitHub will be used for source code management and project tracking.
