from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.chat import _sanitize_unsupported_contact_details


def test_removes_invented_support_channel():
    answer = (
        "\u041e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0439 \u043e\u0442\u0434\u0435\u043b: "
        "IT-\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430 \u0438 \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e\u0441\u0442\u044c.\n\n"
        "\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433: "
        "\u0441\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u0437\u0430\u044f\u0432\u043a\u0443 "
        "\u0432 \u0441\u0438\u0441\u0442\u0435\u043c\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0438."
    )

    context = (
        "\u041a\u0443\u0434\u0430 \u043e\u0431\u0440\u0430\u0449\u0430\u0442\u044c: "
        "IT-\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430 \u0438 \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e\u0441\u0442\u044c"
    )

    result = _sanitize_unsupported_contact_details(answer, context)

    assert "\u0441\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u0437\u0430\u044f\u0432\u043a\u0443" not in result.lower()
    assert "IT-" in result
    assert "\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433:" in result



def test_removes_unsupported_vpn_troubleshooting():
    from backend.app.services.chat import _sanitize_unsupported_contact_details

    answer = (
        "\u041f\u0435\u0440\u0435\u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 "
        "\u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e.\n"
        "\u041f\u043e\u0432\u0442\u043e\u0440\u043d\u043e "
        "\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0435\u0441\u044c "
        "\u043a VPN.\n"
        "\u041e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0439: "
        "IT-\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430 "
        "\u0438 \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e\u0441\u0442\u044c"
    )

    context = (
        "\u0415\u0441\u043b\u0438 VPN \u043d\u0435 "
        "\u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442, "
        "\u043e\u0431\u0440\u0430\u0442\u0438\u0442\u0435\u0441\u044c "
        "\u0432 IT-\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443 "
        "\u0438 \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e\u0441\u0442\u044c."
    )

    result = _sanitize_unsupported_contact_details(
        answer,
        context
    ).lower()

    assert "\u043f\u0435\u0440\u0435\u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435" not in result
    assert "\u043f\u043e\u0432\u0442\u043e\u0440\u043d\u043e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u0435\u0441\u044c" not in result
    assert "it-" in result


def test_keeps_supported_restart_instruction():
    from backend.app.services.chat import _sanitize_unsupported_contact_details

    answer = (
        "\u041f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 "
        "\u043a\u043b\u0438\u0435\u043d\u0442 VPN."
    )

    context = (
        "\u041f\u0440\u0438 \u044d\u0442\u043e\u0439 "
        "\u043e\u0448\u0438\u0431\u043a\u0435 "
        "\u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 "
        "\u043a\u043b\u0438\u0435\u043d\u0442 VPN."
    )

    result = _sanitize_unsupported_contact_details(
        answer,
        context
    )

    assert (
        "\u041f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435"
        in result
    )



def test_normalize_single_surviving_numbered_step():
    from backend.app.services.chat import _normalize_numbered_steps

    value = (
        "Intro\n\n"
        "3. Contact IT support\n\n"
        "Next"
    )

    result = _normalize_numbered_steps(value)

    assert "3. Contact IT support" not in result
    assert "Contact IT support" in result


def test_normalize_numbered_sequence():
    from backend.app.services.chat import _normalize_numbered_steps

    value = (
        "2. First surviving item\n"
        "5. Second surviving item"
    )

    result = _normalize_numbered_steps(value)

    assert "1. First surviving item" in result
    assert "2. Second surviving item" in result
    assert "5. Second surviving item" not in result
