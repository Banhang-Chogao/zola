#!/usr/bin/env python3
"""Generate static JSON seed data for Flight DB tool."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "static" / "data" / "flight-db"

# Default airline / alliance seed (typical flight-tracking reference set)
ALLIANCE_SEED = [
    {"code": "AA", "name": "American Airlines", "alliance": "Oneworld", "hub": "DFW", "hubCity": "Dallas", "country": "United States"},
    {"code": "AC", "name": "Air Canada", "alliance": "Star Alliance", "hub": "YYZ", "hubCity": "Toronto", "country": "Canada"},
    {"code": "AF", "name": "Air France", "alliance": "SkyTeam", "hub": "CDG", "hubCity": "Paris", "country": "France"},
    {"code": "AI", "name": "Air India", "alliance": "Star Alliance", "hub": "DEL", "hubCity": "New Delhi", "country": "India"},
    {"code": "AY", "name": "Finnair", "alliance": "Oneworld", "hub": "HEL", "hubCity": "Helsinki", "country": "Finland"},
    {"code": "BA", "name": "British Airways", "alliance": "Oneworld", "hub": "LHR", "hubCity": "London", "country": "United Kingdom"},
    {"code": "BR", "name": "EVA Air", "alliance": "Star Alliance", "hub": "TPE", "hubCity": "Taipei", "country": "Taiwan"},
    {"code": "CA", "name": "Air China", "alliance": "Star Alliance", "hub": "PEK", "hubCity": "Beijing", "country": "China"},
    {"code": "CI", "name": "China Airlines", "alliance": "SkyTeam", "hub": "TPE", "hubCity": "Taipei", "country": "Taiwan"},
    {"code": "CX", "name": "Cathay Pacific", "alliance": "Oneworld", "hub": "HKG", "hubCity": "Hong Kong", "country": "Hong Kong"},
    {"code": "CZ", "name": "China Southern", "alliance": "SkyTeam", "hub": "CAN", "hubCity": "Guangzhou", "country": "China"},
    {"code": "DL", "name": "Delta Air Lines", "alliance": "SkyTeam", "hub": "ATL", "hubCity": "Atlanta", "country": "United States"},
    {"code": "EK", "name": "Emirates", "alliance": "Independent", "hub": "DXB", "hubCity": "Dubai", "country": "UAE"},
    {"code": "ET", "name": "Ethiopian Airlines", "alliance": "Star Alliance", "hub": "ADD", "hubCity": "Addis Ababa", "country": "Ethiopia"},
    {"code": "EY", "name": "Etihad Airways", "alliance": "Independent", "hub": "AUH", "hubCity": "Abu Dhabi", "country": "UAE"},
    {"code": "GA", "name": "Garuda Indonesia", "alliance": "SkyTeam", "hub": "CGK", "hubCity": "Jakarta", "country": "Indonesia"},
    {"code": "HA", "name": "Hawaiian Airlines", "alliance": "Oneworld", "hub": "HNL", "hubCity": "Honolulu", "country": "United States"},
    {"code": "JL", "name": "Japan Airlines", "alliance": "Oneworld", "hub": "HND", "hubCity": "Tokyo", "country": "Japan"},
    {"code": "KE", "name": "Korean Air", "alliance": "SkyTeam", "hub": "ICN", "hubCity": "Seoul", "country": "South Korea"},
    {"code": "KL", "name": "KLM", "alliance": "SkyTeam", "hub": "AMS", "hubCity": "Amsterdam", "country": "Netherlands"},
    {"code": "LH", "name": "Lufthansa", "alliance": "Star Alliance", "hub": "FRA", "hubCity": "Frankfurt", "country": "Germany"},
    {"code": "LX", "name": "Swiss International", "alliance": "Star Alliance", "hub": "ZRH", "hubCity": "Zurich", "country": "Switzerland"},
    {"code": "MH", "name": "Malaysia Airlines", "alliance": "Oneworld", "hub": "KUL", "hubCity": "Kuala Lumpur", "country": "Malaysia"},
    {"code": "MU", "name": "China Eastern", "alliance": "SkyTeam", "hub": "PVG", "hubCity": "Shanghai", "country": "China"},
    {"code": "NH", "name": "All Nippon Airways", "alliance": "Star Alliance", "hub": "HND", "hubCity": "Tokyo", "country": "Japan"},
    {"code": "NZ", "name": "Air New Zealand", "alliance": "Star Alliance", "hub": "AKL", "hubCity": "Auckland", "country": "New Zealand"},
    {"code": "OS", "name": "Austrian Airlines", "alliance": "Star Alliance", "hub": "VIE", "hubCity": "Vienna", "country": "Austria"},
    {"code": "OZ", "name": "Asiana Airlines", "alliance": "Star Alliance", "hub": "ICN", "hubCity": "Seoul", "country": "South Korea"},
    {"code": "PR", "name": "Philippine Airlines", "alliance": "Oneworld", "hub": "MNL", "hubCity": "Manila", "country": "Philippines"},
    {"code": "QF", "name": "Qantas", "alliance": "Oneworld", "hub": "SYD", "hubCity": "Sydney", "country": "Australia"},
    {"code": "QR", "name": "Qatar Airways", "alliance": "Oneworld", "hub": "DOH", "hubCity": "Doha", "country": "Qatar"},
    {"code": "SA", "name": "South African Airways", "alliance": "Star Alliance", "hub": "JNB", "hubCity": "Johannesburg", "country": "South Africa"},
    {"code": "SK", "name": "SAS", "alliance": "SkyTeam", "hub": "ARN", "hubCity": "Stockholm", "country": "Sweden"},
    {"code": "SN", "name": "Brussels Airlines", "alliance": "Star Alliance", "hub": "BRU", "hubCity": "Brussels", "country": "Belgium"},
    {"code": "SQ", "name": "Singapore Airlines", "alliance": "Star Alliance", "hub": "SIN", "hubCity": "Singapore", "country": "Singapore"},
    {"code": "TG", "name": "Thai Airways", "alliance": "Star Alliance", "hub": "BKK", "hubCity": "Bangkok", "country": "Thailand"},
    {"code": "TK", "name": "Turkish Airlines", "alliance": "Star Alliance", "hub": "IST", "hubCity": "Istanbul", "country": "Turkey"},
    {"code": "TP", "name": "TAP Air Portugal", "alliance": "Star Alliance", "hub": "LIS", "hubCity": "Lisbon", "country": "Portugal"},
    {"code": "UA", "name": "United Airlines", "alliance": "Star Alliance", "hub": "ORD", "hubCity": "Chicago", "country": "United States"},
    {"code": "UL", "name": "SriLankan Airlines", "alliance": "Oneworld", "hub": "CMB", "hubCity": "Colombo", "country": "Sri Lanka"},
    {"code": "VN", "name": "Vietnam Airlines", "alliance": "SkyTeam", "hub": "SGN", "hubCity": "Ho Chi Minh City", "country": "Vietnam"},
    {"code": "VS", "name": "Virgin Atlantic", "alliance": "SkyTeam", "hub": "LHR", "hubCity": "London", "country": "United Kingdom"},
]

FLIGHT_SEED = [
    {
        "airportCode": "ICN",
        "airlineCode": "PR",
        "flightNumber": "467",
        "combinator": "ICNPR467",
        "terminal": "1",
        "departureTime": "09:30",
        "arrivalAirport": "MNL",
        "arrivalTime": "12:45",
        "duration": "3h 15m",
    },
    {
        "airportCode": "SIN",
        "airlineCode": "SQ",
        "flightNumber": "212",
        "combinator": "SINSQ212",
        "terminal": "3",
        "departureTime": "08:15",
        "arrivalAirport": "NRT",
        "arrivalTime": "16:05",
        "duration": "6h 50m",
    },
    {
        "airportCode": "LHR",
        "airlineCode": "BA",
        "flightNumber": "15",
        "combinator": "LHRBA15",
        "terminal": "5",
        "departureTime": "10:30",
        "arrivalAirport": "JFK",
        "arrivalTime": "13:15",
        "duration": "7h 45m",
    },
]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    write_json(OUT_DIR / "alliances.json", ALLIANCE_SEED)
    write_json(OUT_DIR / "flights.json", FLIGHT_SEED)
    write_json(OUT_DIR / "users.json", {"version": 1, "note": "User data persisted client-side via localStorage"})
    print(f"Generated Flight DB data in {OUT_DIR}")


if __name__ == "__main__":
    main()
