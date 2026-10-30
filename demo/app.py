import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime

import brand
import dock
import gradio as gr
import guide
import mobile

from deadwax.agent import Answer, ask, tracing
from deadwax.agent.conversation import Exchange, remember
from deadwax.agent.evidence import HEADERS, Evidence, evidence, rows
from deadwax.agent.models import EVAL_MODEL
from deadwax.config import load_env_file
from deadwax.daily_cap import DailyCap
from deadwax.data import library
from deadwax.retrieval.citations import cited, source_lines

DAILY_QUESTIONS_VARIABLE = "DEADWAX_DEMO_DAILY_QUESTIONS"
DEFAULT_DAILY_QUESTIONS = 80
MAX_QUESTION_CHARS = 300
EARLIER_ANSWER_CHARS = 280
REPOSITORY = "https://github.com/TheDavidKoen/deadwax"

INTRO = f"""
Deadwax is an AI librarian for your music. Ask it about your collection in plain English, such
as how many tracks you have in a genre or what your longest song is, or ask it to build a
playlist to a brief. It answers by calling tools that search the library. The language model
only reads your question and writes the reply. Every count, total and playlist check is worked
out in plain Python, and each answer shows the tool calls behind it.

**This demo runs on a fixed library of 100 tracks**, the same data its evaluation suite is
graded against, so every answer here can be checked. Run Deadwax yourself and it connects to
**your own Spotify account** instead, so you can search your favourite tracks from the terminal
or from an AI assistant such as Claude Code. The guide at the bottom of the page shows how.

[Source code and evaluation results]({REPOSITORY}).
"""

PLACEHOLDER = "Ask a question, or pick one of the examples. The answer appears here."
NO_TRAIL = "The model and every tool call it made will be listed here."

EXAMPLES = [
    "How much krautrock is there?",
    "What's the longest Miles Davis track?",
    "Any folk from before 1975?",
    "Have I got any rap?",
    "How many tracks have I never played?",
    "30 minutes of ambient, no track over 8 minutes",
    "An hour of hip hop",
    "What is Burial's real name?",
]


@dataclass(frozen=True)
class Turn:
    reply: str
    trail: str = ""
    shown: Evidence | None = None
    exchange: Exchange | None = None


def today() -> date:
    return datetime.now(UTC).date()


def how_it_got_there(answer: Answer) -> str:
    calls = [f"{call['name']}({json.dumps(call['args'])})" for call in answer.tool_calls()]
    lines = [f"**Model:** `{answer.model}`", "", "**Tool calls:**"]
    lines += [f"1. `{call}`" for call in calls] if calls else ["none — answered without a tool"]
    return "\n".join(lines)


def with_sources(text: str, answer: Answer) -> str:
    lines = source_lines(cited(text), answer.passages())
    return "\n\n".join([text, "**Sources**", *lines]) if lines else text


def respond(question: str, cap: DailyCap, history: tuple[Exchange, ...]) -> Turn:
    question = question.strip()
    if not question:
        return Turn("Ask a question first.")
    if len(question) > MAX_QUESTION_CHARS:
        return Turn(f"Please keep questions under {MAX_QUESTION_CHARS} characters.")
    if not cap.take(today()):
        return Turn(
            "The demo has answered its daily quota of questions. It runs on a free tier, "
            "so it stops rather than fails. Please try again tomorrow."
        )

    try:
        answer = ask(question, trace_name="demo", history=history)
    except RuntimeError:
        return Turn("Every free-tier model is rate limited right now. Please try again shortly.")
    finally:
        tracing.flush()

    if not answer.converged:
        return Turn("The model call failed before an answer came back. Please try again.")
    text = answer.final_text()
    return Turn(
        reply=with_sources(text, answer),
        trail=how_it_got_there(answer),
        shown=evidence(answer.messages, library.tracks()),
        exchange=Exchange(question, text),
    )


def card(question: str, reply: str) -> str:
    return f"> {question}\n\n{reply}"


def shortened(text: str) -> str:
    return text if len(text) <= EARLIER_ANSWER_CHARS else text[:EARLIER_ANSWER_CHARS] + " …"


def thread_of(earlier: tuple[Exchange, ...]) -> str:
    if not earlier:
        return ""
    lines = ["**Earlier in this conversation**, which is all the agent remembers:"]
    for exchange in earlier:
        lines += [f"**You:** {exchange.question}", f"**Deadwax:** {shortened(exchange.answer)}"]
    return "\n\n".join(lines)


def caption_of(shown: Evidence) -> str:
    return f"**Showing {len(shown.tracks)} of {len(library.tracks())} tracks:** {shown.caption}."


def table_of(shown: Evidence) -> gr.Dataframe:
    return gr.Dataframe(value=rows(shown.tracks), headers=list(HEADERS))


def build_app(cap: DailyCap) -> gr.Blocks:
    whole = Evidence(library.tracks(), "the whole library")

    with gr.Blocks(title="Deadwax", analytics_enabled=False) as app:
        history = gr.State(())
        gr.HTML(brand.HEADER)

        with gr.Row(equal_height=False):
            with gr.Column(scale=2, min_width=280):
                gr.Markdown(INTRO, elem_classes="dw-intro")
                question = gr.Textbox(
                    label="Your question",
                    lines=1,
                    max_lines=6,
                    max_length=MAX_QUESTION_CHARS,
                    placeholder="Ask about the library, or ask for a playlist",
                    elem_id="dw-question",
                    elem_classes="dw-question",
                )
                ask_button = gr.Button("Ask", variant="primary", elem_id="dw-ask")
                with gr.Column(elem_classes="dw-examples"):
                    gr.Examples(examples=EXAMPLES, inputs=question, label="Try one of these")

            with gr.Column(scale=3, min_width=280):
                gr.Markdown("## Answer", elem_classes="dw-section")
                thread = gr.Markdown(elem_classes="dw-thread")
                reply = gr.Markdown(PLACEHOLDER, elem_classes="dw-answer")
                new_conversation = gr.Button("New conversation", size="sm")

        gr.Markdown("## Behind the answer", elem_classes=["dw-section", "dw-behind-heading"])
        with (
            gr.Accordion("Behind the answer", open=False, elem_classes="dw-behind"),
            gr.Row(equal_height=False),
        ):
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("### How it got there")
                trail = gr.Markdown(NO_TRAIL, elem_classes="dw-trail")
            with gr.Column(scale=3, min_width=280):
                gr.Markdown("### The library")
                caption = gr.Markdown(caption_of(whole))
                table = gr.Dataframe(
                    value=rows(whole.tracks),
                    headers=list(HEADERS),
                    interactive=False,
                    wrap=True,
                    max_height=520,
                    elem_classes="dw-table",
                )
                show_all = gr.Button("Show the whole library", size="sm")

        gr.Markdown("## Run it yourself", elem_classes="dw-section")
        with gr.Row(equal_height=False):
            with gr.Column(scale=2, min_width=280):
                gr.HTML(guide.terminal_html())
            with gr.Column(scale=3, min_width=280), gr.Tabs():
                for title, steps in guide.STEPS:
                    with gr.Tab(title):
                        gr.Markdown(steps, elem_classes="dw-guide")

        def answer_question(text: str, earlier: tuple[Exchange, ...]) -> tuple:
            turn = respond(text, cap, earlier)
            if turn.exchange is None or turn.shown is None:
                skipped = (gr.skip(),) * 4
                return turn.reply, *skipped, earlier, gr.skip()
            remembered = remember(earlier, turn.exchange)
            return (
                card(turn.exchange.question, turn.reply),
                thread_of(remembered[:-1]),
                turn.trail,
                caption_of(turn.shown),
                table_of(turn.shown),
                remembered,
                "",
            )

        def start_again() -> tuple:
            return PLACEHOLDER, "", NO_TRAIL, caption_of(whole), table_of(whole), (), ""

        def reset_table() -> tuple:
            return caption_of(whole), table_of(whole)

        outputs = [reply, thread, trail, caption, table, history, question]
        ask_button.click(answer_question, inputs=[question, history], outputs=outputs)
        question.submit(answer_question, inputs=[question, history], outputs=outputs)
        new_conversation.click(start_again, outputs=outputs)
        show_all.click(reset_table, outputs=[caption, table])
    return app


def main() -> None:
    load_env_file()
    os.environ[library.LIBRARY_VARIABLE] = library.FIXTURES
    os.environ["GEMINI_MODEL"] = EVAL_MODEL
    cap = DailyCap(int(os.environ.get(DAILY_QUESTIONS_VARIABLE, DEFAULT_DAILY_QUESTIONS)))
    build_app(cap).launch(
        theme=brand.THEME,
        css=guide.terminal_css() + brand.CSS + dock.CSS + mobile.CSS,
        head=brand.HEAD + dock.script() + mobile.script(PLACEHOLDER),
        favicon_path=str(brand.FAVICON),
        footer_links=["gradio"],
    )


if __name__ == "__main__":
    main()
