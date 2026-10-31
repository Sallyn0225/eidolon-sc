"""Letters over HTTP (GLOSSARY.md「信」): `/api/letters` lists the signed-in user's letters,
the latest first; `/api/letters/{id}` reads one; `/api/letters/{id}/read` has it read (PUT),
on every device, and `/api/letters/{id}/popped` popped up, so it does not again; DELETE
`/api/letters/{id}` deletes it, its voice with it; `/api/letters/{id}/voice/{block}` is a block of it read aloud, as mp3, the
browser's alone to keep. Another's letter, or none, is none (404), to admins too. Whether the
deployer has letters on or off, the letters written stay to be read."""

from fastapi import FastAPI, HTTPException, Response

from eidolon.assembly import Backend
from eidolon.sessions import UserId

_VOICE_CACHE = {"Cache-Control": "private, max-age=31536000, immutable"}
"""A letter read aloud never changes once written."""


def add_letter_routes(app: FastAPI, backend: Backend) -> None:
    @app.get("/api/letters")
    async def letters(user_id: UserId) -> dict:
        """The user's letters, the latest first."""
        return {"letters": [each.shown() for each in await backend.letters.listed(user_id)]}

    @app.get("/api/letters/{letter_id}")
    async def letter(letter_id: int, user_id: UserId) -> dict:
        found = await backend.letters.letter(user_id, letter_id)
        if found is None:
            raise HTTPException(404, "信不存在")
        return found.shown()

    @app.get("/api/letters/{letter_id}/voice/{block}")
    async def voice(letter_id: int, block: int, user_id: UserId) -> Response:
        mp3 = await backend.letters.voice(user_id, letter_id, block)
        if mp3 is None:
            raise HTTPException(404, "信不存在")
        return Response(mp3, media_type="audio/mpeg", headers=_VOICE_CACHE)

    @app.put("/api/letters/{letter_id}/read", status_code=204)
    async def mark_read(letter_id: int, user_id: UserId) -> None:
        if not await backend.letters.mark_read(user_id, letter_id):
            raise HTTPException(404, "信不存在")

    @app.put("/api/letters/{letter_id}/popped", status_code=204)
    async def mark_popped(letter_id: int, user_id: UserId) -> None:
        if not await backend.letters.mark_popped(user_id, letter_id):
            raise HTTPException(404, "信不存在")

    @app.delete("/api/letters/{letter_id}", status_code=204)
    async def delete(letter_id: int, user_id: UserId) -> None:
        if not await backend.letters.delete(user_id, letter_id):
            raise HTTPException(404, "信不存在")
