"""NovaTour travel tools registry.

All tools use the Strands @tool decorator and are designed for use
with Nova Sonic's tool calling via BidiAgent.
"""

from .booking import book_flight
from .flights import search_flights
from .hotels import search_hotels
from .itinerary import plan_itinerary
from .places import search_places
from .routes import plan_route
from .weather import get_forecast, get_weather

ALL_TOOLS = [
    search_flights,
    search_hotels,
    search_places,
    plan_route,
    get_weather,
    get_forecast,
    plan_itinerary,
    book_flight,
]
