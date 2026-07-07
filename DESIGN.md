---
name: Shadow AI Discovery
description: GCP Inventory & Governance Dashboard
colors:
  primary: "#3b82f6"
  secondary: "#0ea5e9"
  neutral-bg: "#0a0a0c"
  neutral-bg-sec: "#141518"
  neutral-card: "#1c1d22"
  border: "#3b3e48"
  text-primary: "#f3f4f6"
  text-secondary: "#94a3b8"
  text-muted: "#64748b"
  btn-violet: "#3b82f6"
  btn-teal: "#1d4ed8"
  pure-white: "#ffffff"
  spinner-track: "rgba(255, 255, 255, 0.3)"
  score-track: "rgba(255, 255, 255, 0.08)"
  shadow-low: "rgba(0, 0, 0, 0.2)"
  shadow-med: "rgba(0, 0, 0, 0.5)"
  shadow-high: "rgba(0, 0, 0, 0.4)"
  accent-rose: "#f87171"
  accent-amber: "#fbbf24"
  accent-emerald: "#34d399"
  glow-purple: "rgba(59, 130, 246, 0.08)"
  badge-type: "rgba(14, 165, 233, 0.15)"
  badge-agent: "rgba(59, 130, 246, 0.15)"
  badge-agent-shadow: "rgba(59, 130, 246, 0.04)"
  badge-runtime: "rgba(255, 255, 255, 0.05)"
  row-selected: "rgba(59, 130, 246, 0.08)"
  row-hover: "rgba(255, 255, 255, 0.02)"
  tint-emerald-bg: "rgba(52, 211, 153, 0.03)"
  tint-emerald-border: "rgba(52, 211, 153, 0.1)"
  tint-emerald-text: "#a7f3d0"
  tint-amber-bg: "rgba(251, 191, 36, 0.03)"
  tint-amber-border: "rgba(251, 191, 36, 0.1)"
  tint-amber-text: "#fde68a"
  tint-rose-bg: "rgba(248, 113, 113, 0.03)"
  tint-rose-border: "rgba(248, 113, 113, 0.1)"
  tint-rose-text: "#fca5a5"
  tint-neutral-bg: "rgba(255, 255, 255, 0.03)"
  tint-neutral-border: "rgba(255, 255, 255, 0.02)"
  tint-surface: "rgba(255, 255, 255, 0.02)"
  tint-surface-dark: "rgba(0, 0, 0, 0.15)"
typography:
  display:
    fontFamily: "Outfit, -apple-system, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 700
    lineHeight: 1
  body:
    fontFamily: "Outfit, -apple-system, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Fira Code, monospace"
    fontSize: "0.75rem"
    fontWeight: 600
rounded:
  sm: "2px"
  md: "2px"
  lg: "4px"
  xl: "4px"
spacing:
  xs: "0.5rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.25rem"
  xl: "1.5rem"
  xxl: "2rem"
components:
  button-primary:
    backgroundColor: "#3b82f6"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0.625rem 1.25rem"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "0.625rem 1.25rem"
---

# Design System: Shadow AI Discovery

## 1. Overview

**Creative North Star: "The Tactical Console"**

The visual language of Shadow AI Discovery is designed to represent a high-utility command center. It offers cloud security engineers immediate clarity, high data density, and clear structural containment. Contrast is prioritized to ensure deep legibility of critical status reports, masked variables, and heuristics analysis. 

Rather than relying on modern SaaS aesthetic clichés or generic game-like glowing elements, the interface adopts a restrained approach. Color is utilized strictly for status indicator roles and key branding elements. Spacing and subtle variations in background tone are used to separate sections, conveying security and expert confidence.

**Key Characteristics:**
- High-contrast typography optimized for technical auditing.
- Strict functional color strategy for status and risk profiles.
- Layered layout containment with clear, clean borders.
- Restrained interactive state feedback without visual clutter.
- Clinical corner radiuses (sharp 0-4px corners) to convey hardware-chassis solidity.

## 2. Colors

The color palette is built around deep dark backgrounds paired with vibrant technical accents that serve specific semantic roles.

### Primary
- **Steel Blue** (#3b82f6): Used for branding elements, active selection states, and primary action highlights. Restrained to technical utilities.

### Secondary
- **Sky Blue** (#0ea5e9): Used for resource type indicators, highlighted variables, and secondary confidence metrics.

### Semantic Accents
- **Safe Emerald** (#34d399): Indicates low risk, verified settings, or completed operations.
- **Warning Amber** (#fbbf24): Flags moderate risks or pending items.
- **Risk Rose** (#f87171): Marks critical vulnerabilities, unauthenticated public ingress, or admin SA permissions.

### Neutral
- **Charcoal Void** (#0a0a0c): The base canvas background (deep matte gray).
- **Deep Charcoal** (#141518): Used for major section headers, secondary panels, and table backgrounds.
- **Space Card** (#1c1d22): Used for dashboard card components and metrics widgets.
- **Ink Primary** (#f3f4f6): Canonical body and title text color.
- **Ink Secondary** (#94a3b8): Muted labels, table columns, and descriptive text.
- **Scanner Border** (#3b3e48): High-contrast gray border for cards, table cells, and buttons.

### Utility & Tint
Functional tints and utility colors used for interactive states, component internals, and tonal layering. These are not semantic — they serve specific component needs.

- **Deep Blue** (#1d4ed8): Button gradient end.
- **Pure White** (#ffffff): Button text, spinner top-border.
- **White 30** (rgba(255, 255, 255, 0.3)): Spinner track.
- **White 8** (rgba(255, 255, 255, 0.08)): Score bar track background.
- **White 5** (rgba(255, 255, 255, 0.05)): Badge/hover tint.
- **White 3** (rgba(255, 255, 255, 0.03)): Indicator pill base background.
- **White 2** (rgba(255, 255, 255, 0.02)): Surface tint, grid item background.
- **Black 20** (rgba(0, 0, 0, 0.2)): Graph container background.
- **Black 15** (rgba(0, 0, 0, 0.15)): Table header background, env var list.
- **Black 50** (rgba(0, 0, 0, 0.5)): Card hover shadow.

**The Functional Accent Rule.** Saturated accent colors are forbidden for purely decorative styling. Every usage of blue, cyan, emerald, amber, or rose must map to a specific resource type, risk severity, or system status.

## 3. Typography

**Display Font:** Outfit (sans-serif)
**Body Font:** Outfit (sans-serif)
**Label/Mono Font:** Fira Code (monospace)

The typeface pairing matches a modern geometric sans-serif (Outfit) for clean layouts with a high-utility monospace font (Fira Code) for environment variables, service accounts, and resource regions.

### Hierarchy
- **Display** (Bold, 2.25rem, line-height 1): Used for large dashboard metrics values.
- **Headline** (Bold, 1.4rem, line-height 1.2): Used for primary screen headings and page headers.
- **Title** (Bold, 1.1rem, line-height 1.3): Used for cards, tables, and section headings.
- **Body** (Regular, 0.95rem, line-height 1.5): Used for descriptions, status details, and text paragraphs.
- **Label** (SemiBold, 0.75rem, letter-spacing 0.05em): Used for column titles, badges, and uppercase identifiers.

**The 75ch Limit Rule.** Body line length must be capped at 65–75 characters (75ch max) to maintain comfortable reading density in descriptions and details drawers.

## 4. Elevation

The system utilizes tonal layering to represent structural depth, rather than heavy dropshadows or complex gradients. 

Depth is conveyed through progressive variations in dark background values (Charcoal Void → Deep Charcoal → Space Card). Dropshadows are applied strictly as reactive feedback to state changes or to separate layered windows from the main dashboard context.

### Shadow Vocabulary
- **Ambient Elevation** (`box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15)`): Applied to cards and containers.
- **Details Elevation** (`box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4)`): Used for the detail panel drawer when hovering or sticky.
- **Focus Ring** (`box-shadow: 0 0 0 2px var(--accent-purple-glow)`): Used under active focus inputs to provide state prominence.

**The Elevation State Rule.** No dropshadow is allowed at rest on flat layout blocks. Shadows are reserved as reactive indicators for hover state transitions, active selections, or details drawers.

## 5. Components

### Buttons
- **Shape:** Sharp rectangular corners (2px radius).
- **Primary:** Gradient background (linear-gradient(135deg, #3b82f6, #1d4ed8)), white text, internal padding (10px 20px).
- **Secondary:** Transparent background, Scanner Border stroke (1px solid #3b3e48), Ink Primary text, internal padding (10px 20px).
- **Hover / Focus:** Primary button uses an opacity reduction (0.9) and a subtle translate Y offset (-1px); secondary button uses a light background fill (#3b3e48).

### Cards / Containers
- **Corner Style:** Sharp rectangular corners (2px for metrics widgets, 4px for content cards/detail drawers).
- **Background:** Space Card (#1c1d22) for metrics, Deep Charcoal (#141518) for tables and details.
- **Border:** Solid Scanner Border (1px solid #3b3e48).
- **Internal Padding:** Spacing scale (1.5rem / 24px).

### Inputs / Fields
- **Style:** Background Space Card (#1c1d22), 1px solid Scanner Border, 2px radius.
- **Focus:** Replaced border color or outline with Steel Blue.
- **Error / Disabled:** Border changes to Risk Rose; opacity reduced to 0.6 if disabled.

### Navigation / Tabs
- **Style:** Flex tab bar. Active button uses Heuristic Blue background highlight (var(--accent-purple-glow)) and Heuristic Blue text color (var(--accent-purple)).

## 6. Do's and Don'ts

### Do:
- **Do** use specific semantic colors (Safe Emerald, Warning Amber, Risk Rose) for risk and scan breakdowns to establish instant visual clarity.
- **Do** mask env var values containing secret-like keys before showing them in detail drawers.
- **Do** ensure contrast of labels and helper text is at least 4.5:1 against the dark background.
- **Do** use Fira Code (monospace) for technical identifiers such as service account names and environmental variables.
- **Do** keep all corners flat and sharp (0px to 4px border-radius) to match the clinical console aesthetic.

### Don't:
- **Don't** use border-left or border-right accent stripes greater than 1px on metrics cards or list items.
- **Don't** apply wide, soft shadows (M ≥ 16px blur) together with border strokes on cards at rest.
- **Don't** use decorative grid background patterns that mimic blueprints or grid paper.
- **Don't** use text gradients in headings or paragraph elements.
- **Don't** exceed 4px corner rounding on cards and drawers.
