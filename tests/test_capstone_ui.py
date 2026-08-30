"""Opt-in browser regression tests against the real, authenticated local API."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

import pytest

pw = pytest.importorskip("playwright.sync_api")
pytestmark = [
    pytest.mark.ui,
    pytest.mark.skipif(os.getenv("ASTERIA_UI_TESTS") != "1", reason="Opt-in browser suite"),
]
ROOT = Path(__file__).resolve().parents[1]
TOKEN = "asteria-browser-test-only"
QUESTION = "Quelle est la franchise pour un degat des eaux ?"


@pytest.fixture(scope="module")
def server_url():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "ASTERIA_API_TOKEN": TOKEN, "LANGSMITH_TRACING": "false"}
    env.pop("OPENAI_API_KEY", None)
    env.pop("LANGSMITH_API_KEY", None)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api:app",
            "--app-dir",
            "projects/07-asteria-investigation-platform",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))
    try:
        for _ in range(200):
            if process.poll() is not None:
                pytest.fail("The UI test server exited before becoming healthy")
            try:
                with opener.open(url + "/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                time.sleep(0.1)
        else:
            pytest.fail("The UI test server did not become healthy")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as playwright:
        executable = os.getenv("ASTERIA_CHROMIUM_EXECUTABLE")
        instance = playwright.chromium.launch(
            headless=True,
            executable_path=executable or None,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        yield instance
        instance.close()


@pytest.fixture
def page(browser, server_url):
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000}, locale="fr-FR", reduced_motion="reduce"
    )
    context.add_init_script(f"sessionStorage.setItem('asteria_api_token', {json.dumps(TOKEN)});")
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server_url)
    pw.expect(page.locator("#system-label")).to_have_text("Connect\u00e9")
    yield page
    context.close()
    assert errors == [], errors


def capture(page, name: str) -> None:
    target = os.getenv("ASTERIA_UI_SCREENSHOTS")
    if target:
        directory = Path(target)
        directory.mkdir(parents=True, exist_ok=True)
        page.evaluate("document.fonts.ready")
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        page.screenshot(
            path=str(directory / f"{name}.png"),
            full_page=True,
            style=".toast { visibility: hidden; }",
        )


def ask(page, question: str = QUESTION) -> None:
    page.locator("#question-input").fill(question)
    page.locator("#run-button").click()
    pw.expect(page.locator("#result-panel")).to_be_visible()
    pw.expect(page.locator("#run-button")).to_be_enabled()


def assert_no_page_overflow(page) -> None:
    sizes = page.evaluate("""() => ({
        actual: document.documentElement.scrollWidth,
        expected: document.documentElement.clientWidth,
        outside: [...document.querySelectorAll('body *')].filter(el => {
            const r = el.getBoundingClientRect();
            return r.width && (r.left < -1 || r.right > innerWidth + 1);
        }).map(el => el.tagName + '#' + el.id + '.' + el.className).slice(0, 20)
    })""")
    assert sizes["actual"] <= sizes["expected"], sizes


@pytest.mark.parametrize("width", [320, 390, 768, 1024, 1440])
def test_responsive_views_and_real_results(page, width: int) -> None:
    page.set_viewport_size({"width": width, "height": 950})
    pw.expect(page.locator("#assistant-heading")).to_be_visible()
    assert int(page.locator("#corpus-count").inner_text()) >= 10
    assert_no_page_overflow(page)
    capture(page, f"assistant-{width}")
    page.locator(".case-button").first.click()
    page.locator("#run-button").click()
    pw.expect(page.locator("#result-panel")).to_be_visible()
    pw.expect(page.locator("#answer-text")).to_contain_text("180")
    assert_no_page_overflow(page)
    capture(page, f"answer-{width}")
    page.locator('.nav-tab[data-view="scenarios"]').click()
    page.locator("#evaluate-button").click()
    pw.expect(page.locator("#pass-rate")).to_contain_text("100")
    pw.expect(page.locator("#scenario-failed")).to_have_text("0")
    capture(page, f"validations-{width}")
    assert_no_page_overflow(page)
    page.locator('.nav-tab[data-view="architecture"]').click()
    pw.expect(page.locator("#readiness-score")).to_contain_text("100")
    assert_no_page_overflow(page)
    capture(page, f"platform-{width}")


@pytest.mark.parametrize(
    ("question", "engine", "status"),
    [
        (QUESTION, "RAG", "Analyse termin\u00e9e"),
        (
            "Quelles pieces et justificatifs faut-il fournir pour un degat des eaux ?",
            "LangGraph",
            "Analyse termin\u00e9e",
        ),
        (
            "Un score automatique peut-il prouver une fraude et refuser le dossier ?",
            "Deep Agent",
            "Revue humaine requise",
        ),
        (
            "Quel remboursement existe pour une couronne dentaire ?",
            "RAG",
            "Revue humaine requise",
        ),
    ],
)
def test_auto_routing_and_human_review(page, question: str, engine: str, status: str) -> None:
    ask(page, question)
    pw.expect(page.locator("#engine-value")).to_have_text(engine)
    pw.expect(page.locator("#result-status")).to_have_text(status)


def test_sources_keyboard_tabs_history_copy_and_download(page, tmp_path: Path) -> None:
    ask(page)
    original = page.locator("#answer-text").inner_text()
    page.locator("#tab-evidence").focus()
    page.keyboard.press("ArrowRight")
    pw.expect(page.locator("#tab-tasks")).to_be_focused()
    pw.expect(page.locator("#panel-tasks")).to_be_visible()
    page.keyboard.press("End")
    pw.expect(page.locator("#tab-checks")).to_have_attribute("aria-selected", "true")
    page.locator(".citation-chip").last.click()
    pw.expect(page.locator("#panel-evidence")).to_be_visible()
    assert page.locator(".evidence-item[open]").count() >= 1
    page.evaluate("navigator.clipboard.writeText = async text => { window.copiedAnswer = text; };")
    page.locator("#copy-result").click()
    assert original in page.evaluate("window.copiedAnswer")
    with page.expect_download() as download:
        page.locator("#download-result").click()
    target = tmp_path / "report.txt"
    download.value.save_as(target)
    report = target.read_text(encoding="utf-8")
    assert original in report
    assert "SOURCES" in report
    assert TOKEN not in report
    page.locator("#new-question").click()
    pw.expect(page.locator("#question-input")).to_have_value("")
    pw.expect(page.locator("#result-panel")).to_be_hidden()
    page.locator("#history-list button").first.click()
    pw.expect(page.locator("#answer-text")).to_have_text(original)


def test_authentication_clear_save_and_escape_do_not_replay_action(page) -> None:
    page.locator("#access-button").click()
    page.get_by_role("button", name="Effacer le jeton").click()
    page.locator("#question-input").fill(QUESTION)
    page.locator("#run-button").click()
    pw.expect(page.locator("#access-dialog")).to_be_visible()
    pw.expect(page.locator("#request-error")).to_contain_text("Acc\u00e8s prot\u00e9g\u00e9")
    page.locator("#token-input").fill(TOKEN)
    page.get_by_role("button", name="Enregistrer", exact=True).click()
    page.locator("#access-button").click()
    page.locator("#token-input").fill("not-saved")
    page.keyboard.press("Escape")
    assert page.evaluate("sessionStorage.getItem('asteria_api_token')") == TOKEN
    ask(page)


def test_loading_prevents_duplicate_requests_and_hides_stale_results(page) -> None:
    ask(page)
    requests = []

    def delayed_response(route):
        requests.append(route.request)
        response = route.fetch()
        page.wait_for_timeout(150)
        pw.expect(page.locator("#run-button")).to_be_disabled()
        pw.expect(page.locator("#loading-state")).to_be_visible()
        pw.expect(page.locator("#result-panel")).to_be_hidden()
        page.locator("#investigation-form").evaluate(
            "form => form.dispatchEvent(new Event('submit', {cancelable: true}))"
        )
        route.fulfill(response=response)

    page.route("**/api/v1/investigations", delayed_response)
    ask(page)
    assert len(requests) == 1


@pytest.mark.parametrize("status", [429, 500])
def test_request_errors_keep_question_and_allow_retry(page, status: int) -> None:
    page.route(
        "**/api/v1/investigations",
        lambda route: route.fulfill(status=status, json={"detail": "internal error"}),
    )
    page.locator("#question-input").fill(QUESTION)
    page.locator("#run-button").click()
    pw.expect(page.locator("#request-error")).to_be_visible()
    pw.expect(page.locator("#question-input")).to_have_value(QUESTION)
    pw.expect(page.locator("#run-button")).to_be_enabled()
    pw.expect(page.locator("#result-panel")).to_be_hidden()
    page.unroute("**/api/v1/investigations")
    ask(page)
    pw.expect(page.locator("#request-error")).to_be_hidden()


def test_offline_bootstrap_retry_and_failed_evaluation_clear_old_results(page) -> None:
    page.route("**/api/v1/platform", lambda route: route.abort())
    page.reload()
    pw.expect(page.locator("#connection-error")).to_be_visible()
    page.unroute("**/api/v1/platform")
    page.locator("#reconnect-button").click()
    pw.expect(page.locator("#connection-error")).to_be_hidden()
    page.locator('.nav-tab[data-view="scenarios"]').click()
    page.locator("#evaluate-button").click()
    pw.expect(page.locator("#pass-rate")).to_contain_text("100")
    page.route(
        "**/api/v1/evaluations",
        lambda route: route.fulfill(status=500, json={"detail": "failed"}),
    )
    page.locator("#evaluate-button").click()
    pw.expect(page.locator("#evaluation-error")).to_be_visible()
    pw.expect(page.locator("#pass-rate")).to_have_text("--")
    assert page.locator(".table-status.is-pass").count() == 0


def test_untrusted_response_is_rendered_as_text(page) -> None:
    payload_text = '<img src=x onerror="window.injected=true">'

    def malicious_answer(route):
        response = route.fetch()
        data = response.json()
        data["answer"] = payload_text
        data["evidence"][0]["excerpt"] = payload_text
        route.fulfill(response=response, json=data)

    page.route("**/api/v1/investigations", malicious_answer)
    ask(page)
    pw.expect(page.locator("#answer-text")).to_have_text(payload_text)
    assert page.locator("#result-panel img").count() == 0
    assert page.evaluate("window.injected === undefined")


def test_mobile_history_and_session_privacy(page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("#history-button").click()
    pw.expect(page.locator("#history-dialog-empty")).to_be_visible()
    page.keyboard.press("Escape")
    ask(page)
    original = page.locator("#answer-text").inner_text()
    page.locator("#new-question").click()
    page.locator("#history-button").click()
    page.locator("#history-dialog-list button").first.click()
    pw.expect(page.locator("#history-dialog")).not_to_be_visible()
    pw.expect(page.locator("#answer-text")).to_have_text(original)
    page.reload()
    pw.expect(page.locator("#system-label")).to_have_text("Connect\u00e9")
    page.locator("#history-button").click()
    pw.expect(page.locator("#history-dialog-empty")).to_be_visible()
    assert page.locator("#history-dialog-list button").count() == 0


def test_explicit_mode_and_advanced_options_reach_api(page) -> None:
    page.locator("#mode-select").select_option("graph")
    page.locator("#advanced-options summary").click()
    page.locator("#review-toggle").uncheck()
    page.locator("#production-toggle").uncheck()
    page.locator("#question-input").fill(QUESTION)
    with page.expect_request("**/api/v1/investigations") as request:
        page.locator("#question-input").press("Control+Enter")
    payload = request.value.post_data_json
    assert payload["mode"] == "graph"
    assert payload["require_human_review_on_insufficient"] is False
    assert payload["enforce_production_gate"] is False
    pw.expect(page.locator("#engine-value")).to_have_text("LangGraph")
