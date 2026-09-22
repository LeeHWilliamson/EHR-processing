import asyncio

from webapp.app.endpoints import faqs, home, tutorial


def test_public_pages_are_available_with_shared_navigation() -> None:
    async def check_pages() -> None:
        for endpoint, title in (
            (home, "Synth-EHR"),
            (tutorial, "Synth-EHR Guided Tutorial"),
            (faqs, "FAQs · Synth-EHR"),
        ):
            response = await endpoint()
            markup = response.path.read_text(encoding="utf-8")
            assert f"<title>{title}</title>" in markup
            assert 'href="/tutorial"' in markup
            assert 'href="/faqs"' in markup

    asyncio.run(check_pages())
