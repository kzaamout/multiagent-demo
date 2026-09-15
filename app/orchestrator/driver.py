"""Scripted human for tests and the golden regenerator.

Waits for the Orchestrator to need the human and answers from the scenario's HumanScript.
It is not part of the application; the presenter is the human in the application.
"""

from __future__ import annotations

import asyncio

from app.agents.base import HumanScript
from app.orchestrator.orchestrator import Answer, Orchestrator


async def drive(orchestrator: Orchestrator, script: HumanScript) -> None:
    run_task = asyncio.create_task(orchestrator.run())
    orchestrator.attach_task(run_task)
    try:
        while not run_task.done():
            waiter = asyncio.create_task(orchestrator.human_needed.wait())
            done, _ = await asyncio.wait({run_task, waiter}, return_when=asyncio.FIRST_COMPLETED)
            if run_task in done:
                waiter.cancel()
                break
            pending = orchestrator.pending()
            if pending["kind"] == "clarifications":
                answers = [
                    Answer(question_id=qid, answer=script.answers.get(qid, ""))
                    for qid in pending["question_ids"]
                ]
                orchestrator.submit_answers(answers)
            elif pending["kind"] == "blocker":
                blocker = pending["blocker"] or {}
                action = script.blocker_action or "escalate"
                orchestrator.submit_answers(
                    [Answer(question_id=blocker["blocker_id"], answer=script.blocker_answer, action=action)]
                )
            elif pending["kind"] == "handoff":
                orchestrator.submit_decision(script.decision or "approve")
            await asyncio.sleep(0)
    finally:
        await run_task
