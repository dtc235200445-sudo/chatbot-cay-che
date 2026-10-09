# Tea Scholar AI

Build a complete frontend website called Tea AI.

This is a scientific and educational AI platform focused on tea plants, tea leaves, tea cultivation, diseases, pests, weather, harvesting and tea-related knowledge.

MAIN GOAL

Create a simple, scientific, clean and beautiful frontend.

The design should NOT be overly complicated, flashy, or look like a generic AI startup.

The visual style should feel like:

Scientific + Agricultural + Modern + Minimal + Trustworthy

Use a clean light theme with plenty of whitespace.

Use a restrained tea-green color palette combined with white, light gray and dark text.

Do not overuse green.

The website should look suitable for a university research/project demonstration.

1. MAIN LAYOUT

Use a simple dashboard layout:

┌─────────────────────────────────────────────────────┐
│                    TOP HEADER                       │
├───────────────┬─────────────────────────────────────┤
│               │                                     │
│    SIDEBAR    │             MAIN CONTENT            │
│               │                                     │
│               │                                     │
│               │                                     │
└───────────────┴─────────────────────────────────────┘


Desktop:

Fixed left sidebar

Main content area

Clean top header

Mobile:

Sidebar becomes hamburger menu

Fully responsive

2. SIDEBAR

At the top:

🌿 Tea AI

Small subtitle:

Tea Knowledge Assistant

Navigation:

Main

🏠 Dashboard

🔎 Search

🌦 Weather

🤖 AI Assistant

System

⚙ Settings

At the bottom:

Small user profile section.

Keep sidebar simple.

Do not use too many menu items.

3. COLOR SYSTEM

Use a scientific natural palette.

Primary:

Tea Green

Supporting colors:

Deep green

Soft green

White

Very light gray

Dark gray

Light beige if necessary

Use green mainly for:

Primary buttons

Active navigation

Important information

AI highlights

Status indicators

Avoid strong gradients.

Avoid neon colors.

Avoid glassmorphism.

Avoid excessive shadows.

4. TYPOGRAPHY

Use:

Inter

or another clean modern sans-serif font.

Typography should be:

Clear

Scientific

Easy to read

Professional

Use strong hierarchy:

Page title
→ Section title
→ Card title
→ Body text
→ Metadata

5. DASHBOARD

Create the main Dashboard page.

Header:

Tea AI

Subtitle:

Intelligent knowledge assistant for tea cultivation and tea leaves.

Below the header, create three main feature cards.

CARD 1

Icon: Search

Title:

Knowledge Search

Description:

Search information about tea plants, leaves, diseases, cultivation and research.

Button:

Search

CARD 2

Icon: Weather

Title:

Weather

Description:

View current weather and forecast information for tea-growing areas.

Button:

View weather

CARD 3

Icon: AI

Title:

AI Assistant

Description:

Ask questions and explore knowledge about tea with AI.

Button:

Ask AI

Make the AI Assistant card slightly more prominent.

6. DASHBOARD — QUICK ACCESS

Add a section:

Quick questions

Display simple clickable chips:

Tea leaf diseases

Tea cultivation

Tea pests

Fertilization

Harvesting

Weather conditions

Clicking a question should navigate to the AI Assistant page.

7. DASHBOARD — RECENT ACTIVITY

Create a simple section:

Recent activity

Example:

Search
“Tea leaf diseases”

AI Assistant
“Why are tea leaves turning yellow?”

Weather
“Phú Thọ weather”

Use simple list items.

8. SEARCH PAGE

Create a clean scientific search interface.

Page title:

Knowledge Search

Subtitle:

Search information from the Tea Knowledge Base.

Large search bar:

🔎

Placeholder:

Search tea knowledge...

Below:

Filter buttons:

All

Documents

Research

Images

Create realistic mock search results.

Example:

Tea Leaf Diseases

Description:

Common diseases affecting tea leaves, symptoms, causes and prevention.

Metadata:

Document · Tea Research

Tea Cultivation Techniques

Description:

Basic techniques for planting, fertilization, irrigation and harvesting.

Metadata:

Document · Agriculture

Tea Plant Characteristics

Description:

Botanical characteristics and growth stages of tea plants.

Metadata:

Research · Botany

Each result should contain:

Title

Description

Source

Type

Date

View button

Keep the cards compact and clean.

9. WEATHER PAGE

Create a simple scientific weather dashboard.

Page title:

Weather

Subtitle:

Weather conditions for tea-growing areas.

Location selector:

📍 Phú Thọ, Vietnam

Create a main weather card.

Display:

28°C

Partly cloudy

Then:

Humidity: 78%

Rain probability: 20%

Wind: 12 km/h

7-DAY FORECAST

Create simple forecast cards:

Today
Tomorrow
Day 3
Day 4
Day 5
Day 6
Day 7

Each card contains:

Weather icon
Temperature
Rain probability

Do not make the weather interface overly colorful.

TEA WEATHER INSIGHT

Add a simple information card:

Tea Growing Conditions

Status:

Favorable

Description:

“Current weather conditions appear generally suitable for tea cultivation.”

This is mock data only.

10. AI ASSISTANT PAGE

This is the main feature.

Create a clean chatbot interface.

Page header:

🤖 Tea AI Assistant

Subtitle:

Ask questions about tea plants, leaves and cultivation.

11. EMPTY CHAT STATE

When there is no conversation:

Center the page content.

Icon:

🌿

Title:

How can I help you?

Description:

Ask anything about tea plants, tea leaves, cultivation, diseases or harvesting.

Below create suggested questions:

Why are tea leaves turning yellow?

What diseases affect tea leaves?

How should tea plants be fertilized?

When should tea leaves be harvested?

How does weather affect tea?

12. CHAT AREA

When a conversation exists:

User messages appear on the right.

AI messages appear on the left.

Keep bubbles simple.

Do not use excessive rounded shapes.

Example:

USER:

Why are my tea leaves turning yellow?

AI:

Tea leaf yellowing can have several possible causes, including nutrient problems, water stress, pests or disease.

Then structure the response:

Possible causes

Nutrient deficiency

Water stress

Pest damage

Disease

What to check

Check the leaf pattern, soil moisture and surrounding plant condition.

13. CHAT INPUT

Fixed at bottom of chat area.

Input:

Ask Tea AI...

Buttons:

📎 Attach

📷 Image

Send button.

These buttons are UI only for now.

No real upload or AI functionality is required.

14. SOURCE SECTION

AI responses should optionally display:

Sources

Example:

📄 Tea Cultivation Guide

Page 24

📄 Tea Plant Disease Research

Page 12

Button:

View source

This prepares the UI for future RAG integration.

15. IMAGE ANALYSIS PLACEHOLDER

Do NOT implement the actual image recognition model.

Only create the UI state for future development.

When clicking the image button, show an upload modal:

Analyze Tea Leaf

Drag and drop image here

or

Choose image

After upload, mock:

Image ready for analysis

Button:

Analyze

This will later connect to a computer vision model.

16. SETTINGS PAGE

Create a very simple settings page.

Sections:

Appearance

Light mode

Language

Vietnamese

AI Response

Short

Balanced

Detailed

Interface

Show source references
Enable animations

These are frontend mock settings only.

17. COMPONENTS

Create reusable components:

Sidebar

Header

Navigation

Feature Card

Search Bar

Search Result Card

Weather Card

Forecast Card

Chat Message

AI Response

Source Card

Button

Input

Modal

Dropdown

Badge

Loading state

Empty state

Error state

Keep all components visually consistent.

18. INTERACTIONS

Implement basic frontend navigation.

Dashboard → Search

Dashboard → Weather

Dashboard → AI Assistant

Search → Search results

Weather → Weather dashboard

AI Assistant → Chat

Suggested question → populate chat input

Sidebar navigation should work.

Buttons should have hover states.

Cards should have subtle hover effects.

No backend is required.

Use mock data.

19. RESPONSIVE DESIGN

Desktop:

Sidebar + content.

Tablet:

Collapsed sidebar.

Mobile:

Hamburger menu.

Cards should stack vertically.

Search results should remain readable.

Chat interface should occupy the full mobile screen.

Weather cards should become horizontally scrollable or stack.

20. SCIENTIFIC UI STYLE

The most important design requirement:

The website should feel like a scientific knowledge platform, not a commercial farming website.

Use:

Lots of whitespace

Clear typography

Thin borders

Subtle shadows

Simple icons

Minimal decoration

Clear data presentation

Consistent spacing

Avoid:

Huge hero sections

Excessive gradients

Neon colors

3D illustrations

Excessive animations

Overly rounded cards

Complex dashboards

Too many colors

21. FRONTEND ONLY

For this version, DO NOT implement:

Real authentication

Real database

Real LLM

RAG

Knowledge Graph

Neo4j

Weather API

Search API

Computer vision model

Use mock data and placeholder services.

However, organize the frontend code cleanly so that later it can connect to:

Tea AI Frontend
       │
       ▼
    Backend API
       │
       ├── AI / LLM
       ├── RAG
       ├── Knowledge Graph
       ├── Weather API
       ├── Search
       └── Image Analysis


22. FINAL REQUIREMENT

Build the complete frontend prototype with these pages:

Dashboard

Knowledge Search

Weather

AI Assistant

Settings

The result should be:

Simple + Scientific + Clean + Modern + Beautiful

Do not over-design it.

The most important thing is clarity and usability.

The website should look like a serious university AI research project that could later become a real Tea Knowledge Assistant.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/7bd946dc-01e1-4d4e-996f-138396b8b697).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
