# MVP Scope

## In Scope

### Core Features
- [x] Streamlit UI with all input controls (neighborhood, vibe, budget, group context, food, interests, travel distance, energy)
- [x] LifestyleAgent with observe → gather → reason → generate → save loop
- [x] Weather-aware recommendations (mock, seasonal)
- [x] Mock event data — 15 events across 8 Chicago neighborhoods
- [x] Mock place data — 20 venues/restaurants across 8 Chicago neighborhoods
- [x] Score-based filtering for events and places
- [x] 3 distinct plan variants per request
- [x] Plan cards with title, vibe badge, neighborhood, budget estimate, confidence score, itinerary
- [x] LLM integration (OpenAI-compatible)
- [x] Full offline fallback (rule-based engine)
- [x] SQLite persistence: user_preferences, plan_history, feedback
- [x] Thumbs up / thumbs down feedback
- [x] Save favorite neighborhood
- [x] Save favorite vibe
- [x] Preferences persist across sessions

### Neighborhoods Covered
- Logan Square
- Wicker Park
- Lakeview
- Lincoln Park
- Pilsen
- West Loop
- River North
- Uptown

### Event Categories
- Live music (concerts, jazz, indie)
- Comedy (improv, standup, open mic)
- Sports (Cubs, Blackhawks)
- Arts (art walks, poetry slams)
- Food markets

### Place Categories
- Restaurants: ramen, tacos, burgers, mediterranean, pizza, fusion, farm-to-table, gastropub
- Bars: cocktail bars, dive bars, tiki bars, sports bars, breweries
- Coffee: specialty coffee, neighborhood cafes
- Museums: Art Institute, Chicago History Museum

## Out of Scope for MVP

- Real-time event data (Ticketmaster, Eventbrite APIs)
- Real weather API integration
- User authentication / multi-user
- Mobile app
- Maps / directions integration
- Social features (share plans, invite friends)
- Push notifications
- Paid/premium tier
- Restaurant reservation booking
- Ticket purchasing

## Known Limitations

- Mock data is static — new events/venues require manual JSON edits
- Weather is simulated based on current month, not real forecast
- Travel distance filter is cosmetic (no geo-coordinates in mock data)
- "Tonight" vs "this weekend" changes which events appear but does not gate-check operating hours precisely
