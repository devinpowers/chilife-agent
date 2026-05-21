# ChiLife Agent — Project Overview

## What It Is

ChiLife Agent is a personal AI lifestyle concierge for Chicago. It helps you decide what to do tonight or this weekend by considering your neighborhood, vibe, budget, group context, weather, food preferences, and saved tastes — then generating 3 fully-planned evening itineraries.

## The Problem

Chicago has an overwhelming amount to do. Finding the right combination of dinner, a show, and a bar that fits your mood, your budget, and who you're with requires 20 minutes of Yelp, Resident Advisor, and Google. ChiLife Agent collapses that into a single conversation.

## Core Value Proposition

| Without ChiLife Agent | With ChiLife Agent |
|-----------------------|--------------------|
| Search Yelp, RA, Google separately | One input form |
| Generic "top 10" lists | Plans personalized to your vibe and context |
| No weather awareness | Outdoor plans adjusted for conditions |
| No memory | Learns your neighborhoods and vibes over time |
| You assemble the evening | Full itinerary with times and venues |

## MVP Scope

- Streamlit web app (local-first)
- Mock event and venue data for 8 Chicago neighborhoods
- Rule-based plan generator (no API key required)
- Optional LLM enhancement via OpenAI-compatible API
- SQLite for preference and feedback persistence

## Target User

Chicago residents aged 25–40 who want a low-friction way to find great evenings without endless searching. Particularly useful for:
- Post-work "what should I do tonight?" decisions
- Planning a date night
- Organizing a group outing
- Exploring a new neighborhood
