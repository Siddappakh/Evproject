import csv
import io

import pytest
from fastapi.testclient import TestClient

from backend.app import database, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "carbon.sqlite3")
    with TestClient(main.app) as test_client:
        response = test_client.post(
            "/api/auth/register",
            json={
                "full_name": "Test Administrator",
                "email": "test@example.com",
                "password": "test-password-123",
                "account_type": "college",
                "workspace_name": "Demo campus",
                "location": "India",
            },
        )
        assert response.status_code == 201
        csrf = test_client.cookies.get(main.CSRF_COOKIE_NAME)
        if csrf:
            test_client.headers["X-CSRF-Token"] = csrf
        yield test_client


def create_workspace(client):
    response = client.put(
        "/api/workspace",
        json={"name": "Demo campus", "account_type": "college", "region": "India"},
    )
    assert response.status_code == 200
    return response.json()


def create_factor(client, category="electricity", unit="kgCO2e/kWh", value=0.8, gas_basis=None):
    payload = {
        "category": category,
        "name": "Reviewed grid factor",
        "value": value,
        "unit": unit,
        "source_name": "Official factor publication",
        "source_url": "https://example.org/factors",
        "factor_year": 2025,
        "region": "India",
        "assumptions": "Use for grid electricity only.",
    }
    if gas_basis:
        payload["gas_basis"] = gas_basis
    return client.post(
        "/api/factors",
        json=payload,
    )


def test_activity_uses_matching_factor_and_dashboard_aggregates(client):
    create_workspace(client)
    factor = create_factor(client)
    assert factor.status_code == 201
    activity = client.post(
        "/api/activities",
        json={
            "category": "electricity",
            "description": "Campus electricity",
            "quantity": 100,
            "unit": "kWh",
            "period": "2026-10",
            "reporting_unit": "Library",
            "factor_id": factor.json()["id"],
        },
    )

    assert activity.status_code == 201
    assert activity.json()["emissions_kg"] == pytest.approx(80)
    dashboard = client.get("/api/dashboard?period=2026-10").json()
    assert dashboard["total_kg"] == pytest.approx(80)
    assert dashboard["activity_count"] == 1
    assert dashboard["categories"] == [{"category": "electricity", "emissions_kg": 80}]
    assert dashboard["contributors"][0]["reporting_unit"] == "Library"
    assert dashboard["trend"] == [{"period": "2026-10", "emissions_kg": 80}]


def test_carbon_explanation_is_grounded_in_saved_data(client):
    create_workspace(client)
    factor = create_factor(client).json()
    client.post("/api/activities", json={
        "category": "electricity", "description": "Office electricity",
        "quantity": 100, "unit": "kWh", "period": "2026-10",
        "activity_date": "2026-10-05", "factor_id": factor["id"],
    })
    explanation = client.get("/api/carbon-explanation?period=2026-10")
    assert explanation.status_code == 200
    body = explanation.json()
    assert body["monthly_total_kg"] == 80
    assert body["daily"] == [{"activity_date": "2026-10-05", "emissions_kg": 80.0}]
    assert body["ai_generated"] is False
    assert "80.0 kg CO2e" in body["explanation"] or "80 kg CO2e" in body["explanation"]


def test_daily_totals_sum_to_monthly_total(client):
    create_workspace(client)
    factor = create_factor(client).json()
    for activity_date, quantity in [("2026-10-03", 25), ("2026-10-18", 75)]:
        response = client.post("/api/activities", json={
            "category": "electricity",
            "description": "Meter reading",
            "quantity": quantity,
            "unit": "kWh",
            "period": "2026-10",
            "activity_date": activity_date,
            "factor_id": factor["id"],
        })
        assert response.status_code == 201
    dashboard = client.get("/api/dashboard?period=2026-10")
    assert dashboard.status_code == 200
    assert dashboard.json()["total_kg"] == pytest.approx(80)
    assert dashboard.json()["daily"] == [
        {"activity_date": "2026-10-03", "emissions_kg": 20.0},
        {"activity_date": "2026-10-18", "emissions_kg": 60.0},
    ]


@pytest.mark.parametrize(
    ("category", "quantity", "unit", "factor_unit", "factor_value", "expected"),
    [
        ("electricity", 100, "kWh", "kgCO2e/kWh", 0.8, 80),
        ("transport", 20, "km", "kgCO2e/km", 0.12, 2.4),
        ("fuel", 5, "L", "kgCO2e/L", 2.68, 13.4),
        ("waste", 2, "kg", "kgCO2e/kg", 0.5, 1),
    ],
)
def test_supported_activity_scenarios(client, category, quantity, unit, factor_unit, factor_value, expected):
    create_workspace(client)
    factor = create_factor(client, category, factor_unit, factor_value).json()
    response = client.post("/api/activities", json={
        "category": category,
        "description": f"{category.title()} test activity",
        "quantity": quantity,
        "unit": unit,
        "period": "2026-10",
        "activity_date": "2026-10-28",
        "factor_id": factor["id"],
    })
    assert response.status_code == 201
    assert response.json()["emissions_kg"] == pytest.approx(expected)

    dashboard = client.get("/api/dashboard?period=2026-10")
    assert dashboard.status_code == 200
    assert dashboard.json()["total_kg"] == pytest.approx(expected)
    assert dashboard.json()["categories"] == [{"category": category, "emissions_kg": expected}]


@pytest.mark.parametrize("quantity", [0, -1])
def test_invalid_activity_quantities_are_rejected(client, quantity):
    create_workspace(client)
    factor = create_factor(client).json()
    response = client.post(
        "/api/activities",
        json={
            "category": "electricity",
            "description": "Invalid quantity",
            "quantity": quantity,
            "unit": "kWh",
            "period": "2026-10",
            "activity_date": "2026-10-28",
            "factor_id": factor["id"],
        },
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_nonfinite_activity_quantity_is_rejected(client):
    create_workspace(client)
    factor = create_factor(client).json()
    response = client.post(
        "/api/activities",
        content=(
            '{"category":"electricity","description":"Invalid quantity","quantity":Infinity,'
            '"unit":"kWh","period":"2026-10","activity_date":"2026-10-28","factor_id":"'
            + factor["id"] + '"}'
        ),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_activity_date_is_valid_and_matches_period(client):
    create_workspace(client)
    factor = create_factor(client).json()
    invalid_dates = ["2026-02-31", "2026-11-28"]
    for activity_date in invalid_dates:
        response = client.post("/api/activities", json={
            "category": "electricity",
            "description": "Date validation test",
            "quantity": 1,
            "unit": "kWh",
            "period": "2026-10",
            "activity_date": activity_date,
            "factor_id": factor["id"],
        })
        assert response.status_code == 422


def test_category_totals_match_saved_activity_sum(client):
    create_workspace(client)
    scenarios = [
        ("electricity", 100, "kWh", "kgCO2e/kWh", 0.8),
        ("transport", 20, "km", "kgCO2e/km", 0.12),
        ("fuel", 5, "L", "kgCO2e/L", 2.68),
        ("waste", 2, "kg", "kgCO2e/kg", 0.5),
    ]
    expected = {}
    for category, quantity, unit, factor_unit, factor_value in scenarios:
        factor = create_factor(client, category, factor_unit, factor_value).json()
        response = client.post("/api/activities", json={
            "category": category,
            "description": f"{category.title()} combined test",
            "quantity": quantity,
            "unit": unit,
            "period": "2026-10",
            "activity_date": "2026-10-28",
            "factor_id": factor["id"],
        })
        assert response.status_code == 201
        expected[category] = pytest.approx(quantity * factor_value)

    dashboard = client.get("/api/dashboard?period=2026-10")
    assert dashboard.status_code == 200
    category_totals = {row["category"]: row["emissions_kg"] for row in dashboard.json()["categories"]}
    assert category_totals["electricity"] == pytest.approx(expected["electricity"])
    assert category_totals["transport"] == pytest.approx(expected["transport"])
    assert category_totals["fuel"] == pytest.approx(expected["fuel"])
    assert category_totals["waste"] == pytest.approx(expected["waste"])
    assert dashboard.json()["total_kg"] == pytest.approx(sum(quantity * value for _, quantity, _, _, value in scenarios))


def test_activity_rejects_mismatched_category_and_incompatible_unit(client):
    create_workspace(client)
    factor = create_factor(client)
    base = {
        "category": "fuel",
        "description": "Diesel use",
        "quantity": 10,
        "unit": "L",
        "period": "2026-10",
        "factor_id": factor.json()["id"],
    }

    assert client.post("/api/activities", json=base).status_code == 422
    base["category"] = "electricity"
    assert client.post("/api/activities", json=base).status_code == 422


def test_dashboard_comparison_target_recommendations_and_csv(client):
    create_workspace(client)
    factor = create_factor(client, "fuel", "kgCO2e/L", 2.5).json()
    for period, quantity in [("2026-09", 20), ("2026-10", 10)]:
        response = client.post(
            "/api/activities",
            json={
                "category": "fuel",
                "description": "Generator fuel",
                "quantity": quantity,
                "unit": "L",
                "period": period,
                "factor_id": factor["id"],
            },
        )
        assert response.status_code == 201

    assert client.put("/api/targets", json={"monthly_target_kg": 40}).json() == {
        "monthly_target_kg": 40
    }
    dashboard = client.get("/api/dashboard?period=2026-10").json()
    assert dashboard["previous_total_kg"] == pytest.approx(50)
    assert dashboard["monthly_target_kg"] == 40
    assert dashboard["trend"] == [
        {"period": "2026-09", "emissions_kg": 50},
        {"period": "2026-10", "emissions_kg": 25},
    ]
    suggestion = client.get("/api/recommendations?period=2026-10").json()[0]
    assert suggestion["category"] == "fuel"
    assert suggestion["estimated_savings_kg"] == pytest.approx(2.5)
    assert "not a measured" in suggestion["savings_note"]

    report = client.get("/api/reports.csv?period=2026-10")
    rows = list(csv.reader(io.StringIO(report.text)))
    assert report.status_code == 200
    assert ["Account type", "college"] in rows
    header = rows.index(["Period", "Category", "Activity", "Reporting unit", "Quantity", "Unit",
                         "Emissions (kg)", "Gas basis", "Factor name", "Factor value",
                         "Factor unit", "Factor year", "Factor region", "Factor classification",
                         "Source classification", "Factor selection status", "Factor source",
                         "Source publication/version", "Factor source URL",
                         "Methodology", "Assumptions"])
    assert rows[header + 1][0] == "2026-10"
    assert rows[header + 1][6] == "25.0"
    assert rows[header + 1][16] == "Official factor publication"


def test_factor_requires_source_and_workspace(client):
    payload = {
        "category": "waste",
        "name": "Waste factor",
        "value": 1.2,
        "unit": "kgCO2e/kg",
        "source_name": "Reference",
        "source_url": "javascript:alert(1)",
        "factor_year": 2025,
        "region": "India",
    }
    assert client.post("/api/factors", json=payload).status_code == 422
    payload["source_url"] = "https://example.org"
    assert client.post("/api/factors", json=payload).status_code == 409


def test_non_finite_factors_are_rejected(client):
    create_workspace(client)
    response = client.post(
        "/api/factors",
        content='{"category":"electricity","name":"Invalid factor","value":NaN,'
        '"unit":"kgCO2e/kWh","source_name":"Reference",'
        '"source_url":"https://example.org","factor_year":2025,"region":"India"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_account_workspace_data_is_isolated(client):
    create_workspace(client)
    factor = create_factor(client).json()
    created = client.post("/api/activities", json={
        "category": "electricity", "description": "Private first account activity",
        "quantity": 10, "unit": "kWh", "period": "2026-10", "factor_id": factor["id"],
    })
    assert created.status_code == 201

    client.post("/api/auth/logout", json={})
    registered = client.post("/api/auth/register", json={
        "full_name": "Second Account Administrator",
        "email": "second@example.com",
        "password": "second-password-123",
        "account_type": "organization",
        "workspace_name": "Second Organization",
    })
    assert registered.status_code == 201
    csrf = client.cookies.get(main.CSRF_COOKIE_NAME)
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    configured = client.put("/api/workspace", json={
        "name": "Second Organization", "account_type": "organization", "region": "India"
    })
    assert configured.status_code == 200
    assert client.get("/api/activities?period=2026-10").json() == []
    assert client.get("/api/dashboard?period=2026-10").json()["total_kg"] == 0
    assert client.get("/api/factors").json() == []


def test_csv_escapes_spreadsheet_formula_text(client):
    create_workspace(client)
    factor = create_factor(client).json()
    activity = client.post(
        "/api/activities",
        json={
            "category": "electricity",
            "description": "=HYPERLINK(\"https://example.org\")",
            "quantity": 1,
            "unit": "kWh",
            "period": "2026-10",
            "factor_id": factor["id"],
        },
    )
    assert activity.status_code == 201
    response = client.get("/api/reports.csv?period=2026-10")
    rows = list(csv.reader(io.StringIO(response.text)))
    header = rows.index(["Period", "Category", "Activity", "Reporting unit", "Quantity", "Unit",
                         "Emissions (kg)", "Gas basis", "Factor name", "Factor value",
                         "Factor unit", "Factor year", "Factor region", "Factor classification",
                         "Source classification", "Factor selection status", "Factor source",
                         "Source publication/version", "Factor source URL",
                         "Methodology", "Assumptions"])
    assert rows[header + 1][2].startswith("'=")


def test_electricity_factor_is_selected_by_fiscal_year_and_proxy_is_labelled(client):
    create_workspace(client)
    seeded = client.post("/api/factors/seed")
    assert seeded.status_code == 201
    assert seeded.json()["seeded_factors_count"] >= 16

    fy_2024 = client.post("/api/activities", json={
        "category": "electricity",
        "description": "FY 2024-25 electricity",
        "quantity": 100,
        "unit": "kWh",
        "period": "2024-06",
        "activity_date": "2024-06-15",
    })
    fy_2025 = client.post("/api/activities", json={
        "category": "electricity",
        "description": "FY 2025-26 electricity",
        "quantity": 100,
        "unit": "kWh",
        "period": "2025-06",
        "activity_date": "2025-06-15",
    })
    fy_2026_proxy = client.post("/api/activities", json={
        "category": "electricity",
        "description": "FY 2026-27 electricity proxy",
        "quantity": 100,
        "unit": "kWh",
        "period": "2026-10",
        "activity_date": "2026-10-15",
    })

    assert fy_2024.json()["factor_value"] == pytest.approx(0.710)
    assert fy_2024.json()["emissions_kg"] == pytest.approx(71)
    assert fy_2024.json()["factor_gas_basis"] == "CO2"
    assert fy_2025.json()["factor_value"] == pytest.approx(0.675)
    assert fy_2025.json()["emissions_kg"] == pytest.approx(67.5)
    assert fy_2025.json()["factor_classification"] == "official"
    assert fy_2026_proxy.json()["factor_value"] == pytest.approx(0.675)
    assert fy_2026_proxy.json()["factor_classification"] == "proxy"
    assert fy_2026_proxy.json()["factor_source_classification"] == "official"
    assert fy_2026_proxy.json()["factor_selection_status"] == "proxy"


def test_stale_client_factor_id_cannot_bypass_date_selection(client):
    create_workspace(client)
    seeded = client.post("/api/factors/seed")
    assert seeded.status_code == 201
    factors = client.get("/api/factors?category=electricity").json()
    stale = next(factor for factor in factors if factor["factor_year"] == 2025)

    activity = client.post("/api/activities", json={
        "category": "electricity",
        "description": "Stale factor selection",
        "quantity": 83,
        "unit": "kWh",
        "period": "2026-11",
        "activity_date": "2026-11-17",
        "factor_id": stale["id"],
    })

    assert activity.status_code == 201
    body = activity.json()
    assert body["factor_value"] == pytest.approx(0.675)
    assert body["factor_classification"] == "proxy"
    assert body["factor_source_classification"] == "official"
    assert body["emissions_kg"] == pytest.approx(56.025)


def test_future_electricity_factor_is_not_selected(client):
    create_workspace(client)
    client.post("/api/factors/seed")
    activity = client.post("/api/activities", json={
        "category": "electricity",
        "description": "Before published factors",
        "quantity": 83,
        "unit": "kWh",
        "period": "2023-11",
        "activity_date": "2023-11-17",
    })

    assert activity.status_code == 201
    body = activity.json()
    assert body["factor_name"] == "No verified emission factor"
    assert body["emissions_kg"] == 0


def test_dashboard_reports_gas_basis_and_aggregates_all_activities(client):
    create_workspace(client)
    factor = create_factor(client, unit="kgCO2/kWh", value=0.71, gas_basis="CO2").json()
    first = client.post("/api/activities", json={
        "category": "electricity", "description": "CO2 activity", "quantity": 83,
        "unit": "kWh", "period": "2026-10", "factor_id": factor["id"],
    })
    second = client.post("/api/activities", json={
        "category": "electricity", "description": "CO2 activity two", "quantity": 100,
        "unit": "kWh", "period": "2026-10", "factor_id": factor["id"],
    })
    assert first.status_code == 201
    assert second.status_code == 201
    dashboard = client.get("/api/dashboard?period=2026-10").json()
    assert dashboard["total_kg"] == pytest.approx(129.93)
    assert dashboard["activity_count"] == 2
    assert dashboard["gas_basis"] == "CO2"


def test_passenger_km_and_vehicle_km_use_distinct_units(client):
    create_workspace(client)
    vehicle = create_factor(client, "transport", "kgCO2e/vehicle-km", 0.2).json()
    passenger = create_factor(client, "transport", "kgCO2e/passenger-km", 0.08).json()

    vehicle_activity = client.post("/api/activities", json={
        "category": "transport", "description": "Vehicle distance", "quantity": 10,
        "unit": "vehicle-km", "period": "2026-10", "factor_id": vehicle["id"],
    })
    passenger_activity = client.post("/api/activities", json={
        "category": "transport", "description": "Passenger distance", "quantity": 10,
        "unit": "passenger-km", "period": "2026-10", "factor_id": passenger["id"],
    })

    assert vehicle_activity.status_code == 201
    assert vehicle_activity.json()["emissions_kg"] == pytest.approx(2)
    assert passenger_activity.status_code == 201
    assert passenger_activity.json()["emissions_kg"] == pytest.approx(0.8)


def test_water_factor_has_water_category_and_provenance(client):
    create_workspace(client)
    factor = client.post("/api/factors", json={
        "category": "water",
        "name": "Regional municipal water",
        "value": 0.000344,
        "unit": "kgCO2e/L",
        "gas_basis": "CO2e",
        "source_name": "Water methodology",
        "source_url": "https://example.org/water",
        "source_publication": "Water factors 2025, Table 2",
        "methodology": "Treatment and distribution boundary.",
        "factor_year": 2025,
        "region": "India",
        "classification": "estimated",
        "assumptions": "Regional estimate.",
    })
    assert factor.status_code == 201
    saved = factor.json()
    assert saved["category"] == "water"
    assert saved["source_publication"] == "Water factors 2025, Table 2"
    activity = client.post("/api/activities", json={
        "category": "water", "description": "Municipal water", "quantity": 1000,
        "unit": "L", "period": "2026-10", "factor_id": saved["id"],
    })
    assert activity.status_code == 201
    assert activity.json()["emissions_kg"] == pytest.approx(0.344)


def test_water_migration_preserves_factor_ids_and_linked_activity(client):
    workspace = create_workspace(client)
    seeded = client.post("/api/factors/seed")
    assert seeded.status_code == 201
    workspace_id = workspace["id"]
    with database.connect() as connection:
        factor = connection.execute(
            """
            SELECT * FROM emission_factors
            WHERE workspace_id = ? AND name = 'Municipal Water Supply'
            """,
            (workspace_id,),
        ).fetchone()
        assert factor is not None
        factor_id = factor["id"]
        connection.execute(
            "UPDATE emission_factors SET category = 'waste' WHERE id = ?",
            (factor_id,),
        )
    activity = database.save_activity(
        workspace_id=workspace_id,
        category="waste",
        description="Historical water record",
        quantity=1000,
        unit="L",
        period="2026-10",
        activity_date="2026-10-15",
        reporting_unit="Campus",
        factor=dict(factor),
        emissions_kg=0.344,
    )

    database.initialize_database()

    with database.connect() as connection:
        migrated_factor = connection.execute(
            "SELECT category FROM emission_factors WHERE id = ?", (factor_id,)
        ).fetchone()
        linked_activity = connection.execute(
            "SELECT factor_id, category, emissions_kg FROM activities WHERE id = ?",
            (activity["id"],),
        ).fetchone()
    assert migrated_factor["category"] == "water"
    assert linked_activity["factor_id"] == factor_id
    assert linked_activity["category"] == "waste"
    assert linked_activity["emissions_kg"] == pytest.approx(0.344)
    assert database.initialize_database() is None


def test_legacy_electricity_factor_is_excluded_from_new_selection(client):
    workspace = create_workspace(client)
    client.post("/api/factors/seed")
    workspace_id = workspace["id"]
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO emission_factors (
                id, workspace_id, category, name, value, unit, gas_basis,
                source_name, source_url, factor_year, region, assumptions,
                classification
            ) VALUES (?, ?, 'electricity', ?, 0.710, 'kgCO2e/kWh', 'CO2e',
                      'Central Electricity Authority', 'https://cea.nic.in',
                      2024, 'India', 'Preserved legacy factor', 'unverified')
            """,
            (
                "legacy-electricity-factor",
                workspace_id,
                "CEA National Grid Electricity Baseline",
            ),
        )

    selected = database.get_applicable_factor(
        workspace_id, "electricity", "kWh", "2023-06-15"
    )
    assert selected is None
    response = client.post("/api/activities", json={
        "category": "electricity",
        "description": "Legacy factor attempt",
        "quantity": 10,
        "unit": "kWh",
        "period": "2026-10",
        "factor_id": "legacy-electricity-factor",
    })
    assert response.status_code == 422


def test_official_factor_requires_publication_provenance(client):
    create_workspace(client)
    response = client.post("/api/factors", json={
        "category": "electricity",
        "name": "Unproven official factor",
        "value": 0.7,
        "unit": "kgCO2/kWh",
        "gas_basis": "CO2",
        "source_name": "CEA",
        "source_url": "https://cea.nic.in",
        "factor_year": 2026,
        "region": "India",
        "classification": "official",
    })
    assert response.status_code == 422
    assert "publication" in response.json()["detail"]


def test_existing_activity_snapshot_survives_reinitialization(client):
    create_workspace(client)
    factor = create_factor(client).json()
    created = client.post("/api/activities", json={
        "category": "electricity", "description": "Historical reading", "quantity": 10,
        "unit": "kWh", "period": "2026-10", "factor_id": factor["id"],
    }).json()

    database.initialize_database()

    activities = client.get("/api/activities?period=2026-10").json()
    assert len(activities) == 1
    assert activities[0]["id"] == created["id"]
    assert activities[0]["emissions_kg"] == created["emissions_kg"]
    assert activities[0]["factor_id"] == created["factor_id"]
