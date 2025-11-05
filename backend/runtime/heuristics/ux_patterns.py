"""
UX Pattern Library - Context-Aware Planner Heuristics (Week 5)

Small, declarative rulebook for auto-adding scope, waits, and readiness checks
to common UX patterns (App Launcher, modals, Lightning hydration).

No heavy logic. Just pattern matching and step enrichment.
"""

# Week 5: UX Pattern Rules (declarative, lightweight)
UX_PATTERNS = [
    # Salesforce App Launcher - Scoped Search
    {
        "id": "salesforce_app_launcher_scope",
        "when": {"contains_text": "App Launcher"},
        "adds": {
            "within": "App Launcher",
            "wait": "dialog",
            "post_wait_ms": 1500,
        },
    },

    # Click item in App Launcher search results
    {
        "id": "salesforce_click_in_launcher",
        "when": {
            "action": "click",
            "prev_step_has": "App Launcher",
        },
        "adds": {
            "within": "App Launcher",
            "wait": "navigation",
        },
    },

    # Salesforce Lightning "New" button on list views
    {
        "id": "salesforce_lightning_new_on_list",
        "when": {
            "action": "click",
            "target_lower": "new",
            "url_includes": "/lightning/o/",
        },
        "adds": {
            "wait_for_gate": True,
            "post_wait_ms": 1500,
        },
    },

    # Generic modal/dialog scoping
    {
        "id": "dialog_scope_default",
        "when": {"modal_open": True},
        "adds": {"within": "active_dialog"},
    },
]
