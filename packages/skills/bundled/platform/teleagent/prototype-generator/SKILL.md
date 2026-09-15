---
name: prototype-generator
description: Interactive HTML prototype generator for software projects. Use when user asks to "create prototype", "generate wireframe", "make mockup", "生成原型", "画原型", "交互原型", "原型图", or similar. Covers Web management systems, mobile apps, mini-programs, and data visualization dashboards. Produces single-file interactive HTML prototypes with high-fidelity UI, mock data, and page navigation. Can read existing PRD documents to auto-extract fields, flows, and permissions.
name_cn: 项目原型生成器
description_cn: 生成高交互单HTML原型，支持Web管理系统、移动端APP、小程序和大屏展示，可基于PRD文档自动生成
---

# Prototype Generator

Generate single-file, high-interaction HTML prototypes for software projects. Output one `.html` file that opens directly in a browser with realistic UI, mock data, and page navigation.

## Workflow

1. **Classify** prototype type
2. **Gather** requirements (from PRD or conversation)
3. **Generate** HTML prototype
4. **Iterate** based on user feedback

## Step 1: Classify Prototype Type

Determine from user input or PRD content:

- **web**: Web management system (sidebar + tables + forms)
- **app**: Mobile application (bottom tab bar + card layout)
- **mini**: Mini-program (WeChat-style header + tabbar)
- **dashboard**: Data visualization large screen (dark theme + ECharts)
- **other**: Other or unclear

This determines which CSS layout and UI style to use.

## Step 2: Gather Requirements

### If PRD exists

1. Read the total PRD (`README.md`) to get: project name, roles, module list
2. Read each module PRD to extract:
   - Page list and routes
   - Form fields (name, type, required, options, validation)
   - Table columns and data
   - Status values and color tags
   - Workflow steps and transitions
   - Permission rules (which role sees what)
3. Generate pages directly from extracted data — no need to ask further

### If no PRD

Use `question` tool to fill gaps in 2-3 batches. Core items:

- Project name and type
- Page list (what pages are needed)
- Key forms and fields
- Roles and permission differences
- Special UI requirements (maps, charts, file upload)

Ask only what's missing. If user provides enough detail upfront, skip to Step 3.

## Step 3: Generate HTML Prototype

### Output

Single HTML file: `{project-name}-prototype.html` in the working directory.

### Type-specific UI specs

Read the matching spec for layout, colors, and component patterns:

- **web** — [references/web-ui-spec.md](references/web-ui-spec.md)
- **app** — [references/app-ui-spec.md](references/app-ui-spec.md)
- **mini** — [references/mini-ui-spec.md](references/mini-ui-spec.md)
- **dashboard** — [references/dashboard-ui-spec.md](references/dashboard-ui-spec.md)

### Generation rules

- Use Chinese for all labels, placeholders, button text
- Embed all CSS and JS in the single HTML file (no external CSS/JS except icon fonts if needed)
- Create 5-8 mock data records with realistic Chinese content
- Implement page switching via JavaScript (all pages in one HTML, toggle visibility)
- Forms must be fillable: inputs accept text, dropdowns open, checkboxes toggle
- Buttons must have visual hover/active feedback
- Status tags must use correct colors per type spec
- Permission differences: show/hide elements based on selected role
- Add a **role switcher** (top-right corner dropdown) so reviewer can toggle between roles to see permission differences
- For forms from PRD: include ALL fields, with correct control types, options, and required marks (*)
- For tables from PRD: include ALL columns with mock data matching field types
- For workflows from PRD: show status labels matching the status dictionary colors
- Responsive: web/dashboard look good at 1920×1080; app/mini center at mobile width

### Mock data guidelines

- Use realistic Chinese names, company names, addresses
- Cover ALL status values (at least one record per status)
- Include boundary cases (long names, large amounts)
- Dates in current year
- Financial numbers with comma separators

## Step 4: Iterate

After generating, ask:
> 原型已生成，有需要调整的地方吗？

Common iteration patterns:
- Add/remove form fields
- Change page layout or navigation
- Adjust colors or spacing
- Add missing pages or interactions
- Fix mock data
- Change role permission display
