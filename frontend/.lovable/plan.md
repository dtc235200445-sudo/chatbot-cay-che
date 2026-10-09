# Tea AI frontend prototype

## Overview
Build a complete responsive Tea AI research dashboard with five connected pages and mock-only interactions. The visual language will be light, restrained, and scientific: white and pale neutral surfaces, tea green used selectively, thin borders, compact typography, minimal shadows, and no gradients or decorative effects.

## Pages and interactions
- **Dashboard:** feature cards for Knowledge Search, Weather, and AI Assistant; quick-question chips that open the assistant; recent activity list.
- **Knowledge Search:** working mock search field, result filtering, realistic compact research results, and clear empty/loading/error presentation states.
- **Weather:** Phú Thọ location selector, current conditions, seven-day forecast, and a tea-growing suitability insight.
- **AI Assistant:** empty state, suggested prompts, mock conversation generation, user/assistant message styling, citations, fixed composer, attachment controls, and image-analysis upload modal with mock ready/analyze states.
- **Settings:** mock appearance, language, response-length, source-reference, and animation controls with local page state.
- **Navigation:** fixed desktop sidebar, compact tablet behavior, mobile drawer, active-page state, and functional links between all pages.

## Shared design and components
- Establish semantic colors, typography, spacing, borders, shadows, and restrained motion in the global design system.
- Add a botanical Tea AI brand mark and consistent page shell/header.
- Create reusable feature, search result, weather, forecast, source, state, navigation, badge, input, modal, and control components.
- Use the existing shadcn controls and install AI Elements primitives for conversation, messages, prompt input, and loading states.
- Keep all data and behavior local and mocked; no authentication, database, external API, or AI service.

## Responsive and quality checks
- Verify desktop at 1280px and mobile at 390px, including drawer navigation, stacked cards, readable search results, scrollable forecasts, and full-height chat.
- Verify search, filters, suggested questions, chat sending, modal flow, settings controls, active navigation, and keyboard-accessible interactions.
- Add unique metadata for every page and confirm the final build, lint, and browser console are clean.

## Technical details
- TanStack Start file routes: `/`, `/search`, `/weather`, `/assistant`, and `/settings`.
- Tailwind v4 semantic tokens in `src/styles.css`; Inter loaded from the root document head.
- React local state drives mock filtering, messaging, upload status, and settings.
- Lucide icons provide scientific/navigation cues; the Tea AI identity uses a custom botanical mark rather than a generic AI icon.
