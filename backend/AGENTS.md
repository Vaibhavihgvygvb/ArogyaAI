# ArogyaAI Agent Instructions

Before making any code changes:

1. Read:

   * docs/PROJECT_CONTEXT.md
   * docs/ARCHITECTURE.md
   * docs/CURRENT_TASK.md

2. Analyze existing files before generating code.

3. Show implementation plan before writing code.

4. Do not modify unrelated files.

5. Follow SQLAlchemy 2.0 style.

6. Build in this order:

   * Database
   * Models
   * Schemas
   * Services
   * APIs
   * Tests

Current Status:

Completed:

* SQLite infrastructure
* Base class
* SessionLocal
* FastAPI startup initialization
* Model registry
* Doctor model
* Doctor table verification

Next Task:

* Patient model

Future:

* Visit model
* Medication model
* Reminder system
