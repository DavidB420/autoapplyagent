class WorkdayAdapter:
    name = "workday"

    async def open_application(self, url: str):
        raise NotImplementedError

    async def get_questions(self):
        raise NotImplementedError

    async def fill_question(self, question, answer: str):
        raise NotImplementedError

    async def submit(self):
        raise NotImplementedError
