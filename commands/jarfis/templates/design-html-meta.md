# Design HTML Meta Template

Insert the following meta information as an HTML comment at the top of each HTML mockup file.

```html
<!--
owner: DESIGN
projects: [{project_name}]
url: {url_path}
last_updated: {date}
last_updated_by: {ticket}
summary: {page_description}
responsive: {PC / PC + Mobile / PC + Mobile + Tablet}
-->
```

## Field Descriptions

| Field | Description |
|------|------|
| owner | Always `DESIGN` |
| projects | List of projects this mockup is related to |
| url | URL path that the mockup represents |
| last_updated | Last modification date |
| last_updated_by | Ticket/workflow that triggered the modification |
| summary | One-line description of the page |
| responsive | Responsive support scope |
