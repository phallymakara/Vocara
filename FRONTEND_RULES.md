# Frontend Engineering & UI Consistency Rules

These rules govern all frontend development for the Vocara project. Follow every rule strictly.

## 1. UI & Visual Hierarchy
* **Zero Shadows**: Never use box-shadows (`box-shadow: none !important;`). Use subtle flat borders (`border-slate-200` or `#e2e8f0`) instead.
* **No Unnecessary Container Fills**: Do not fill background colors on containers outside of text unless explicitly requested. Keep the layout flat, clean, and breathable.
* **No Container Nesting Clutter**: Avoid nesting cards inside cards. Maintain a clean, minimal visual hierarchy.
* **Icons**: Use only standard, clean icon libraries (Lucide React). Never use AI-generated or inconsistent icons.
* **Mobile Responsiveness**: On mobile screens, hide the text product name and display only the brand logo.
* **Fonts & Typography**: Follow consistent typography (`Calibri`, `Kantumruy Pro`, `Inter`, sans-serif) across all headers, inputs, buttons, and labels.
* **No Icons in Documentation**: Do not use decorative icons in README markdown files.

## 2. Forms & Error Handling
* **Exact Error Placement**: Always display error messages directly adjacent to the input field where the problem occurred.
* **No Technical Jargon**: Never expose stack traces, database exceptions, internal HTTP codes, or technical jargon to users. Use simple, human-friendly guidance.
* **Flat Error Styling**: For input errors, highlight the field with a red border (`border-red-600` / `#dc2626`) and render plain red error text below the input. Never wrap error messages in colored cards or shadow boxes.
* **Input Placeholders**: Do not use fake or example data as input placeholders. Use concise descriptive labels or clear hints.

## 3. Engineering & Architecture
* **Dynamic Endpoints**: Never hardcode API hostnames or ports. Use `import.meta.env.VITE_API_BASE_URL` with dynamic relative fallback (`/api/v1`).
* **Clean File Responsibilities**: Keep components small, focused, and single-purpose. Avoid large multi-hundred-line monolithic files.
* **Structured State & API Flow**: Centralize API communication in typed API client services and reusable hooks.
* **No Breaking Changes**: Preserve all existing backend endpoints, database structures, business logic, and roles.

